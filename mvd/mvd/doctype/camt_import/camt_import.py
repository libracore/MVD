# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from bs4 import BeautifulSoup
import hashlib
import json
from datetime import datetime
import operator
import re
import six
from frappe.utils.background_jobs import enqueue
from mvd.mvd.doctype.fakultative_rechnung.fakultative_rechnung import create_unpaid_sinv

class CAMTImport(Document):
    pass

@frappe.whitelist()
def lese_camt_file(camt_import, file_path):
    # erstelle master daten
    errors = []
    imported_payments = []
    assigned_payments = []
    unassigned_payments = []
    submitted_payments = []
    unsubmitted_payments = []
    unimported_payments = []
    deleted_payments = []
    master_data = {
        'status': 'Open',
        'errors': errors,
        'imported_payments': imported_payments,
        'unimported_payments': unimported_payments,
        'assigned_payments': assigned_payments,
        'unassigned_payments': unassigned_payments,
        'submitted_payments': submitted_payments,
        'unsubmitted_payments': unsubmitted_payments,
        'deleted_payments': deleted_payments
    }
    
    # lese und prüfe camt file
    camt_file = get_camt_file(file_path, test=True)
    if not camt_file:
        master_data['status'] = 'Failed'
        master_data['errors'].append("Das CAMT File konnte nicht gelesen werden.")
        return update_camt_import_record(camt_import, master_data)
    
    args = {
        'master_data': master_data,
        'camt_file': file_path,
        'camt_import': camt_import
    }
    enqueue("mvd.mvd.doctype.camt_import.camt_import.verarbeite_camt_file", queue='long', job_name='Verarbeite CAMT Import {0}'.format(camt_import), timeout=5000, **args)

def verarbeite_camt_file(master_data, camt_file, camt_import):
    frappe.publish_realtime('msgprint', 'Verarbeitung CAMT Import {0} gestartet'.format(camt_import))
    
    # lese und prüfe camt file
    camt_file = get_camt_file(camt_file)
    
    # verarbeite camt file
    master_data = process_camt_file(master_data, camt_file, camt_import)
    
    # update camt import datensatz
    update_camt_import_record(camt_import, master_data)

def get_camt_file(file_path, test=False):
    try:
        physical_path = "/home/frappe/frappe-bench/sites/{0}{1}".format(frappe.local.site_path.replace("./", ""), file_path)
        with open(physical_path, 'r') as f:
            content = f.read()
        soup = BeautifulSoup(content, 'lxml')
        iban = soup.document.bktocstmrdbtcdtntfctn.ntfctn.acct.id.iban.get_text()
        if test:
            return True
        else:
            return soup
    except:
        return False

def process_camt_file(master_data, camt_file, camt_import):
    master_data['status'] = 'In Bearbeitung'
    camt_import = frappe.get_doc("CAMT Import", camt_import)
    account = camt_import.account
    sektion = camt_import.sektion_id
    company = camt_import.company
    
    transaction_entries = camt_file.find_all('ntry')
    
    for entry in transaction_entries:
        entry_soup = BeautifulSoup(six.text_type(entry), 'lxml')
        date = entry_soup.bookgdt.dt.get_text()
        transactions = entry_soup.find_all('txdtls')
        # fetch entry amount as fallback
        entry_amount = float(entry_soup.amt.get_text())
        entry_currency = entry_soup.amt['ccy']
        for transaction in transactions:
            transaction_soup = BeautifulSoup(six.text_type(transaction), 'lxml')
            try:
                unique_reference = transaction_soup.refs.acctsvcrref.get_text()
                amount = float(transaction_soup.amt.get_text())
                currency = transaction_soup.amt['ccy']
                try:
                    party_soup = BeautifulSoup(six.text_type(transaction_soup.dbtr), 'lxml')
                    customer_name = party_soup.nm.get_text()
                    try:
                        street = party_soup.strtnm.get_text()
                        try:
                            street_number = party_soup.bldgnb.get_text()
                            address_line = "{0} {1}".format(street, street_number)
                        except:
                            address_line = street
                    except:
                        address_line = ""
                    try:
                        plz = party_soup.pstcd.get_text()
                    except:
                        plz = ""
                    try:
                        town = party_soup.twnnm.get_text()
                    except:
                        town = ""
                    try:
                        country = party_soup.ctry.get_text()
                    except:
                        party_iban = ""
                    customer_address = "{0}, {1}, {2}".format(address_line, plz, town)
                    try:
                        customer_iban = "{0}".format(transaction_soup.dbtracct.id.iban.get_text())
                    except:
                        customer_iban = ""
                except:
                    # CRDT: use RltdPties:Dbtr
                    #party_soup = BeautifulSoup(str(transaction_soup.txdtls.rltdpties.dbtr)) 
                    try:
                        customer_iban = transaction_soup.dbtracct.id.iban.get_text()
                    except Exception as e:
                        customer_iban = ""
                        frappe.log_error("Error parsing customer info: {0} ({1})".format(e, six.text_type(transaction_soup.dbtr)))
                        # key related parties not found / no customer info
                        customer_name = "Postschalter"
                        customer_address = ""
                try:
                    charges = float(transaction_soup.chrgs.ttlchrgsandtaxamt.get_text())
                except:
                    charges = 0.0
                # paid or received: (DBIT: paid, CRDT: received)
                credit_debit = transaction_soup.cdtdbtind.get_text()
                try:
                    # try to find ESR reference
                    transaction_reference = transaction_soup.rmtinf.strd.cdtrrefinf.ref.get_text()
                except:
                    try:
                        # try to find a user-defined reference (e.g. SINV.)
                        transaction_reference = transaction_soup.rmtinf.ustrd.get_text()
                    except:
                        try:
                            # try to find an end-to-end ID
                            transaction_reference = transaction_soup.refs.endtoendid.get_text()
                        except:
                            transaction_reference = unique_reference
                if credit_debit == "CRDT":
                    # starte import/matching flow für zahlung
                    master_data = create_payment_entry(date=date, to_account=account, received_amount=amount, 
                        transaction_id=unique_reference, remarks="QRR: {0}, {1}, {2}, IBAN: {3}".format(
                        transaction_reference, customer_name, customer_address, customer_iban), company=company, sektion=sektion, qrr=transaction_reference, master_data=master_data)
                        
            except Exception as e:
                master_data['errors'].append("Parsing error: {0}:{1}".format(six.text_type(transaction), e))
                pass
    
    return master_data

def create_payment_entry(date, to_account, received_amount, transaction_id, remarks, company, sektion, qrr, master_data):
    # get default customer
    default_customer = get_default_customer(sektion)
    if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}):
        # create new payment entry
        new_payment_entry = frappe.get_doc({'doctype': 'Payment Entry'})
        new_payment_entry.payment_type = "Receive"
        new_payment_entry.party_type = "Customer";
        new_payment_entry.party = default_customer
        new_payment_entry.company = company
        # date is in DD.MM.YYYY
        new_payment_entry.posting_date = date
        new_payment_entry.paid_to = to_account
        new_payment_entry.received_amount = received_amount
        new_payment_entry.paid_amount = received_amount
        new_payment_entry.reference_no = transaction_id
        new_payment_entry.reference_date = date
        new_payment_entry.remarks = remarks
        inserted_payment_entry = new_payment_entry.insert()
        
        master_data['imported_payments'].append(inserted_payment_entry.name)
        
        # suche nach sinv anhand qrr
        sinv = sinv_lookup(qrr)
        if sinv:
            # matche sinv & payment
            master_data = match(sinv, inserted_payment_entry.name, master_data)
            return master_data
        
        # suche nach fr anhand qrr
        fr = fr_lookup(qrr)
        if fr:
            # erstelle sinv aus fr
            sinv = create_unpaid_sinv(fr, betrag=received_amount)
            # matche sinv & payment
            master_data = match(sinv, inserted_payment_entry.name, master_data)
            return master_data
        
        # weder sinv noch fr
        master_data['unassigned_payments'].append(inserted_payment_entry.name)
        master_data['unsubmitted_payments'].append(inserted_payment_entry.name)
        return master_data
        
    else:
        master_data['unimported_payments'].append([qrr, transaction_id])
        return master_data

def sinv_lookup(qrr):
    sinv = frappe.db.sql("""SELECT `name`
                            FROM `tabSales Invoice`
                            WHERE `docstatus` = 1
                            AND REPLACE(`esr_reference`, ' ', '') = '{qrr}'""".format(qrr=qrr), as_dict=True)
    if len(sinv) > 0:
        return sinv[0].name
    else:
        return False

def fr_lookup(qrr):
    fr = frappe.db.sql("""SELECT `name`
                            FROM `tabFakultative Rechnung`
                            WHERE `docstatus` = 1
                            AND `status` = 'Unpaid'
                            AND REPLACE(`qrr_referenz`, ' ', '') = '{qrr}'""".format(qrr=qrr), as_dict=True)
    if len(fr) > 0:
        return fr[0].name
    else:
        return False

def match(sales_invoice, payment_entry, master_data):
    # get the customer
    customer = frappe.get_value("Sales Invoice", sales_invoice, "customer")
    payment_entry_record = frappe.get_doc("Payment Entry", payment_entry)
    # assign the actual customer
    payment_entry_record.party = customer            
    payment_entry_record.save()
    
    # now, add the reference to the sales invoice
    submittable = create_reference(payment_entry, sales_invoice)
    
    master_data['assigned_payments'].append(payment_entry_record.name)
    
    if submittable:
        pe = frappe.get_doc("Payment Entry", payment_entry_record.name)
        pe.submit()
        master_data['submitted_payments'].append(pe.name)
    else:
        master_data['unsubmitted_payments'].append(payment_entry_record.name)
        
    return master_data

def create_reference(payment_entry, sales_invoice):
    # create a new payment entry reference
    reference_entry = frappe.get_doc({"doctype": "Payment Entry Reference"})
    reference_entry.parent = payment_entry
    reference_entry.parentfield = "references"
    reference_entry.parenttype = "Payment Entry"
    reference_entry.reference_doctype = "Sales Invoice"
    reference_entry.reference_name = sales_invoice
    reference_entry.total_amount = frappe.get_value("Sales Invoice", sales_invoice, "base_grand_total")
    reference_entry.outstanding_amount = frappe.get_value("Sales Invoice", sales_invoice, "outstanding_amount")
    paid_amount = frappe.get_value("Payment Entry", payment_entry, "paid_amount")
    if paid_amount > reference_entry.outstanding_amount:
        reference_entry.allocated_amount = reference_entry.outstanding_amount
    else:
        reference_entry.allocated_amount = paid_amount
    reference_entry.insert();
    # update unallocated amount
    payment_record = frappe.get_doc("Payment Entry", payment_entry)
    payment_record.unallocated_amount -= reference_entry.allocated_amount
    payment_record.save()
    
    if payment_record.unallocated_amount > 0:
        return False
    else:
        return True

def get_default_customer(sektion):
    default_customer = frappe.get_doc("Sektion", sektion).default_customer
    return default_customer

def update_camt_import_record(camt_import, master_data, aktualisierung=False):
    camt_import = frappe.get_doc("CAMT Import", camt_import)
    if master_data['status'] == 'Failed':
        camt_import.status = 'Failed'
    else:
        if len(master_data['submitted_payments']) == len(master_data['imported_payments']):
            camt_import.status = 'Closed'
        else:
            camt_import.status = 'Verarbeitet'
            if (len(master_data['submitted_payments']) + len(master_data['deleted_payments'])) == len(master_data['imported_payments']):
                camt_import.status = 'Closed'
        
    camt_import.anz_importet_payments = len(master_data['imported_payments'])
    camt_import.anz_matched_payments = len(master_data['assigned_payments'])
    camt_import.anz_unmatched_payments = len(master_data['unassigned_payments'])
    camt_import.anz_submitted_payments = len(master_data['submitted_payments'])
    camt_import.anz_unsubmitted_payments = len(master_data['unsubmitted_payments'])
    camt_import.anz_deleted_payments = len(master_data['deleted_payments'])
    camt_import.importet_payments = str(master_data['imported_payments'])
    camt_import.matched_payments = str(master_data['assigned_payments'])
    camt_import.unmatched_payments = str(master_data['unassigned_payments'])
    camt_import.submitted_payments = str(master_data['submitted_payments'])
    camt_import.unsubmitted_payments = str(master_data['unsubmitted_payments'])
    camt_import.deleted_payments = str(master_data['deleted_payments'])
    camt_import.errors = str(master_data['errors'])
    camt_import.master_data = str(master_data)
    camt_import.save()
    
    if not aktualisierung:
        frappe.publish_realtime('msgprint', 'Verarbeitung CAMT Import {0} beendet'.format(camt_import.name))
    return

@frappe.whitelist()
def aktualisiere_camt_uebersicht(camt_import):
    camt_import = frappe.get_doc("CAMT Import", camt_import)
    master_data = eval(camt_import.master_data)
    master_data = {
        'status': master_data['status'],
        'errors': [],
        'imported_payments': master_data['imported_payments'],
        'unimported_payments': master_data['unimported_payments'],
        'assigned_payments': [],
        'unassigned_payments': [],
        'submitted_payments': [],
        'unsubmitted_payments': [],
        'deleted_payments': []
    }
    default_customer = get_default_customer(camt_import.sektion_id)
    
    for imported_payment in master_data['imported_payments']:
        if not frappe.db.exists('Payment Entry', imported_payment):
            master_data['deleted_payments'].append(imported_payment)
        else:
            cancelled = check_if_payment_is_cancelled(imported_payment)
            if cancelled:
                master_data['deleted_payments'].append(imported_payment)
            else:
                submitted = check_if_payment_is_submitted(imported_payment)
                if submitted:
                    master_data['submitted_payments'].append(imported_payment)
                    master_data['assigned_payments'].append(imported_payment)
                else:
                    assigned = check_if_payment_is_assigned(imported_payment, default_customer)
                    if assigned:
                        master_data['assigned_payments'].append(imported_payment)
                        master_data['unsubmitted_payments'].append(imported_payment)
                    else:
                        master_data['unassigned_payments'].append(imported_payment)
                        master_data['unsubmitted_payments'].append(imported_payment)
    
    return update_camt_import_record(camt_import.name, master_data, aktualisierung=True)

def check_if_payment_is_cancelled(imported_payment):
    pe = frappe.get_doc("Payment Entry", imported_payment)
    if pe.docstatus == 2:
        return True
    else:
        return False

def check_if_payment_is_submitted(imported_payment):
    pe = frappe.get_doc("Payment Entry", imported_payment)
    if pe.docstatus == 1:
        return True
    else:
        return False

def check_if_payment_is_assigned(imported_payment, default_customer):
    pe = frappe.get_doc("Payment Entry", imported_payment)
    if pe.party != default_customer:
        return True
    else:
        return False
