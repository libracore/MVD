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
    # lese und prüfe camt file
    camt_file = get_camt_file(file_path, test=True)
    if not camt_file:
        camt_status_update(camt_import, 'Failed')
        return
    
    args = {
        'camt_file': file_path,
        'camt_import': camt_import
    }
    enqueue("mvd.mvd.doctype.camt_import.camt_import.verarbeite_camt_file", queue='long', job_name='Verarbeite CAMT Import {0}'.format(camt_import), timeout=5000, **args)

def verarbeite_camt_file(camt_file, camt_import):
    # lese und prüfe camt file
    camt_file = get_camt_file(camt_file)
    
    # Zahlungen von CAMT-File einlesen
    zahlungen_einlesen(camt_file, camt_import)

def zahlungen_einlesen(camt_file, camt_import):
    """
    Diese Funktion list das CAMT-File aus und erzeugt für alle darin enthaltenen Eingangszahlungen einen Payment Entry
    """
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
                    # erfasse ausgelesene Zahlung in CAMT-Import
                    erfasse_ausgelesene_zahlungen(transaction_reference, unique_reference, date, amount, camt_import.name)
                    
                    # suche nach Sales Invoice oder Fakultative Rechnung anhand QRR-Referenz
                    sinv_lookup_data = sinv_lookup(transaction_reference, amount)
                    
                    # erfasse Payment Entry
                    erstelle_zahlung(sinv_lookup=sinv_lookup_data, date=date, to_account=account, received_amount=amount, 
                        transaction_id=unique_reference, remarks="QRR: {0}, {1}, {2}, IBAN: {3}".format(
                        transaction_reference, customer_name, customer_address, customer_iban), company=company, sektion=sektion, qrr=transaction_reference, camt_import=camt_import.name)
            except Exception as e:
                # Zahlung konnte nicht ausgelesen werden, entsprechender Errorlog im CAMT-File wird erzeugt
                erfasse_fehlgeschlagenes_auslesen(six.text_type(transaction), e, camt_import.name)
                pass
    
    camt_status_update(camt_import.name, 'Zahlungen eingelesen - verbuche Matches')
    frappe.db.commit()
    verbuche_matches(camt_import.name)
    return

def sinv_lookup(qrr_ref, betrag):
    """
    Diese Funktion sucht nach gebuchten Sales Invoices anhand der QRR-Referenznummer aus der CAMT-Zahlung
    
    Mögliche Antwort Cases:
    -----------------------
    - Check: True & info: Sinv Match
        -> Zahlung wird erstellt und gegen Sinv verbucht (insofern Sinv unbezahlt)
    
    - Check: False & info: Multi-Sinvs
        -> Unzugewiesene Zahlung wird erstellt
    
    - Check: False & info: No Sinvs
        -> Unzugewiesene Zahlung wird erstellt
    
    - Check: False & info: Paid Fak
        -> Zugewiesene, aber unverbuchte Zahlung wird erstellt
    """
    sinvs = frappe.db.sql("""SELECT *
                            FROM `tabSales Invoice`
                            WHERE `docstatus` = 1
                            AND REPLACE(`esr_reference`, ' ', '') = '{qrr_ref}'""".format(qrr_ref=qrr_ref), as_dict=True)
    
    if len(sinvs) > 0:
        # Sinv gefunden
        if len(sinvs) > 1:
            # mehere Sinvs gefunden -> erzeuge unzugewiesene Zahlung
            return {
                'check': False,
                'info': 'Multi-Sinvs',
                'sinv': ''
            }
        else:
            # unique match -> erzeuge Zahlung
            return {
                'check': True,
                'info': 'Sinv Match',
                'sinv': sinvs[0].name
            }
    else:
        # sinv nicht gefunden, starte suche nach Fakultativer Rechnung
        return fak_lookup(qrr_ref, betrag)

def fak_lookup(qrr_ref, betrag):
    """
    Diese Funktion sucht nach gebuchten Fakultativen Rechnungen anhand der QRR-Referenznummer aus der CAMT-Zahlung
    """
    faks = frappe.db.sql("""SELECT *
                            FROM `tabFakultative Rechnung`
                            WHERE `docstatus` = 1
                            AND REPLACE(`qrr_referenz`, ' ', '') = '{qrr_ref}'""".format(qrr_ref=qrr_ref), as_dict=True)
    
    if len(faks) > 0:
        # FK gefunden
        if len(faks) > 1:
            # mehere Fakultative Rechungen gefunden -> erzeuge unzugewiesene Zahlung
            return {
                'check': False,
                'info': 'Multi-Sinvs',
                'sinv': ''
            }
        else:
            # unique match -> umwandlung Fakultative Rechnung in Sales Invoice
            return create_unpaid_sinv(faks[0].name, betrag)
    else:
        # FK nicht gefunden -> erzeuge unzugewiesene Zahlung
        return {
            'check': False,
            'info': 'No Sinv',
            'sinv': ''
        }

def create_unpaid_sinv(fak, betrag):
    """
    Diese Funktion wandelt durch den Zahlungsdatensatz gefundene Fakultative Rechnungen in Sales Invoices um
    """
    fak_doc = frappe.get_doc("Fakultative Rechnung", fak)
    if fak_doc.status == 'Unpaid':
        # umwandlung Fakultative Rechnung in Sales Invoice
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", fak_doc.mv_mitgliedschaft)
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
            customer = mitgliedschaft.rg_kunde
            address = mitgliedschaft.rg_adresse
            contact = mitgliedschaft.rg_kontakt
        
        if fak_doc.typ == 'HV':
            betrag = sektion.betrag_hv
            item = [{"item_code": sektion.hv_artikel, "qty": 1, "rate": fak_doc.betrag}]
        else:
            item = [{"item_code": sektion.spenden_artikel, "qty": 1, "rate": betrag}]
        sinv = frappe.get_doc({
            "doctype": "Sales Invoice",
            "ist_mitgliedschaftsrechnung": 0,
            "ist_hv_rechnung": 1 if fak_doc.typ == 'HV' else 0,
            "ist_spenden_rechnung": 0 if fak_doc.typ == 'HV' else 1,
            "mv_mitgliedschaft": fak_doc.mv_mitgliedschaft,
            "company": sektion.company,
            "cost_center": company.cost_center,
            "customer": customer,
            "customer_address": address,
            "contact_person": contact,
            'mitgliedschafts_jahr': fak_doc.bezugsjahr if fak_doc.bezugsjahr and fak_doc.bezugsjahr > 0 else int(getdate(today()).strftime("%Y")),
            'due_date': add_days(today(), 30),
            'debit_to': company.default_receivable_account,
            'sektions_code': str(sektion.sektion_id) or '00',
            'sektion_id': fak_doc.sektion_id,
            "items": item,
            "inkl_hv": 0,
            "esr_reference": fak_doc.qrr_referenz or get_qrr_reference(fr=fak_doc.name)
        })
        sinv.insert(ignore_permissions=True)
        
        # submit workaround weil submit ignore_permissions=True nicht kennt
        sinv.docstatus = 1
        sinv.save(ignore_permissions=True)
        
        fak_doc.status = 'Paid'
        fak_doc.bezahlt_via = sinv.name
        fak_doc.save(ignore_permissions=True)
        return {
                'check': True,
                'info': 'Sinv Match',
                'sinv': sinv.name
            }
    else:
        # Fakultative Rechnung wurde bereits beglichen -> erzeuge ungebuchte, aber zugewiesene Zahlung
        return {
            'check': False,
            'info': 'Paid Fak',
            'sinv': fak_doc.name
        }

def erstelle_zahlung(sinv_lookup, date, to_account, received_amount, transaction_id, remarks, company, sektion, qrr, camt_import):
    """
    Diese Funktion erzeugt einen Payment Entry, insofern noch kein Payment Entry mit der selben Transaktions-ID der Bank vorhanden ist
    """
    if sinv_lookup['check']:
        sinv = frappe.get_doc("Sales Invoice", sinv_lookup['sinv'])
        customer = sinv.customer
        sektion = sinv.sektion_id
        company = sinv.company
        mitgliedschaft = sinv.mv_mitgliedschaft
        mv_kunde = sinv.mv_kunde
        payment_match_status = 'Rechnungs Match'
    else:
        # get default customer
        customer = get_default_customer(sektion)
        mitgliedschaft = None
        mv_kunde = None
        payment_match_status = 'Nicht zugewiesen'
    
    if sektion:
        to_account = frappe.db.get_value('Sektion', sektion, 'account')
    
    # erstelle Zahlung wenn noch nicht vorhanden
    if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}):
        # create new payment entry
        new_payment_entry = frappe.get_doc({'doctype': 'Payment Entry'})
        new_payment_entry.payment_type = "Receive"
        new_payment_entry.party_type = "Customer"
        new_payment_entry.party = customer
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
        new_payment_entry.camt_import = camt_import
        new_payment_entry.mv_mitgliedschaft = mitgliedschaft
        new_payment_entry.mv_kunde = mv_kunde
        new_payment_entry.camt_status = payment_match_status
        
        inserted_payment_entry = new_payment_entry.insert()
        
        # erfasse eingelesene Zahlung in CAMT-Import
        erfasse_eingelesene_zahlungen(qrr, transaction_id, date, received_amount, camt_import, sinv_lookup['check'])
        return
    else:
        # erfasse nicht eingelesene Zahlung in CAMT-Import
        erfasse_nicht_eingelesene_zahlungen(qrr, transaction_id, date, received_amount, camt_import)
        return

def verbuche_matches(camt_import):
    """
    Diese Funktion verbucht (und ggf. splittet (bei Überzahlungen)) alle Payment Entries welche einer Sales Invoice zugeordnet werden konnten
    """
    pes = frappe.db.sql("""SELECT
                                `name`
                            FROM `tabPayment Entry`
                            WHERE `docstatus` = 0
                            AND `camt_import` = '{camt_import}'""".format(camt_import=camt_import), as_dict=True)
    
    for pe in pes:
        pe_doc = frappe.get_doc("Payment Entry", pe.name)
        sinv = frappe.db.sql("""SELECT
                                    `name`
                                FROM `tabSales Invoice`
                                WHERE `docstatus` = 1
                                AND REPLACE(`esr_reference`, ' ', '') = '{qrr}'""".format(qrr=pe_doc.esr_reference), as_dict=True)
        if len(sinv) > 0:
            sinv_doc = frappe.get_doc("Sales Invoice", sinv[0].name)
            
            if sinv_doc.ist_mitgliedschaftsrechnung:
                camt_mitgliedschaften_update(camt_import)
            elif sinv_doc.ist_hv_rechnung:
                camt_hv_update(camt_import)
            elif sinv_doc.ist_spenden_rechnung:
                camt_spenden_update(camt_import)
            elif sinv_doc.ist_sonstige_rechnung:
                camt_produkte_update(camt_import)
            
            if pe_doc.paid_amount <= sinv_doc.outstanding_amount:
                # Teilzahlung oder vollständige Bezahlung
                row = pe_doc.append('references', {})
                row.reference_doctype = "Sales Invoice"
                row.reference_name = sinv_doc.name
                row.due_date = sinv_doc.due_date
                row.total_amount = sinv_doc.base_grand_total
                row.outstanding_amount = sinv_doc.outstanding_amount
                row.allocated_amount = pe_doc.paid_amount
                pe_doc.total_allocated_amount = pe_doc.paid_amount
                pe_doc.unallocated_amount = 0
                pe_doc.camt_status = 'Verbucht'
                pe_doc.save()
                pe_doc.submit()
                camt_gebuchte_zahlung_update(camt_import)
            else:
                # Überzahlung (Splitten)
                ueberzahlung = frappe.copy_doc(pe_doc)
                ueberzahlung.paid_amount = (pe_doc.paid_amount - sinv_doc.outstanding_amount) * -1
                ueberzahlung.camt_status = 'Überbezahlt'
                ueberzahlung.insert()
                
                camt_ueberzahlung_update(camt_import)
                
                pe_doc.paid_amount = sinv_doc.outstanding_amount
                row = pe_doc.append('references', {})
                row.reference_doctype = "Sales Invoice"
                row.reference_name = sinv_doc.name
                row.due_date = sinv_doc.due_date
                row.total_amount = sinv_doc.base_grand_total
                row.outstanding_amount = sinv_doc.outstanding_amount
                row.allocated_amount = pe_doc.paid_amount
                pe_doc.total_allocated_amount = pe_doc.paid_amount
                pe_doc.unallocated_amount = 0
                pe_doc.camt_status = 'Verbucht'
                pe_doc.save()
                pe_doc.submit()
                camt_gebuchte_zahlung_update(camt_import)
    
    camt_status_update(camt_import, 'Verarbeitet')

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

def get_default_customer(sektion):
    default_customer = frappe.get_doc("Sektion", sektion).default_customer
    return default_customer

def erfasse_ausgelesene_zahlungen(transaction_reference, unique_reference, date, received_amount, camt_import):
    ausgelesene_zahlungen = frappe.db.get_value('CAMT Import', camt_import, 'ausgelesene_zahlungen')
    qty = frappe.db.get_value('CAMT Import', camt_import, 'ausgelesene_zahlungen_qty') + 1
    if ausgelesene_zahlungen:
        ausgelesene_zahlungen += '\n{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    else:
        ausgelesene_zahlungen = '{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    frappe.db.set_value('CAMT Import', camt_import, 'ausgelesene_zahlungen', ausgelesene_zahlungen)
    frappe.db.set_value('CAMT Import', camt_import, 'ausgelesene_zahlungen_qty', qty)

def erfasse_eingelesene_zahlungen(transaction_reference, unique_reference, date, received_amount, camt_import, sinv_match):
    eingelesene_zahlungen = frappe.db.get_value('CAMT Import', camt_import, 'eingelesene_zahlungen')
    qty = frappe.db.get_value('CAMT Import', camt_import, 'eingelesene_zahlungen_qty') + 1
    if eingelesene_zahlungen:
        eingelesene_zahlungen += '\n{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    else:
        eingelesene_zahlungen = '{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    frappe.db.set_value('CAMT Import', camt_import, 'eingelesene_zahlungen', eingelesene_zahlungen)
    frappe.db.set_value('CAMT Import', camt_import, 'eingelesene_zahlungen_qty', qty)
    if sinv_match:
        match_qty = frappe.db.get_value('CAMT Import', camt_import, 'rg_match_qty') + 1
        frappe.db.set_value('CAMT Import', camt_import, 'rg_match_qty', match_qty)

def erfasse_nicht_eingelesene_zahlungen(transaction_reference, unique_reference, date, received_amount, camt_import):
    nicht_eingelesene_zahlungen = frappe.db.get_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen')
    qty = frappe.db.get_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen_qty') + 1
    if nicht_eingelesene_zahlungen:
        nicht_eingelesene_zahlungen += '\n{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    else:
        nicht_eingelesene_zahlungen = '{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    frappe.db.set_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen', nicht_eingelesene_zahlungen)
    frappe.db.set_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen_qty', qty)

def camt_status_update(camt_import, status):
    frappe.db.set_value('CAMT Import', camt_import, 'status', status)

def camt_gebuchte_zahlung_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'verbuchte_zahlung_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'verbuchte_zahlung_qty', qty)

def camt_ueberzahlung_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'ueberzahlung_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'ueberzahlung_qty', qty)

def erfasse_fehlgeschlagenes_auslesen(transaction, err, camt_import):
    fehlgeschlagenes_auslesen = frappe.db.get_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen')
    qty = frappe.db.get_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen_qty') + 1
    if fehlgeschlagenes_auslesen:
        fehlgeschlagenes_auslesen += '\n{0}\n{1}\n-----------------------------'.format(transaction, err)
    else:
        fehlgeschlagenes_auslesen = '{0}\n{1}\n-----------------------------'.format(transaction, err)
    frappe.db.set_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen', fehlgeschlagenes_auslesen)
    frappe.db.set_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen_qty', qty)

def camt_mitgliedschaften_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'mitgliedschaften_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'mitgliedschaften_qty', qty)

def camt_hv_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'hv_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'hv_qty', qty)

def camt_spenden_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'spenden_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'spenden_qty', qty)

def camt_produkte_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'produkte_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'produkte_qty', qty)
