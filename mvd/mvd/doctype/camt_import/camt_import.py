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
from decimal import Decimal, ROUND_HALF_UP
from frappe.utils.data import today

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
    overpaid = []
    doppelte_mitgliedschaft = []
    gebucht_weggezogen = []
    underpaid = []
    master_data = {
        'status': 'Open',
        'errors': errors,
        'imported_payments': imported_payments,
        'unimported_payments': unimported_payments,
        'assigned_payments': assigned_payments,
        'unassigned_payments': unassigned_payments,
        'submitted_payments': submitted_payments,
        'unsubmitted_payments': unsubmitted_payments,
        'deleted_payments': deleted_payments,
        'overpaid': overpaid,
        'doppelte_mitgliedschaft': doppelte_mitgliedschaft,
        'gebucht_weggezogen': gebucht_weggezogen,
        'underpaid': underpaid,
        'splittet_overpaid': []
    }
    '''
        imported_payments = Alle importierten Zahlungen aus dem CAMT-File
        unimported_payments = Alle Zahlungen aus dem CAMT-File welche nicht importiert werden konnten, da die entsprechende Transaktions-ID bereits verwendet wurde
        assigned_payments = Alle Zahlungen die einem effektiven Debitor zugewiesen werden konnten
        unassigned_payments = Alle Zahlungen zu denen kein Debitor gefunden werden konnten und weiterhin auf den Standard-Debitor zugewiesen sind
        submitted_payments = Alle verbuchten Zahlungen
        unsubmitted_payments = importierte, aber nicht verbuchte Zahlungen (zugewiesene wie auch unzugewiesene)
        deleted_payments = Zahlungen die einst importiert wurden, danach aber entweder gelöscht oder abgebrochen wurden
        overpaid = Zahlungen die importiert & zugewiesen wurden, aber überbezahlt sind
        doppelte_mitgliedschaft = Zahlungen die importiert & zugewiesen wurden, sowie der überbezahlte Wert exakt dem zugewiesenen Wert entspricht
    '''
    
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
    
    # prüfe overpaids nach offenen mitgliedschaftsrechnungen
    if len(master_data['overpaid']) > 0:
        for overpaid in master_data['overpaid']:
            pe = frappe.get_doc("Payment Entry", overpaid)
            if pe.unallocated_amount > 0:
                mitgliedschaftsrechnungen = frappe.db.sql("""SELECT
                                                                `name`
                                                            FROM `tabSales Invoice`
                                                            WHERE `outstanding_amount` = '{outstanding_amount}'
                                                            AND `ist_mitgliedschaftsrechnung` = 1
                                                            AND `customer` = '{customer}'""".format(outstanding_amount=pe.unallocated_amount, customer=pe.party), as_dict=True)
                if len(mitgliedschaftsrechnungen) > 0:
                    master_data['overpaid'].remove(overpaid)
                    master_data['assigned_payments'].remove(overpaid)
                    master_data['unsubmitted_payments'].remove(overpaid)
                    
                    master_data = match(mitgliedschaftsrechnungen[0].name, pe.name, master_data)
    
    # splitte overpaids, mit zuweisung zu mitgliedschaftsrechnung, nach 1. pe mit Mitgliedschaftsrechnung = Submitted und 2. Rest auf neue Zahlung als Draft
    if len(master_data['overpaid']) > 0:
        for overpaid in master_data['overpaid']:
            pe = frappe.get_doc("Payment Entry", overpaid)
            for sinv in pe.references:
                if sinv.reference_doctype == 'Sales Invoice':
                    sinv = frappe.get_doc("Sales Invoice", sinv.reference_name)
                    if sinv.ist_mitgliedschaftsrechnung:
                        # dupliziere Zahlung
                        new_pe = frappe.copy_doc(pe)
                        new_pe.reference_no = pe.reference_no + ' Überzahlung von {0}'.format(pe.name)
                        new_pe.references = []
                        new_pe.received_amount = pe.unallocated_amount
                        new_pe.paid_amount = pe.unallocated_amount
                        new_pe.unallocated_amount = pe.unallocated_amount
                        new_pe.insert()
                        master_data['overpaid'].append(new_pe.name)
                        master_data['assigned_payments'].append(new_pe.name)
                        master_data['unsubmitted_payments'].append(new_pe.name)
                        master_data['imported_payments'].append(new_pe.name)
                        master_data['splittet_overpaid'].append(new_pe.name)
                        
                        # reduziere urspungszahlung um neu zugewiesenen Betrag und verbuche
                        pe.received_amount = pe.received_amount - pe.unallocated_amount
                        pe.paid_amount = pe.paid_amount - pe.unallocated_amount
                        pe.unallocated_amount = 0
                        pe.save()
                        pe.submit()
                        master_data['overpaid'].remove(pe.name)
                        master_data['unsubmitted_payments'].remove(pe.name)
                        master_data['submitted_payments'].append(pe.name)
                        
    
    return master_data

def create_payment_entry(date, to_account, received_amount, transaction_id, remarks, company, sektion, qrr, master_data):
    # get default customer
    default_customer = get_default_customer(sektion)
    if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}):
        # create new payment entry
        new_payment_entry = frappe.get_doc({'doctype': 'Payment Entry'})
        new_payment_entry.payment_type = "Receive"
        new_payment_entry.party_type = "Customer"
        new_payment_entry.party = default_customer
        new_payment_entry.sektion_id = sektion
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
        sinv, wegzug = sinv_lookup(qrr)
        if sinv and not wegzug:
            # matche sinv & payment
            master_data = match(sinv, inserted_payment_entry.name, master_data)
            return master_data
        
        if wegzug:
            # matche sinv & payment in fremdsektion (zuzugssektion)
            master_data = match(wegzug, inserted_payment_entry.name, master_data, fremdsektion=True)
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
    sinv = frappe.db.sql("""SELECT `name`, `mv_mitgliedschaft`, `docstatus`
                            FROM `tabSales Invoice`
                            WHERE REPLACE(`esr_reference`, ' ', '') = '{qrr}'""".format(qrr=qrr), as_dict=True)
    if len(sinv) > 0:
        if sinv[0].docstatus == 1:
            return sinv[0].name, False
        elif sinv[0].docstatus == 2:
            # potenzieller wegzug
            potenzieller_wegzug = find_potenzieller_wegzug(sinv[0].mv_mitgliedschaft)
            if potenzieller_wegzug:
                return False, potenzieller_wegzug
            else:
                return False, False
        else:
            return False, False
    else:
        return False, False

def find_potenzieller_wegzug(mitgliedschaft):
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    if mitgliedschaft.status_c == 'Wegzug':
        if mitgliedschaft.wegzug_zu:
            umzugs_mitgliedschaft = frappe.db.sql("""SELECT
                                                        `name`
                                                    FROM `tabMitgliedschaft`
                                                    WHERE `sektion_id` = '{wegzug_zu}'
                                                    AND `mitglied_nr` = '{mitglied_nr}'""".format(wegzug_zu=mitgliedschaft.wegzug_zu, mitglied_nr=mitgliedschaft.mitglied_nr), as_dict=True)
            if len(umzugs_mitgliedschaft) > 0:
                umzugs_mitgliedschaft = umzugs_mitgliedschaft[0].name
                sinv = frappe.db.sql("""SELECT `name` FROM `tabSales Invoice` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}' AND `docstatus` = 1 AND `status` != 'Paid'""".format(mitgliedschaft=umzugs_mitgliedschaft), as_dict=True)
                if len(sinv) > 0:
                    return sinv[0].name
                else:
                    return False
            else:
                return False
        else:
            return False
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

def match(sales_invoice, payment_entry, master_data, fremdsektion=False):
    # get the customer
    customer = frappe.get_value("Sales Invoice", sales_invoice, "customer")
    mitgliedschaft = frappe.get_value("Sales Invoice", sales_invoice, "mv_mitgliedschaft")
    payment_entry_record = frappe.get_doc("Payment Entry", payment_entry)
    # assign the actual customer
    payment_entry_record.party = customer
    payment_entry_record.mv_mitgliedschaft = mitgliedschaft
    payment_entry_record.save()
    
    # now, add the reference to the sales invoice
    submittable, master_data = create_reference(payment_entry, sales_invoice, master_data, fremdsektion=fremdsektion)
    
    master_data['assigned_payments'].append(payment_entry_record.name)
    if fremdsektion:
        master_data['gebucht_weggezogen'].append(payment_entry_record.name)
    
    if submittable:
        pe = frappe.get_doc("Payment Entry", payment_entry_record.name)
        pe.submit()
        master_data['submitted_payments'].append(pe.name)
    else:
        master_data['unsubmitted_payments'].append(payment_entry_record.name)
        
    return master_data

def create_reference(payment_entry, sales_invoice, master_data, fremdsektion):
    # create a new payment entry reference
    reference_entry = frappe.get_doc({"doctype": "Payment Entry Reference"})
    reference_entry.parent = payment_entry
    reference_entry.parentfield = "references"
    reference_entry.parenttype = "Payment Entry"
    reference_entry.reference_doctype = "Sales Invoice"
    reference_entry.reference_name = sales_invoice
    reference_entry.total_amount = frappe.get_value("Sales Invoice", sales_invoice, "base_grand_total")
    reference_entry.outstanding_amount = frappe.get_value("Sales Invoice", sales_invoice, "outstanding_amount")
    if not fremdsektion:
        paid_amount = frappe.get_value("Payment Entry", payment_entry, "paid_amount")
        if paid_amount >= reference_entry.outstanding_amount:
            reference_entry.allocated_amount = reference_entry.outstanding_amount
        else:
            reference_entry.allocated_amount = paid_amount
            master_data['underpaid'].append(payment_entry)
    else:
        paid_amount = reference_entry.outstanding_amount
        reference_entry.allocated_amount = paid_amount
    reference_entry.insert();
    # update unallocated amount
    payment_record = frappe.get_doc("Payment Entry", payment_entry)
    payment_record.unallocated_amount -= reference_entry.allocated_amount
    if fremdsektion:
        payment_record.company = frappe.get_value("Sales Invoice", sales_invoice, "company")
        payment_record.sektion_id = frappe.get_value("Sales Invoice", sales_invoice, "sektion_id")
        payment_record.paid_from = frappe.get_value("Sales Invoice", sales_invoice, "debit_to")
        payment_record.paid_to = frappe.get_value("Sektion", payment_record.sektion_id, "account")
        differenz = payment_record.paid_amount - paid_amount
        row = payment_record.append('deductions', {})
        row.amount = differenz * -1
        row.account = frappe.get_value("Sektion", payment_record.sektion_id, "zwischen_konto")
        row.cost_center = frappe.get_value("Company", payment_record.company, "cost_center")
        
    payment_record.save()
    
    if payment_record.unallocated_amount > 0:
        # exakt um HV Betrag überzahlt
        if payment_record.unallocated_amount == 12:
            fr = fr_lookup_based_on_sinv(sales_invoice)
            if fr:
                sinv = create_unpaid_sinv(fr, betrag=12)
                hv_reference_entry = frappe.get_doc({"doctype": "Payment Entry Reference"})
                hv_reference_entry.parent = payment_entry
                hv_reference_entry.parentfield = "references"
                hv_reference_entry.parenttype = "Payment Entry"
                hv_reference_entry.reference_doctype = "Sales Invoice"
                hv_reference_entry.reference_name = sinv
                hv_reference_entry.total_amount = frappe.get_value("Sales Invoice", sinv, "base_grand_total")
                hv_reference_entry.outstanding_amount = frappe.get_value("Sales Invoice", sinv, "outstanding_amount")
                paid_amount = frappe.get_value("Payment Entry", payment_entry, "paid_amount")
                hv_reference_entry.allocated_amount = 12
                hv_reference_entry.insert();
                # update unallocated amount
                payment_record = frappe.get_doc("Payment Entry", payment_entry)
                payment_record.unallocated_amount -= hv_reference_entry.allocated_amount
                payment_record.save()
                
                return True, master_data
            else:
                master_data['overpaid'].append(payment_record.name)
                return False, master_data
        # Doppelter Mitgliedschaftsbetrag
        elif payment_record.unallocated_amount == reference_entry.allocated_amount:
            master_data['doppelte_mitgliedschaft'].append(payment_record.name)
            return False, master_data
        else:
            master_data['overpaid'].append(payment_record.name)
            return False, master_data
    else:
        # nicht über rechnungsbetrag, soweit so gut
        return True, master_data

def fr_lookup_based_on_sinv(sinv):
    fr = frappe.db.sql("""SELECT `name`
                            FROM `tabFakultative Rechnung`
                            WHERE `docstatus` = 1
                            AND `status` = 'Unpaid'
                            AND `typ` = 'HV'
                            AND `sales_invoice` = '{sinv}'""".format(sinv=sinv), as_dict=True)
    if len(fr) > 0:
        return fr[0].name
    else:
        return False

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
    camt_import.anz_overpaid = len(master_data['overpaid'])
    camt_import.anz_underpaid = len(master_data['underpaid'])
    camt_import.underpaid = str(master_data['underpaid'])
    camt_import.anz_doppelte_mitgliedschaft = len(master_data['doppelte_mitgliedschaft'])
    camt_import.gebucht_weggezogen = len(master_data['gebucht_weggezogen'])
    camt_import.gebucht_weggezogen_list = str(master_data['gebucht_weggezogen'])
    camt_import.importet_payments = str(master_data['imported_payments'])
    camt_import.matched_payments = str(master_data['assigned_payments'])
    camt_import.unmatched_payments = str(master_data['unassigned_payments'])
    camt_import.submitted_payments = str(master_data['submitted_payments'])
    camt_import.unsubmitted_payments = str(master_data['unsubmitted_payments'])
    camt_import.deleted_payments = str(master_data['deleted_payments'])
    camt_import.overpaid = str(master_data['overpaid'])
    camt_import.splittet_overpaid = str(master_data['splittet_overpaid'])
    camt_import.doppelte_mitgliedschaft = str(master_data['doppelte_mitgliedschaft'])
    camt_import.errors = str(master_data['errors'])
    camt_import.master_data = str(master_data)
    camt_import.save()
    erstelle_report(camt_import.name)
    
    if not aktualisierung:
        frappe.publish_realtime('msgprint', 'Verarbeitung CAMT Import {0} beendet'.format(camt_import.name))
    return

@frappe.whitelist()
def aktualisiere_camt_uebersicht(camt_import):
    camt_import = frappe.get_doc("CAMT Import", camt_import)
    master_data = eval(camt_import.master_data)
    master_data = {
        'status': master_data['status'],
        'gebucht_weggezogen': master_data['gebucht_weggezogen'],
        'errors': [],
        'imported_payments': master_data['imported_payments'],
        'unimported_payments': master_data['unimported_payments'],
        'assigned_payments': [],
        'unassigned_payments': [],
        'submitted_payments': [],
        'unsubmitted_payments': [],
        'deleted_payments': [],
        'overpaid': [],
        'doppelte_mitgliedschaft': [],
        'underpaid': [],
        'splittet_overpaid': master_data['splittet_overpaid']
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
                    underpaid = check_if_payment_is_underpaid(imported_payment)
                    if underpaid:
                        master_data['underpaid'].append(imported_payment)
                else:
                    assigned = check_if_payment_is_assigned(imported_payment, default_customer)
                    if assigned:
                        master_data['assigned_payments'].append(imported_payment)
                        master_data['unsubmitted_payments'].append(imported_payment)
                        overpaid, doppelte_mitgliedschaft = check_if_payment_is_overpaid(imported_payment)
                        if overpaid:
                            if doppelte_mitgliedschaft:
                                master_data['doppelte_mitgliedschaft'].append(imported_payment)
                            else:
                                master_data['overpaid'].append(imported_payment)
                        else:
                            underpaid = check_if_payment_is_underpaid(imported_payment)
                            if underpaid:
                                master_data['underpaid'].append(imported_payment)
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

def check_if_payment_is_overpaid(imported_payment):
    pe = frappe.get_doc("Payment Entry", imported_payment)
    if pe.unallocated_amount > 0:
        if (pe.paid_amount / 2) == pe.unallocated_amount:
            return True, True
        else:
            return True, False
    else:
        return False, False

def check_if_payment_is_underpaid(imported_payment):
    pe = frappe.get_doc("Payment Entry", imported_payment)
    for sinv in pe.references:
        if sinv.allocated_amount < sinv.outstanding_amount:
            return True
    return False

@frappe.whitelist()
def mit_spende_ausgleichen(pe):
    payment_entry = frappe.get_doc("Payment Entry", pe)
    mitgliedschaft = payment_entry.mv_mitgliedschaft
    
    # erstelle fr
    from mvd.mvd.doctype.fakultative_rechnung.fakultative_rechnung import create_hv_fr
    fr = create_hv_fr(mitgliedschaft, betrag_spende=payment_entry.unallocated_amount)
    # erstelle sinv aus fr
    sinv = create_unpaid_sinv(fr, betrag=payment_entry.unallocated_amount)
    
    # match sinv mit pe
    reference_entry = frappe.get_doc({"doctype": "Payment Entry Reference"})
    reference_entry = payment_entry.append('references', {})
    reference_entry.reference_doctype = "Sales Invoice"
    reference_entry.reference_name = sinv
    reference_entry.total_amount = frappe.get_value("Sales Invoice", sinv, "base_grand_total")
    reference_entry.outstanding_amount = frappe.get_value("Sales Invoice", sinv, "outstanding_amount")
    reference_entry.allocated_amount = reference_entry.outstanding_amount
    #reference_entry.insert();
    # update unallocated amount
    payment_entry.unallocated_amount -= reference_entry.allocated_amount
    payment_entry.save()
    payment_entry.submit()
    return

@frappe.whitelist()
def mit_folgejahr_ausgleichen(pe):
    payment_entry = frappe.get_doc("Payment Entry", pe)
    sinv_to_copy = frappe.get_doc("Sales Invoice", payment_entry.references[0].reference_name)
    sinv = frappe.copy_doc(sinv_to_copy)
    sinv.mitgliedschafts_jahr = sinv_to_copy.mitgliedschafts_jahr + 1
    sinv.insert()
    sinv.submit()
    
    # match sinv mit pe
    reference_entry = frappe.get_doc({"doctype": "Payment Entry Reference"})
    reference_entry = payment_entry.append('references', {})
    reference_entry.reference_doctype = "Sales Invoice"
    reference_entry.reference_name = sinv.name
    reference_entry.total_amount = sinv.base_grand_total
    reference_entry.outstanding_amount = sinv.outstanding_amount
    reference_entry.allocated_amount = reference_entry.outstanding_amount
    #reference_entry.insert();
    # update unallocated amount
    payment_entry.unallocated_amount -= reference_entry.allocated_amount
    payment_entry.save()
    payment_entry.submit()
    return

@frappe.whitelist()
def kulanz_ausgleich(pe):
    payment_entry = frappe.get_doc("Payment Entry", pe)
    pe = frappe.copy_doc(payment_entry)
    pe.reference_no = 'Kulanzausgleich {0}'.format(payment_entry.name)
    pe.paid_to = frappe.get_value("Sektion", pe.sektion_id, "kulanz_konto")
    
    new_payment = 0
    for sinv in pe.references:
        if sinv.outstanding_amount > sinv.allocated_amount:
            outstanding_amount = frappe.get_value("Sales Invoice", sinv.reference_name, "outstanding_amount")
            if outstanding_amount > 0:
                new_payment += outstanding_amount
                sinv.allocated_amount = outstanding_amount
                sinv.outstanding_amount = outstanding_amount
    if new_payment > 0:
        pe.paid_amount = new_payment
        pe.insert()
        pe.save()
        pe.submit()
        payment_entry.add_comment('Comment', text='Kulanzausgleich erfolgte mittels {0}'.format(pe.name))
        return
    else:
        frappe.throw("Die Rechnung wurde bereits andersweitig beglichen!")

@frappe.whitelist()
def rueckzahlung(pe):
    payment_entry = frappe.get_doc("Payment Entry", pe)
    row = payment_entry.append('deductions', {})
    row.amount = payment_entry.unallocated_amount * -1
    row.account = frappe.get_value("Sektion", payment_entry.sektion_id, "zwischen_konto")
    row.cost_center = frappe.get_value("Company", payment_entry.company, "cost_center")
    payment_entry.unallocated_amount = 0
    payment_entry.save()
    payment_entry.submit()
    return
    
@frappe.whitelist()
def erstelle_report(camt):
    camt_record = frappe.get_doc("CAMT Import", camt)
    
    allgemein = {
        'filename': str(camt_record.camt_file).split("/")[3],
        'filedatum': '',
        'taxen': 0,
        'anzahl': 0,
        'total': 0,
        'sammlungen': []
    }
    
    verbuchte_zahlungen = {
        'mitgliedschaften': 0,
        'fremd_sektionen': 0,
        'haftpflicht': 0,
        'spenden': 0,
        'anzahl': 0,
        'total': 0,
        'underpaid': 0
    }
    
    nicht_verbuchte_zahlungen = {
        'doppelt_bezahlt': 0,
        'ueberzahlt': 0,
        'unbekannte_referenz': 0,
        'anzahl': 0,
        'total': 0
    }
    
    physical_path = "/home/frappe/frappe-bench/sites/{0}{1}".format(frappe.local.site_path.replace("./", ""), camt_record.camt_file)
    with open(physical_path, 'r') as f:
        content = f.read()
    soup = BeautifulSoup(content, 'lxml')
    allgemein['filedatum'] = frappe.utils.get_datetime(soup.document.bktocstmrdbtcdtntfctn.grphdr.credttm.get_text().split("T")[0]).strftime('%d.%m.%Y')
    transaction_entries = soup.find_all('ntry')
    for entry in transaction_entries:
        entry_soup = BeautifulSoup(six.text_type(entry), 'lxml')
        date = entry_soup.bookgdt.dt.get_text()
        transactions = entry_soup.find_all('txdtls')
        # fetch entry amount as fallback
        entry_amount = float(entry_soup.amt.get_text())
        allgemein['sammlungen'].append('Datum: ' + frappe.utils.get_datetime(date).strftime('%d.%m.%Y') + ", Betrag: " + "{:,.2f}".format(proper_round(entry_amount, Decimal('0.01'))).replace(",", "'"))
        for transaction in transactions:
            transaction_soup = BeautifulSoup(six.text_type(transaction), 'lxml')
            unique_reference = transaction_soup.refs.acctsvcrref.get_text()
            allgemein['total'] += float(transaction_soup.amt.get_text())
            allgemein['anzahl'] += 1
            try:
                allgemein['taxen'] += float(transaction_soup.chrgs.ttlchrgsandtaxamt.get_text())
            except:
                allgemein['taxen'] += 0.0
            _pe = frappe.db.sql("""SELECT `name` FROM `tabPayment Entry` WHERE `reference_no` = '{unique_reference}'""".format(unique_reference=unique_reference), as_dict=True)
            try:
                pe = frappe.get_doc("Payment Entry", _pe[0].name)
                if pe.docstatus == 1:
                    verbuchte_zahlungen['total'] += float(pe.paid_amount)
                    verbuchte_zahlungen['anzahl'] += 1
                    for _sinv in pe.references:
                        sinv = frappe.get_doc("Sales Invoice", _sinv.reference_name)
                        if camt_record.sektion_id == pe.sektion_id:
                            if sinv.ist_mitgliedschaftsrechnung:
                                verbuchte_zahlungen['mitgliedschaften'] += 1
                            elif sinv.ist_hv_rechnung:
                                verbuchte_zahlungen['haftpflicht'] += 1
                            elif sinv.ist_spenden_rechnung:
                                verbuchte_zahlungen['spenden'] += 1
                            if _sinv.allocated_amount < _sinv.outstanding_amount:
                                verbuchte_zahlungen['underpaid'] += 1
                        else:
                            verbuchte_zahlungen['fremd_sektionen'] += 1
                else:
                    nicht_verbuchte_zahlungen['total'] += float(pe.paid_amount)
                    nicht_verbuchte_zahlungen['anzahl'] += 1
                    if pe.name in eval(camt_record.overpaid):
                        nicht_verbuchte_zahlungen['ueberzahlt'] += 1
                    elif pe.name in eval(camt_record.doppelte_mitgliedschaft):
                        nicht_verbuchte_zahlungen['doppelt_bezahlt'] += 1
                    elif pe.name in eval(camt_record.unmatched_payments):
                        nicht_verbuchte_zahlungen['unbekannte_referenz'] += 1
                    
            except:
                pass
    
    for pe in eval(camt_record.splittet_overpaid):
        pe = frappe.get_doc("Payment Entry", pe)
        nicht_verbuchte_zahlungen['total'] += float(pe.paid_amount)
        nicht_verbuchte_zahlungen['anzahl'] += 1
        nicht_verbuchte_zahlungen['ueberzahlt'] += 1
    
    template_data = {
        'sektion': camt_record.sektion_id,
        'allgemein': {
            'filename': allgemein['filename'],
            'filedatum': allgemein['filedatum'],
            'taxen': "{:,.2f}".format(proper_round(allgemein['taxen'], Decimal('0.01'))).replace(",", "'"),
            'anzahl': str(allgemein['anzahl']),
            'total': "{:,.2f}".format(proper_round(allgemein['total'], Decimal('0.01'))).replace(",", "'")
        },
        'verbuchte_zahlungen': {
            'mitgliedschaften': str(verbuchte_zahlungen['mitgliedschaften']),
            'fremd_sektionen': str(verbuchte_zahlungen['fremd_sektionen']),
            'haftpflicht': str(verbuchte_zahlungen['haftpflicht']),
            'spenden': str(verbuchte_zahlungen['spenden']),
            'anzahl': str(verbuchte_zahlungen['anzahl']),
            'underpaid': str(verbuchte_zahlungen['underpaid']),
            'total': "{:,.2f}".format(proper_round(verbuchte_zahlungen['total'], Decimal('0.01'))).replace(",", "'")
        },
        'nicht_verbuchte_zahlungen': {
            'doppelt_bezahlt': str(nicht_verbuchte_zahlungen['doppelt_bezahlt']),
            'ueberzahlt': str(nicht_verbuchte_zahlungen['ueberzahlt']),
            'unbekannte_referenz': str(nicht_verbuchte_zahlungen['unbekannte_referenz']),
            'anzahl': str(nicht_verbuchte_zahlungen['anzahl']),
            'total': "{:,.2f}".format(proper_round(nicht_verbuchte_zahlungen['total'], Decimal('0.01'))).replace(",", "'")
        }
    }
    zahlungsreport = frappe.render_template('templates/includes/camt_report.html', template_data)
    camt_record.report = zahlungsreport
    camt_record.save()
    return
    
def proper_round(number, decimals):
    return float(Decimal(number).quantize(decimals, ROUND_HALF_UP))

@frappe.whitelist()
def sinv_bez_mit_ezs_oder_bar(sinv, ezs=False, bar=False, hv=False):
    sinv = frappe.get_doc("Sales Invoice", sinv)
    if hv:
        hv_sinv = create_unpaid_sinv(hv, betrag=12)
    
    customer = sinv.customer
    mitgliedschaft = sinv.mv_mitgliedschaft
    payment_entry_record = frappe.get_doc({
        'doctype': "Payment Entry",
        'party_type': 'Customer',
        'party': customer,
        'mv_mitgliedschaft': mitgliedschaft,
        'company': sinv.company,
        'sektion_id': sinv.sektion_id,
        'paid_from': sinv.debit_to,
        'paid_amount': sinv.outstanding_amount,
        'paid_to': frappe.get_value("Sektion", sinv.sektion_id, "account"),
        'received_amount': sinv.outstanding_amount,
        'references': [
            {
                'reference_doctype': "Sales Invoice",
                'reference_name': sinv.name,
                'total_amount': sinv.base_grand_total,
                'outstanding_amount': sinv.outstanding_amount,
                'allocated_amount': sinv.outstanding_amount
            }
        ],
        'reference_no': 'Barzahlung {0}'.format(sinv.name) if bar else 'EZS-Zahlung {0}'.format(sinv.name),
        'reference_date': today()
    }).insert()
    
    if hv:
        hv_sinv = frappe.get_doc("Sales Invoice", hv_sinv)
        hv_row = payment_entry_record.append('references', {})
        hv_row.reference_doctype = "Sales Invoice"
        hv_row.reference_name = hv_sinv.name
        hv_row.total_amount = hv_sinv.base_grand_total
        hv_row.outstanding_amount = hv_sinv.outstanding_amount
        hv_row.allocated_amount = hv_sinv.outstanding_amount
        payment_entry_record.paid_amount += hv_sinv.outstanding_amount
        payment_entry_record.received_amount += hv_sinv.outstanding_amount
        payment_entry_record.total_allocated_amount = payment_entry_record.paid_amount
        payment_entry_record.reference_no = payment_entry_record.reference_no + " & {0}".format(hv_sinv.name)
        payment_entry_record.save()
    
    payment_entry_record.submit()
    
@frappe.whitelist()
def get_filter_for_doppelte():
    pe_mit_doppelzahlungen = frappe.db.sql("""SELECT
                                                `name`
                                            FROM `tabPayment Entry`
                                            WHERE `unallocated_amount` = `total_allocated_amount`
                                            AND `total_allocated_amount` > 0
                                            AND `docstatus` = 0""", as_list=True)
    return pe_mit_doppelzahlungen

@frappe.whitelist()
def get_filter_for_unassigned():
    return frappe.get_list('Sektion', fields='default_customer', as_list=True)
