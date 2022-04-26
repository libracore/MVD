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
from frappe.utils.data import add_days, today, getdate, now

class CAMTImport(Document):
    def validate(self):
        if not self.sektion_id:
            sektionen = frappe.db.sql("""SELECT `for_value` FROM `tabUser Permission` WHERE `allow` = 'Sektion' AND `is_default` = 1 AND `user` = '{user}'""".format(user=frappe.session.user), as_dict=True)
            if len(sektionen) > 0:
                self.sektion_id = sektionen[0].for_value
                sektion = frappe.get_doc("Sektion", sektionen[0].for_value)
                self.company = sektion.company
                self.account = sektion.account

@frappe.whitelist()
def lese_camt_file(camt_import, file_path):
    # erstelle master daten
    master_data = erstelle_master_data()
    
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
    # lese und prüfe camt file
    camt_file = get_camt_file(camt_file)
    
    # Zahlungen von CAMT-File einlesen
    master_data = zahlungen_einlesen(master_data, camt_file, camt_import)
    
    # Zahlungen zuweisen
    master_data = zahlungen_zuweisen(master_data)
    
    # update camt import datensatz
    update_camt_import_record(camt_import, master_data)

# --------------------------------------
# Haupt Funktionen
# --------------------------------------
def zahlungen_einlesen(master_data, camt_file, camt_import):
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
                    master_data = erstelle_zahlung(date=date, to_account=account, received_amount=amount, 
                        transaction_id=unique_reference, remarks="QRR: {0}, {1}, {2}, IBAN: {3}".format(
                        transaction_reference, customer_name, customer_address, customer_iban), company=company, sektion=sektion, qrr=transaction_reference, master_data=master_data)
                        
            except Exception as e:
                master_data['errors'].append("Parsing error: {0}:{1}".format(six.text_type(transaction), e))
                pass
    return master_data
    # ~ return zahlungen_zuweisen(master_data)

def erstelle_zahlung(date, to_account, received_amount, transaction_id, remarks, company, sektion, qrr, master_data):
    # get default customer
    default_customer = get_default_customer(sektion)
    
    # erstelle Zahlung wenn noch nicht vorhanden
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
        new_payment_entry.remarks_clone = remarks
        new_payment_entry.esr_reference = qrr
        
        inserted_payment_entry = new_payment_entry.insert()
        # ~ frappe.db.commit()
        
        master_data['imported_payments'].append(inserted_payment_entry.name)
        
        return master_data
    else:
        master_data['unimported_payments'].append([qrr, transaction_id])
        return master_data

def zahlungen_zuweisen(master_data):
    '''
        Ablauf:
        1. Suche nach offener Rechnung -> Bei Erfolg: 4., sonst 2.
            1.1 Anhand QRR/ESR
            1.2 Hack Anhand stellen 11-24 von QRR/ESR
        2. Prüfe HV Zahlung
            2.1 Betrag = 12? -> Suche nach HV FAK Rechnung -> Bei Erfolg: 4., sonst 3.
        3. Prüfe Spenden Zahlung
            3.1 suche nach Spenden FAK Rechnung anhand QRR/ESR -> Bei Erfolg: 4., sonst 5.
        4. Verbuchen / Splitten
            (4.0) Hack
            4.1 Verbuchen Zahlung mit Rechnung
            4.2 Wenn überzahlt --> Überzahlung in eigene Zahlung umwandeln
            4.3 Wenn Überzahlung = CHF 12 und keine HV FAK vorhanden --> HV Fak erstellen, umwandeln und zuweisen
        5. Umzugshandling
    '''
    
    importierte = master_data['imported_payments']
    for imp_pe in importierte:
        pe = frappe.get_doc("Payment Entry", imp_pe)
        
        # 1.1
        qrr = pe.esr_reference
        
        # HACK (zu kurze ERPNext Referenznummern): soll später entfernt werden
        qrr_short = pe.esr_reference[4:27]
        
        sinv = frappe.db.sql("""SELECT `name`, `mv_mitgliedschaft`, `docstatus`, `due_date`, `base_grand_total`, `outstanding_amount`, `customer`
                            FROM `tabSales Invoice`
                            WHERE (REPLACE(`esr_reference`, ' ', '') = '{qrr}' OR REPLACE(`esr_reference`, ' ', '') = '{qrr_short}')
                            AND `status` != 'Paid'""".format(qrr=qrr, qrr_short=qrr_short), as_dict=True)
        
        # 1.2
        if not len(sinv) > 0:
            # HACK (alte Debitoren)
            qrr = pe.esr_reference[11:24]
            
            sinv = frappe.db.sql("""SELECT `name`, `mv_mitgliedschaft`, `docstatus`, `due_date`, `base_grand_total`, `outstanding_amount`, `customer`
                                FROM `tabSales Invoice`
                                WHERE `esr_reference` LIKE '%{qrr}%'
                                AND `status` != 'Paid'""".format(qrr=qrr), as_dict=True)
        
        # 2.1 / 3.1
        if not len(sinv) > 0 and pe.paid_amount == 12:
            qrr = pe.esr_reference
            
            # HACK (zu kurze ERPNext Referenznummern): soll später entfernt werden
            qrr_short = pe.esr_reference[4:27]
            
            fr = frappe.db.sql("""SELECT `name`
                                FROM `tabFakultative Rechnung`
                                WHERE `docstatus` = 1
                                AND `status` = 'Unpaid'
                                AND (REPLACE(`qrr_referenz`, ' ', '') = '{qrr}' OR REPLACE(`qrr_referenz`, ' ', '') = '{qrr_short}')""".format(qrr=qrr, qrr_short=qrr_short), as_dict=True)
            if len(fr) > 0:
                fr_sinv = create_unpaid_sinv(fr[0].name, betrag=12)
                sinv = frappe.db.sql("""SELECT `name`, `mv_mitgliedschaft`, `docstatus`, `due_date`, `base_grand_total`, `outstanding_amount`, `customer`
                                        FROM `tabSales Invoice`
                                        WHERE `name` = '{fr_sinv}'""".format(fr_sinv=fr_sinv), as_dict=True)
        # 4.
        if len(sinv) > 0:
            if sinv[0].docstatus == 1:
                # Kunde zu Payment Entry zuweisen
                pe.party = sinv[0].customer
                pe.mv_mitgliedschaft = sinv[0].mv_mitgliedschaft
                
                # HACK 2
                if pe.paid_amount < sinv[0].outstanding_amount and pe.paid_amount == 12:
                    if pe.esr_reference[11:14] != '000':
                        # erstelle fr
                        from mvd.mvd.doctype.fakultative_rechnung.fakultative_rechnung import create_hv_fr
                        fr = create_hv_fr(pe.mv_mitgliedschaft)
                        # erstelle sinv aus fr
                        hv_sinv = create_unpaid_sinv(fr)
                        sinv = frappe.db.sql("""SELECT `name`, `mv_mitgliedschaft`, `docstatus`, `due_date`, `base_grand_total`, `outstanding_amount`, `customer`
                                                FROM `tabSales Invoice`
                                                WHERE `name` = '{hv_sinv}'""".format(hv_sinv=hv_sinv), as_dict=True)
                
                # 4.1
                # Referenz Rechnung <> Zahlung hinzufügen
                row = pe.append('references', {})
                row.reference_doctype = "Sales Invoice"
                row.reference_name = sinv[0].name
                row.due_date = sinv[0].due_date
                row.total_amount = sinv[0].base_grand_total
                row.outstanding_amount = sinv[0].outstanding_amount
                
                
                if pe.paid_amount <= sinv[0].outstanding_amount:
                    row.allocated_amount = pe.paid_amount
                    pe.total_allocated_amount = pe.paid_amount
                    pe.unallocated_amount = 0
                    if pe.paid_amount < sinv[0].outstanding_amount:
                        master_data['underpaid'].append(pe.name)
                else:
                    row.allocated_amount = sinv[0].outstanding_amount
                    pe.total_allocated_amount = sinv[0].outstanding_amount
                    pe.unallocated_amount = pe.paid_amount - sinv[0].outstanding_amount
                    
                    # prüfe doppelte Mitgliedschaft
                    doppelte_mitgliedschaft = False
                    if pe.total_allocated_amount == pe.unallocated_amount:
                        doppelte_mitgliedschaft = True
                    
                    # 4.2
                    # dupliziere (splitte) Zahlung (überzahlter Betrag auf eigene Zahlung)
                    new_pe = frappe.copy_doc(pe)
                    new_pe.reference_no = pe.reference_no + ' Überzahlung von {0}'.format(pe.name)
                    new_pe.references = []
                    new_pe.received_amount = pe.unallocated_amount
                    new_pe.paid_amount = pe.unallocated_amount
                    new_pe.unallocated_amount = pe.unallocated_amount
                    
                    new_pe.insert()
                    
                    # 4.3
                    if new_pe.unallocated_amount == 12:
                        fr = frappe.db.sql("""SELECT `name`
                                                FROM `tabFakultative Rechnung`
                                                WHERE `docstatus` = 1
                                                AND `status` = 'Unpaid'
                                                AND `typ` = 'HV'
                                                AND `mv_mitgliedschaft` = '{mv_mitgliedschaft}'""".format(mv_mitgliedschaft=new_pe.mv_mitgliedschaft), as_dict=True)
                        if len(fr) > 0:
                            fr_sinv = create_unpaid_sinv(fr[0].name)
                            sinv = frappe.db.sql("""SELECT `name`, `mv_mitgliedschaft`, `docstatus`, `due_date`, `base_grand_total`, `outstanding_amount`, `customer`
                                                    FROM `tabSales Invoice`
                                                    WHERE `name` = '{fr_sinv}'""".format(fr_sinv=fr_sinv), as_dict=True)[0].name
                        else:
                            mitgliedschaft = new_pe.mv_mitgliedschaft
                            
                            # erstelle fr
                            from mvd.mvd.doctype.fakultative_rechnung.fakultative_rechnung import create_hv_fr
                            fr = create_hv_fr(mitgliedschaft)
                            # erstelle sinv aus fr
                            sinv = create_unpaid_sinv(fr)
                            
                        # match sinv mit pe
                        reference_entry = new_pe.append('references', {})
                        reference_entry.reference_doctype = "Sales Invoice"
                        reference_entry.reference_name = sinv
                        reference_entry.total_amount = frappe.get_value("Sales Invoice", sinv, "base_grand_total")
                        reference_entry.outstanding_amount = frappe.get_value("Sales Invoice", sinv, "outstanding_amount")
                        reference_entry.allocated_amount = reference_entry.outstanding_amount
                        
                        # update unallocated amount
                        new_pe.unallocated_amount = 0
                        new_pe.save()
                        new_pe.submit()
                        master_data['assigned_payments'].append(new_pe.name)
                        master_data['imported_payments'].append(new_pe.name)
                        master_data['submitted_payments'].append(new_pe.name)
                            
                    else:
                        master_data['overpaid'].append(new_pe.name)
                        master_data['assigned_payments'].append(new_pe.name)
                        master_data['unsubmitted_payments'].append(new_pe.name)
                        master_data['imported_payments'].append(new_pe.name)
                        if doppelte_mitgliedschaft:
                            master_data['doppelte_mitgliedschaft'].append(new_pe.name)
                    
                    pe.received_amount = pe.total_allocated_amount
                    pe.paid_amount = pe.total_allocated_amount
                    pe.unallocated_amount = 0
                try:
                    pe.save()
                    master_data['assigned_payments'].append(pe.name)
                
                    if pe.unallocated_amount == 0:
                        pe.submit()
                        master_data['submitted_payments'].append(pe.name)
                    else:
                        master_data['unsubmitted_payments'].append(pe.name)
                except Exception as err:
                    frappe.log_error("{0}\n{1}".format(err, str(pe.as_dict())), "Zahlung konnte nicht verarbeitet werden")
            
            else:
                # 5.
                potenzieller_umzug = False
                if sinv[0].mv_mitgliedschaft:
                    mitgliedschaft = frappe.get_doc("Mitgliedschaft", sinv[0].mv_mitgliedschaft)
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
                                    potenzieller_umzug = sinv[0].name
                
                if potenzieller_umzug:
                    sinv = frappe.db.sql("""SELECT `name`, `mv_mitgliedschaft`, `docstatus`, `due_date`, `base_grand_total`, `outstanding_amount`, `customer`, `company`, `sektion_id`, `debit_to`
                                            FROM `tabSales Invoice`
                                            WHERE `name` = '{potenzieller_umzug}'""".format(potenzieller_umzug=potenzieller_umzug), as_dict=True)
                    
                    pe.party = sinv[0].customer
                    pe.mv_mitgliedschaft = sinv[0].mv_mitgliedschaft
                    pe.company = sinv[0].company
                    pe.sektion_id = sinv[0].sektion_id
                    pe.paid_from = sinv[0].debit_to
                    pe.paid_to = frappe.get_value("Sektion", pe.sektion_id, "account")
                    differenz = pe.paid_amount - paid_amount
                    row = pe.append('deductions', {})
                    row.amount = differenz * -1
                    row.account = frappe.get_value("Sektion", pe.sektion_id, "zwischen_konto")
                    row.cost_center = frappe.get_value("Company", pe.company, "cost_center")
                    
                    pe.save()
                    pe.submit()
                    
                    master_data['gebucht_weggezogen'].append(pe.name)
                    master_data['assigned_payments'].append(pe.name)
                    master_data['submitted_payments'].append(pe.name)
                else:
                    master_data['unsubmitted_payments'].append(pe.name)
                    master_data['unassigned_payments'].append(pe.name)
        else:
            # prüfe allfällige doppelzahlung und weise kunde zu
            qrr = pe.esr_reference
            
            # HACK (zu kurze ERPNext Referenznummern): soll später entfernt werden
            qrr_short = pe.esr_reference[4:27]
            
            sinv = frappe.db.sql("""SELECT `name`, `mv_mitgliedschaft`, `customer`
                                    FROM `tabSales Invoice`
                                    WHERE (REPLACE(`esr_reference`, ' ', '') = '{qrr}' OR REPLACE(`esr_reference`, ' ', '') = '{qrr_short}')""".format(qrr=qrr, qrr_short=qrr_short), as_dict=True)
            
            if not len(sinv) > 0:
                # HACK (alte Debitoren)
                qrr = pe.esr_reference[11:24]
                
                sinv = frappe.db.sql("""SELECT `name`, `mv_mitgliedschaft`, `customer`
                                    FROM `tabSales Invoice`
                                    WHERE `esr_reference` LIKE '%{qrr}%'""".format(qrr=qrr), as_dict=True)
            
            if len(sinv) > 0:
                # Kunde zu Payment Entry zuweisen
                pe.party = sinv[0].customer
                pe.mv_mitgliedschaft = sinv[0].mv_mitgliedschaft
                pe.save()
                master_data['assigned_payments'].append(pe.name)
                master_data['unsubmitted_payments'].append(pe.name)
            else:
                # HACK 2 (alte Debitoren)
                qrr = pe.esr_reference[11:21]
                customers = frappe.db.sql("""SELECT `name`, `kunde_mitglied`, `rg_kunde` FROM `tabMitgliedschaft` WHERE `miveba_buchungen` LIKE '%{qrr}%'""".format(qrr=qrr), as_dict=True)
                if len(customers) > 0:
                    # Kunde zu Payment Entry zuweisen
                    pe.party = customers[0].rg_kunde if customers[0].rg_kunde else customers[0].kunde_mitglied
                    pe.mv_mitgliedschaft = customers[0].name
                    pe.save()
                    master_data['assigned_payments'].append(pe.name)
                    master_data['unsubmitted_payments'].append(pe.name)
                else:
                    master_data['unsubmitted_payments'].append(pe.name)
                    master_data['unassigned_payments'].append(pe.name)
    
    return master_data

# --------------------------------------
# Hilfs-Funktionen
# --------------------------------------
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

def erstelle_master_data():
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
    master_data = {
        'status': 'Open',
        'errors': [],
        'imported_payments': [],
        'unimported_payments': [],
        'assigned_payments': [],
        'unassigned_payments': [],
        'submitted_payments': [],
        'unsubmitted_payments': [],
        'deleted_payments': [],
        'overpaid': [],
        'doppelte_mitgliedschaft': [],
        'gebucht_weggezogen': [],
        'underpaid': [],
        'splittet_overpaid': []
    }
    
    return master_data

def proper_round(number, decimals):
    return float(Decimal(number).quantize(decimals, ROUND_HALF_UP))

def get_default_customer(sektion):
    default_customer = frappe.get_doc("Sektion", sektion).default_customer
    return default_customer

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

# --------------------------------------
# CAMT Aktualisierungs- / CAMT Report Erstellungs- Funktionen
# --------------------------------------

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
    pe_status_update(master_data, camt_import.name)
    return

def pe_status_update(master_data, camt_import):
    if len(master_data['imported_payments']) > 0:
        if len(master_data['imported_payments']) > 1:
            imported_payments = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_import` = '{camt_import}' WHERE `name` IN {pes}""".format(camt_import=camt_import, pes=tuple(master_data['imported_payments'])), as_list=True)
        else:
            imported_payments = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_import` = '{camt_import}' WHERE `name` = '{pes}'""".format(camt_import=camt_import, pes=master_data['imported_payments'][0]), as_list=True)
        if len(master_data['submitted_payments']) > 0:
            if len(master_data['submitted_payments']) > 1:
                submitted_payments = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_status` = 'Verbucht' WHERE `name` IN {pes}""".format(pes=tuple(master_data['submitted_payments'])), as_list=True)
            else:
                submitted_payments = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_status` = 'Verbucht' WHERE `name` = '{pes}'""".format(pes=master_data['submitted_payments'][0]), as_list=True)
        if len(master_data['unassigned_payments']) > 0:
            if len(master_data['unassigned_payments']) > 1:
                unassigned_payments = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_status` = 'Nicht zugewiesen' WHERE `name` IN {pes}""".format(pes=tuple(master_data['unassigned_payments'])), as_list=True)
            else:
                unassigned_payments = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_status` = 'Nicht zugewiesen' WHERE `name` = '{pes}'""".format(pes=master_data['unassigned_payments'][0]), as_list=True)
        if len(master_data['underpaid']) > 0:
            if len(master_data['underpaid']) > 1:
                underpaid = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_status` = 'Unterbezahlt' WHERE `name` IN {pes}""".format(pes=tuple(master_data['underpaid'])), as_list=True)
            else:
                underpaid = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_status` = 'Unterbezahlt' WHERE `name` = '{pes}'""".format(pes=master_data['underpaid'][0]), as_list=True)
        if len(master_data['overpaid']) > 0:
            if len(master_data['overpaid']) > 1:
                overpaid = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_status` = 'Überbezahlt' WHERE `name` IN {pes}""".format(pes=tuple(master_data['overpaid'])), as_list=True)
            else:
                overpaid = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_status` = 'Überbezahlt' WHERE `name` = '{pes}'""".format(pes=master_data['overpaid'][0]), as_list=True)
        if len(master_data['doppelte_mitgliedschaft']) > 0:
            if len(master_data['doppelte_mitgliedschaft']) > 1:
                doppelte_mitgliedschaft = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_status` = 'Doppelte Mitgliedschafts-Zahlung' WHERE `name` IN {pes}""".format(pes=tuple(master_data['doppelte_mitgliedschaft'])), as_list=True)
            else:
                doppelte_mitgliedschaft = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_status` = 'Doppelte Mitgliedschafts-Zahlung' WHERE `name` = '{pes}'""".format(pes=master_data['doppelte_mitgliedschaft'][0]), as_list=True)
        if len(master_data['gebucht_weggezogen']) > 0:
            if len(master_data['gebucht_weggezogen']) > 1:
                gebucht_weggezogen = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_status` = 'Wegzug' WHERE `name` IN {pes}""".format(pes=tuple(master_data['gebucht_weggezogen'])), as_list=True)
            else:
                gebucht_weggezogen = frappe.db.sql("""UPDATE `tabPayment Entry` SET `camt_status` = 'Wegzug' WHERE `name` = '{pes}'""".format(pes=master_data['gebucht_weggezogen'][0]), as_list=True)
    
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
            pes = frappe.db.sql("""SELECT `name` FROM `tabPayment Entry` WHERE `reference_no` LIKE '{unique_reference}%'""".format(unique_reference=unique_reference), as_dict=True)
            for pe in pes:
                try:
                    pe = frappe.get_doc("Payment Entry", pe.name)
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

# --------------------------------------
# Client Whitelist Funktionen
# --------------------------------------
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
        pe.difference_amount = 0
        pe.base_received_amount = new_payment
        pe.received_amount = new_payment
        pe.insert()
        pe.save()
        pe.submit()
        payment_entry.add_comment('Comment', text='Kulanzausgleich erfolgte mittels {0}'.format(pe.name))
        return
    else:
        frappe.throw("Die Rechnung wurde bereits andersweitig beglichen!")

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

@frappe.whitelist()
def sinv_bez_mit_ezs_oder_bar(sinv, ezs=False, bar=False, hv=False, datum=False, betrag=False):
    sinv = frappe.get_doc("Sales Invoice", sinv)
    betrag = float(betrag)
    if betrag > sinv.outstanding_amount:
        frappe.throw("Der Bezahlte Betrag darf die ausstehende Summe nicht überschreiten")
    if hv:
        hv_sinv = create_unpaid_sinv(hv, betrag=12)
    
    customer = sinv.customer
    mitgliedschaft = sinv.mv_mitgliedschaft
    payment_entry_record = frappe.get_doc({
        'doctype': "Payment Entry",
        'posting_date': datum or today(),
        'party_type': 'Customer',
        'party': customer,
        'mv_mitgliedschaft': mitgliedschaft,
        'company': sinv.company,
        'sektion_id': sinv.sektion_id,
        'paid_from': sinv.debit_to,
        'paid_amount': betrag,
        'paid_to': frappe.get_value("Sektion", sinv.sektion_id, "account"),
        'received_amount': betrag,
        'references': [
            {
                'reference_doctype': "Sales Invoice",
                'reference_name': sinv.name,
                'total_amount': sinv.base_grand_total,
                'outstanding_amount': sinv.outstanding_amount,
                'allocated_amount': betrag
            }
        ],
        'reference_no': 'Barzahlung {0}'.format(sinv.name) if bar else 'EZS-Zahlung {0}'.format(sinv.name),
        'reference_date': datum or today()
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
def mitgliedschaft_zuweisen(mitgliedschaft):
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    if mitgliedschaft.rg_kunde:
        return mitgliedschaft.rg_kunde
    else:
        return mitgliedschaft.kunde_mitglied
    
@frappe.whitelist()
def als_hv_verbuchen(pe):
    payment_entry = frappe.get_doc("Payment Entry", pe)
    mitgliedschaft = payment_entry.mv_mitgliedschaft
    
    # erstelle fr
    from mvd.mvd.doctype.fakultative_rechnung.fakultative_rechnung import create_hv_fr
    fr = create_hv_fr(mitgliedschaft)
    # erstelle sinv aus fr
    sinv = create_unpaid_sinv(fr)
    
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
def fr_bez_ezs(fr, datum, betrag):
    betrag = float(betrag)
    hv_sinv = create_unpaid_sinv(fr, betrag=betrag)
    hv_sinv = frappe.get_doc("Sales Invoice", hv_sinv)
    
    customer = hv_sinv.customer
    mitgliedschaft = hv_sinv.mv_mitgliedschaft
    payment_entry_record = frappe.get_doc({
        'doctype': "Payment Entry",
        'posting_date': datum or today(),
        'party_type': 'Customer',
        'party': customer,
        'mv_mitgliedschaft': mitgliedschaft,
        'company': hv_sinv.company,
        'sektion_id': hv_sinv.sektion_id,
        'paid_from': hv_sinv.debit_to,
        'paid_amount': hv_sinv.outstanding_amount,
        'paid_to': frappe.get_value("Sektion", hv_sinv.sektion_id, "account"),
        'received_amount': hv_sinv.outstanding_amount,
        'references': [
            {
                'reference_doctype': "Sales Invoice",
                'reference_name': hv_sinv.name,
                'total_amount': hv_sinv.base_grand_total,
                'outstanding_amount': hv_sinv.outstanding_amount,
                'allocated_amount': hv_sinv.outstanding_amount
            }
        ],
        'reference_no': 'EZS-Zahlung {0}'.format(hv_sinv.name),
        'reference_date': datum or today()
    }).insert()
    
    payment_entry_record.submit()
    
    return

@frappe.whitelist()
def fr_bez_bar(fr, datum):
    fr = frappe.get_doc("Fakultative Rechnung", fr)
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", fr.mv_mitgliedschaft)
    sektion = frappe.get_doc("Sektion", mitgliedschaft.sektion_id)
    company = frappe.get_doc("Company", sektion.company)
    
    if not mitgliedschaft.rg_kunde:
        customer = mitgliedschaft.kunde_mitglied
        contact = mitgliedschaft.kontakt_mitglied
        if not mitgliedschaft.rg_adresse:
            address = mitgliedschaft.adresse_mitglied
        else:
            address = mitgliedschaft.rg_adresse
    else:
        customer = mitgliedschaft.rg_kunde_mitglied
        address = mitgliedschaft.rg_adresse_mitglied
        contact = mitgliedschaft.rg_kontakt_mitglied
    
    item = [{"item_code": sektion.hv_artikel, "qty": 1, "rate": sektion.betrag_hv}]
    
    sinv = frappe.get_doc({
        "doctype": "Sales Invoice",
        "posting_date": datum or today(),
        "set_posting_time": 1,
        "ist_mitgliedschaftsrechnung": 0,
        "ist_hv_rechnung": 1 if fr.typ == 'HV' else 0,
        "ist_spenden_rechnung": 0 if fr.typ == 'HV' else 1,
        "mv_mitgliedschaft": fr.mv_mitgliedschaft,
        "company": sektion.company,
        "cost_center": company.cost_center,
        "customer": customer,
        "customer_address": address,
        "contact_person": contact,
        'mitgliedschafts_jahr': int(getdate(today()).strftime("%Y")),
        'due_date': add_days(today(), 30),
        'debit_to': company.default_receivable_account,
        'sektions_code': str(sektion.sektion_id) or '00',
        'sektion_id': fr.sektion_id,
        "items": item,
        "inkl_hv": 0,
        "esr_reference": fr.qrr_referenz or get_qrr_reference(fr=fr.name)
    })
    sinv.insert(ignore_permissions=True)
    
    pos_profile = frappe.get_doc("POS Profile", sektion.pos_barzahlung)
    sinv.is_pos = 1
    sinv.pos_profile = pos_profile.name
    row = sinv.append('payments', {})
    row.mode_of_payment = pos_profile.payments[0].mode_of_payment
    row.account = pos_profile.payments[0].account
    row.type = pos_profile.payments[0].type
    row.amount = sinv.grand_total
    sinv.save(ignore_permissions=True)
    
    # submit workaround weil submit ignore_permissions=True nicht kennt
    sinv.docstatus = 1
    sinv.save(ignore_permissions=True)
    
    fr.status = 'Paid'
    fr.bezahlt_via = sinv.name
    fr.save(ignore_permissions=True)
    
    return

@frappe.whitelist()
def reopen_payment_as_admin(pe):
    frappe.db.sql("""UPDATE `tabPayment Entry` SET `docstatus` = 0 WHERE `name` = '{pe}'""".format(pe=pe), as_list=True)
    return

@frappe.whitelist()
def reopen_sinv_as_admin(sinv):
    frappe.db.sql("""UPDATE `tabSales Invoice` SET `docstatus` = 0 WHERE `name` = '{sinv}'""".format(sinv=sinv), as_list=True)
    return
