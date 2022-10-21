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
    
    # Verbuche Matches
    try:
        verbuche_matches(camt_import)
    except Exception as err:
        camt_status_update(camt_import, 'Failed')
        frappe.log_error("{0}".format(err), 'CAMT-Import {0} failed'.format(camt_import))
    
    # Aktualisiere CAMT Übersicht
    aktualisiere_camt_uebersicht(camt_import)

def zahlungen_einlesen(camt_file, camt_import):
    """
    Diese Funktion list das CAMT-File aus und erzeugt für alle darin enthaltenen Eingangszahlungen einen Payment Entry
    """
    camt_import = frappe.get_doc("CAMT Import", camt_import)
    account = camt_import.account
    sektion = camt_import.sektion_id
    company = camt_import.company
    
    transaction_entries = camt_file.find_all('ntry')
    
    frappe.db.set_value('CAMT Import', camt_import.name, 'camt_file_datum', frappe.utils.get_datetime(camt_file.document.bktocstmrdbtcdtntfctn.grphdr.credttm.get_text().split("T")[0]).strftime('%Y-%m-%d'))
    
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
                try:
                    camt_amount = float(frappe.db.get_value('CAMT Import', camt_import.name, 'camt_amount')) + amount
                    frappe.db.set_value('CAMT Import', camt_import.name, 'camt_amount', camt_amount)
                except:
                    pass
                currency = transaction_soup.amt['ccy']
                try:
                    camt_taxes = float(frappe.db.get_value('CAMT Import', camt_import.name, 'camt_taxen')) + float(transaction_soup.chrgs.ttlchrgsandtaxamt.get_text())
                    frappe.db.set_value('CAMT Import', camt_import.name, 'camt_taxen', camt_taxes)
                except:
                    pass
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
                            AND (
                                REPLACE(`esr_reference`, ' ', '') = '{qrr_ref}'
                                OR
                                REPLACE(`esr_reference`, ' ', '') = '{qrr_ref_short}'
                            )
                            AND `outstanding_amount` > 0""".format(qrr_ref=qrr_ref, qrr_ref_short=qrr_ref[8:27]), as_dict=True)
    
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
                            AND REPLACE(`qrr_referenz`, ' ', '') = '{qrr_ref}'
                            AND `status` = 'Unpaid'""".format(qrr_ref=qrr_ref), as_dict=True)
    
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
                                AND (
                                    REPLACE(`esr_reference`, ' ', '') = '{qrr}'
                                    OR
                                    REPLACE(`esr_reference`, ' ', '') = '{qrr_ref_short}'
                                )
                                AND `outstanding_amount` > 0""".format(qrr=pe_doc.esr_reference, qrr_ref_short=pe_doc.esr_reference[8:27]), as_dict=True)
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
            
            if pe_doc.paid_amount <= sinv_doc.outstanding_amount or sinv_doc.ist_spenden_rechnung:
                # Teilzahlung oder vollständige Bezahlung
                row = pe_doc.append('references', {})
                row.reference_doctype = "Sales Invoice"
                row.reference_name = sinv_doc.name
                row.due_date = sinv_doc.due_date
                row.total_amount = sinv_doc.base_grand_total
                row.outstanding_amount = sinv_doc.outstanding_amount
                row.allocated_amount = pe_doc.paid_amount
                
                # bei Spendenrechnungen muss der gesammte (gerundete!) Betrag ausgeglichen werden
                # Hierzu muss ggf. eine Rundungsdifferenz abgeschrieben werden
                if sinv_doc.ist_spenden_rechnung:
                    if sinv_doc.outstanding_amount > sinv_doc.base_grand_total:
                        row.allocated_amount = sinv_doc.outstanding_amount
                        deductions_row = pe_doc.append('deductions', {})
                        deductions_row.account = frappe.db.get_value('Company', sinv_doc.company, 'write_off_account')
                        deductions_row.cost_center = frappe.db.get_value('Company', sinv_doc.company, 'cost_center')
                        deductions_row.amount = sinv_doc.rounding_adjustment
                    else:
                        row.allocated_amount = sinv_doc.outstanding_amount
                        deductions_row = pe_doc.append('deductions', {})
                        deductions_row.account = frappe.db.get_value('Company', sinv_doc.company, 'write_off_account')
                        deductions_row.cost_center = frappe.db.get_value('Company', sinv_doc.company, 'cost_center')
                        deductions_row.amount = sinv_doc.rounding_adjustment
                
                pe_doc.total_allocated_amount = pe_doc.paid_amount
                pe_doc.unallocated_amount = 0
                pe_doc.camt_status = 'Verbucht'
                pe_doc.save()
                pe_doc.submit()
                camt_gebuchte_zahlung_update(camt_import)
            else:
                # Überzahlung (Splitten)
                ueberzahlung = frappe.copy_doc(pe_doc)
                ueberzahlung.paid_amount = (pe_doc.paid_amount - sinv_doc.outstanding_amount)
                ueberzahlung.received_amount = ueberzahlung.paid_amount
                ueberzahlung.base_received_amount = ueberzahlung.paid_amount
                ueberzahlung.camt_status = 'Überbezahlt'
                ueberzahlung.insert()
                
                verabreite_ueberzahlung(camt_import, ueberzahlung, sinv_doc)
                
                camt_ueberzahlung_update(camt_import)
                
                pe_doc.paid_amount = sinv_doc.outstanding_amount
                pe_doc.received_amount = sinv_doc.outstanding_amount
                pe_doc.base_received_amount = sinv_doc.outstanding_amount
                row = pe_doc.append('references', {})
                row.reference_doctype = "Sales Invoice"
                row.reference_name = sinv_doc.name
                row.due_date = sinv_doc.due_date
                row.total_amount = sinv_doc.base_grand_total
                row.outstanding_amount = sinv_doc.outstanding_amount
                row.allocated_amount = pe_doc.paid_amount
                pe_doc.total_allocated_amount = pe_doc.paid_amount
                pe_doc.unallocated_amount = 0
                pe_doc.difference_amount = 0
                pe_doc.camt_status = 'Verbucht'
                pe_doc.save()
                pe_doc.submit()
                camt_gebuchte_zahlung_update(camt_import)
    
    camt_status_update(camt_import, 'Verarbeitet')

def verabreite_ueberzahlung(camt_import, ueberzahlung, sinv_doc):
    from mvd.mvd.utils.manuelle_rechnungs_items import get_item_price
    hv_item = frappe.db.get_value('Sektion', ueberzahlung.sektion_id, 'hv_artikel')
    mitgliedschaft_item = frappe.db.get_value('Sektion', ueberzahlung.sektion_id, 'mitgliedschafts_artikel')
    hv_item_price = get_item_price(hv_item)
    mitgliedschaft_item_price = get_item_price(mitgliedschaft_item)
    
    if int(sinv_doc.ist_sonstige_rechnung) == 1:
        if ueberzahlung.paid_amount == mitgliedschaft_item_price:
            # TBD !!!
            return
        else:
            camt_zugewiesen_nicht_verbucht_update(camt_import)
            return
    elif int(sinv_doc.ist_mitgliedschaftsrechnung) == 1:
        if ueberzahlung.paid_amount == hv_item_price:
            mitgliedschaftsjahr = int(frappe.db.get_value('Mitgliedschaft', sinv_doc.mv_mitgliedschaft, 'bezahltes_mitgliedschaftsjahr'))
            if mitgliedschaftsjahr < int(sinv_doc.mitgliedschafts_jahr):
                mitgliedschaftsjahr = int(sinv_doc.mitgliedschafts_jahr)
            if int(frappe.db.get_value('Mitgliedschaft', sinv_doc.mv_mitgliedschaft, 'zahlung_hv')) < mitgliedschaftsjahr:
                # create new HV RG
                sektion = frappe.get_doc("Sektion", sinv_doc.sektion_id)
                fr = frappe.get_doc({
                    "doctype": "Fakultative Rechnung",
                    "mv_mitgliedschaft": sinv_doc.mv_mitgliedschaft,
                    'due_date': add_days(today(), 30),
                    'sektion_id': str(sektion.name),
                    'sektions_code': str(sektion.sektion_id) or '00',
                    'sales_invoice': None,
                    'typ': 'HV',
                    'betrag': hv_item_price,
                    'posting_date': today(),
                    'company': sektion.company,
                    'druckvorlage': '',
                    'bezugsjahr': mitgliedschaftsjahr
                })
                fr.insert(ignore_permissions=True)
                fr.submit()
                unpaid_sinv = create_unpaid_sinv(fr.name, hv_item_price)['sinv']
                
                row = ueberzahlung.append('references', {})
                row.reference_doctype = "Sales Invoice"
                row.reference_name = unpaid_sinv
                row.due_date = add_days(today(), 30)
                row.total_amount = hv_item_price
                row.outstanding_amount = hv_item_price
                row.allocated_amount = hv_item_price
                ueberzahlung.total_allocated_amount = hv_item_price
                ueberzahlung.unallocated_amount = 0
                ueberzahlung.difference_amount = 0
                ueberzahlung.save()
                ueberzahlung.submit()
                camt_gebuchte_zahlung_update(camt_import)
                camt_hv_update(camt_import)
            else:
                camt_zugewiesen_nicht_verbucht_update(camt_import)
                return
        else:
            camt_zugewiesen_nicht_verbucht_update(camt_import)
            return
    elif int(sinv_doc.ist_hv_rechnung) == 1:
        if ueberzahlung.paid_amount == hv_item_price:
            mitgliedschaftsjahr = int(frappe.db.get_value('Mitgliedschaft', sinv_doc.mv_mitgliedschaft, 'bezahltes_mitgliedschaftsjahr'))
            if int(sinv_doc.mitgliedschafts_jahr) < mitgliedschaftsjahr:
                # create new HV RG
                sektion = frappe.get_doc("Sektion", sinv_doc.sektion_id)
                fr = frappe.get_doc({
                    "doctype": "Fakultative Rechnung",
                    "mv_mitgliedschaft": sinv_doc.mv_mitgliedschaft,
                    'due_date': add_days(today(), 30),
                    'sektion_id': str(sektion.name),
                    'sektions_code': str(sektion.sektion_id) or '00',
                    'sales_invoice': None,
                    'typ': 'HV',
                    'betrag': hv_item_price,
                    'posting_date': today(),
                    'company': sektion.company,
                    'druckvorlage': '',
                    'bezugsjahr': mitgliedschaftsjahr
                })
                fr.insert(ignore_permissions=True)
                fr.submit()
                unpaid_sinv = create_unpaid_sinv(fr.name, hv_item_price)['sinv']
                
                row = ueberzahlung.append('references', {})
                row.reference_doctype = "Sales Invoice"
                row.reference_name = unpaid_sinv
                row.due_date = add_days(today(), 30)
                row.total_amount = hv_item_price
                row.outstanding_amount = hv_item_price
                row.allocated_amount = hv_item_price
                ueberzahlung.total_allocated_amount = hv_item_price
                ueberzahlung.unallocated_amount = 0
                ueberzahlung.difference_amount = 0
                ueberzahlung.save()
                ueberzahlung.submit()
                camt_gebuchte_zahlung_update(camt_import)
                camt_hv_update(camt_import)
            else:
                camt_zugewiesen_nicht_verbucht_update(camt_import)
                return
        else:
            camt_zugewiesen_nicht_verbucht_update(camt_import)
            return
    else:
        camt_zugewiesen_nicht_verbucht_update(camt_import)
        return

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
    else:
        no_match_qty = frappe.db.get_value('CAMT Import', camt_import, 'anz_unmatched_payments') + 1
        frappe.db.set_value('CAMT Import', camt_import, 'anz_unmatched_payments', no_match_qty)

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

def camt_zugewiesen_nicht_verbucht_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'zugewiesen_unverbucht_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'zugewiesen_unverbucht_qty', qty)

@frappe.whitelist()
def suche_mitgliedschaft_aus_pe(payment_entry):
    data = []
    pe = frappe.get_doc("Payment Entry", payment_entry)
    try:
        # suche alte Zahlungen anhand IBAN
        remarks = pe.remarks_clone.split("IBAN: ")[1]
        if len(remarks) > 0:
            other_pes = frappe.db.sql("""SELECT
                                            `mv_mitgliedschaft` AS `mitgliedschaft`
                                        FROM `tabPayment Entry`
                                        WHERE `remarks_clone` LIKE '%{remarks}%'
                                        AND `name` != '{pe}'
                                        AND `mv_mitgliedschaft` IS NOT NULL""".format(remarks=remarks, pe=pe.name), as_dict=True)
            if len(other_pes) > 0:
                for entry in other_pes:
                    unabhaengiger_debitor = frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'unabhaengiger_debitor')
                    if int(unabhaengiger_debitor) == 1:
                        data.append({
                            'vorname': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'rg_vorname') or '',
                            'nachname': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'rg_nachname') or '',
                            'firma': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'rg_firma') or '',
                            'sektion': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'sektion_id') or '',
                            'status': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'status_c') or '',
                            'mitgliedschaft': entry.mitgliedschaft,
                            'quelle': 'IBAN'
                        })
                    else:
                        data.append({
                            'vorname': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'vorname_1') or '',
                            'nachname': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'nachname_1') or '',
                            'firma': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'firma') or '',
                            'sektion': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'sektion_id') or '',
                            'status': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'status_c') or '',
                            'mitgliedschaft': entry.mitgliedschaft,
                            'quelle': 'IBAN'
                        })
    except:
        pass
    
    # suche alte Rechnungen anhand QRR-Referenz
    alte_rechnungen = frappe.db.sql("""SELECT
                                        `mv_mitgliedschaft` AS `mitgliedschaft`
                                    FROM `tabSales Invoice`
                                    WHERE REPLACE(`esr_reference`, ' ', '') LIKE '%{qrr}%'
                                    AND `mv_mitgliedschaft` IS NOT NULL""".format(qrr=pe.esr_reference), as_dict=True)
    if len(alte_rechnungen) > 0:
        for entry in alte_rechnungen:
            unabhaengiger_debitor = frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'unabhaengiger_debitor')
            if int(unabhaengiger_debitor) == 1:
                data.append({
                    'vorname': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'rg_vorname') or '',
                    'nachname': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'rg_nachname') or '',
                    'firma': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'rg_firma') or '',
                    'sektion': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'sektion_id') or '',
                    'status': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'status_c') or '',
                    'mitgliedschaft': entry.mitgliedschaft,
                        'quelle': 'Rechnung'
                })
            else:
                data.append({
                    'vorname': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'vorname_1') or '',
                    'nachname': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'nachname_1') or '',
                    'firma': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'firma') or '',
                    'sektion': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'sektion_id') or '',
                    'status': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'status_c') or '',
                    'mitgliedschaft': entry.mitgliedschaft,
                        'quelle': 'Rechnung'
                })
    
    # suche Fakultative Rechnungen anhand QRR-Referenz
    alte_rechnungen = frappe.db.sql("""SELECT
                                        `mv_mitgliedschaft` AS `mitgliedschaft`
                                    FROM `tabFakultative Rechnung`
                                    WHERE REPLACE(`qrr_referenz`, ' ', '') LIKE '%{qrr}%'
                                    AND `mv_mitgliedschaft` IS NOT NULL""".format(qrr=pe.esr_reference), as_dict=True)
    if len(alte_rechnungen) > 0:
        for entry in alte_rechnungen:
            unabhaengiger_debitor = frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'unabhaengiger_debitor')
            if int(unabhaengiger_debitor) == 1:
                data.append({
                    'vorname': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'rg_vorname') or '',
                    'nachname': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'rg_nachname') or '',
                    'firma': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'rg_firma') or '',
                    'sektion': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'sektion_id') or '',
                    'status': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'status_c') or '',
                    'mitgliedschaft': entry.mitgliedschaft,
                        'quelle': 'Fakultative Rechnung'
                })
            else:
                data.append({
                    'vorname': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'vorname_1') or '',
                    'nachname': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'nachname_1') or '',
                    'firma': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'firma') or '',
                    'sektion': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'sektion_id') or '',
                    'status': frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'status_c') or '',
                    'mitgliedschaft': entry.mitgliedschaft,
                        'quelle': 'Fakultative Rechnung'
                })
    
    return data

@frappe.whitelist()
def mitgliedschaft_zuweisen(mitgliedschaft):
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    if mitgliedschaft.rg_kunde:
        return {
            'mitgliedschaft': mitgliedschaft.name,
            'customer': mitgliedschaft.rg_kunde
        }
    else:
        return {
            'mitgliedschaft': mitgliedschaft.name,
            'customer': mitgliedschaft.kunde_mitglied
        }

@frappe.whitelist()
def aktualisiere_camt_uebersicht(camt_import):
    # verbuchte Zahlungen
    verbuchte_zahlungen = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 1""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'verbuchte_zahlung_qty', verbuchte_zahlungen)
    
    # nicht zugewiesene Zahlungen
    nicht_zugewiesene_zahlungen = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 0
                                            AND `camt_status` = 'Nicht zugewiesen'""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'anz_unmatched_payments', nicht_zugewiesene_zahlungen)
    
    # zugewiesene aber unverbuchte Zahlungen
    zugewiesen_unverbucht_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 0
                                            AND `mv_mitgliedschaft` IS NOT NULL""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'zugewiesen_unverbucht_qty', zugewiesen_unverbucht_qty)
    
    # Verbuchte Zahlungen welche ein Guthaben auslösen
    guthaben_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 1
                                            AND `unallocated_amount` > 0""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'guthaben_qty', guthaben_qty)
    
    # Stornierte Zahlungen
    storno_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 2""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'stornierte_zahlungen_qty', storno_qty)
    
    # HV, Mitgliedschaften, Produkte und Spenden
    gebuchte_pes = frappe.db.sql("""SELECT `name`
                                    FROM `tabPayment Entry`
                                    WHERE `camt_import` = '{camt_import}'
                                    AND `docstatus` = 1""".format(camt_import=camt_import), as_dict=True)
    # reset old values
    frappe.db.set_value('CAMT Import', camt_import, 'mitgliedschaften_qty', 0)
    frappe.db.set_value('CAMT Import', camt_import, 'hv_qty', 0)
    frappe.db.set_value('CAMT Import', camt_import, 'spenden_qty', 0)
    frappe.db.set_value('CAMT Import', camt_import, 'produkte_qty', 0)
    
    # set new values
    for pe in gebuchte_pes:
        pe_doc = frappe.get_doc("Payment Entry", pe.name)
        if len(pe_doc.references) > 0:
            for reference in pe_doc.references:
                if int(frappe.db.get_value('Sales Invoice', reference.reference_name, 'ist_mitgliedschaftsrechnung')) == 1:
                    camt_mitgliedschaften_update(camt_import)
                elif int(frappe.db.get_value('Sales Invoice', reference.reference_name, 'ist_hv_rechnung')) == 1:
                    camt_hv_update(camt_import)
                elif int(frappe.db.get_value('Sales Invoice', reference.reference_name, 'ist_spenden_rechnung')) == 1:
                    camt_spenden_update(camt_import)
                elif int(frappe.db.get_value('Sales Invoice', reference.reference_name, 'ist_sonstige_rechnung')) == 1:
                    camt_produkte_update(camt_import)
    
    # update report data
    verbuchte_zahlungen_gegen_rechnung = frappe.db.sql("""SELECT
                                                            SUM(`amount`) AS `amount`,
                                                            `item_code`
                                                        FROM `tabSales Invoice Item` WHERE `parent` IN (
                                                            SELECT DISTINCT
                                                                `reference_name`
                                                            FROM `tabPayment Entry Reference`
                                                            WHERE `parent` IN (
                                                                SELECT
                                                                    `name`
                                                                FROM `tabPayment Entry`
                                                                WHERE `camt_import` = '{camt_import}'
                                                                AND `docstatus` = 1
                                                            )
                                                        )
                                                        GROUP BY `item_code`""".format(camt_import=camt_import), as_dict=True)
    
    verbuchte_guthaben = frappe.db.sql("""SELECT
                                                SUM(`unallocated_amount`) AS `amount`,
                                                `mv_mitgliedschaft` AS `mitgliedschaft`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `mv_mitgliedschaft` IS NOT NULL
                                            AND `docstatus` = 1
                                            AND `unallocated_amount` > 0
                                            GROUP BY `mv_mitgliedschaft`""".format(camt_import=camt_import), as_dict=True)
    
    falsch_verbuchte_guthaben = frappe.db.sql("""SELECT
                                                        `unallocated_amount` AS `amount`,
                                                        `name`
                                                    FROM `tabPayment Entry`
                                                    WHERE `camt_import` = '{camt_import}'
                                                    AND `mv_mitgliedschaft` IS NULL
                                                    AND `docstatus` = 1""".format(camt_import=camt_import), as_dict=True)
    
    nicht_gebuchte_pes = frappe.db.sql("""SELECT `name`
                                    FROM `tabPayment Entry`
                                    WHERE `camt_import` = '{camt_import}'
                                    AND `docstatus` != 1""".format(camt_import=camt_import), as_dict=True)
    
    report_data = ''
    # nicht eingelesene Zahlungen
    if int(frappe.db.get_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen_qty')) > 0:
        report_data += """<p style="color: red;"><br>Achtung; {0} Zahlung(en) konnte(n) <u>nicht</u> eingelesen werden!</p>""".format(frappe.db.get_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen_qty'))
    # Artikel Aufschlüsselung
    if len(verbuchte_zahlungen_gegen_rechnung) > 0:
        totalbetrag = 0
        report_data += """<h3>Artikel Aufschlüsselung</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Artikel</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                </tr>"""
        for entry in verbuchte_zahlungen_gegen_rechnung:
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0} ({1})</td>
                                <td style="text-align: right;">{2}</td>
                            </tr>""".format(frappe.get_value("Item", entry.item_code, "item_name"), frappe.get_value("Item", entry.item_code, "sektion_id"), "{:,.2f}".format(entry.amount).replace(",", "'"))
            totalbetrag += entry.amount
        report_data += """
                        <tr>
                            <td style="text-align: left;"><b>Total</b></td>
                            <td style="text-align: right;"><b>{0}</b></td>
                        </tr>""".format("{:,.2f}".format(totalbetrag).replace(",", "'"))
        
        report_data += """</tbody></table>"""
    
    # Verbuchte Guthaben
    if len(verbuchte_guthaben) > 0:
        report_data += """<h3>Verbuchte Guthaben</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Mitglied</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                </tr>"""
        for entry in verbuchte_guthaben:
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0}</td>
                                <td style="text-align: right;">{1}</td>
                            </tr>""".format("""<a href="/desk#Form/Mitgliedschaft/{0}">""".format(entry.mitgliedschaft) + str(frappe.get_value("Mitgliedschaft", entry.mitgliedschaft, "mitglied_nr")) + """</a>""", \
                            "{:,.2f}".format(entry.amount).replace(",", "'"))
        report_data += """</tbody></table>"""
    
    # Falsch verbuchte Guthaben
    if len(falsch_verbuchte_guthaben) > 0:
        report_data += """<h3>Falsch verbuchte Guthaben</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Zahlung</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                </tr>"""
        for entry in falsch_verbuchte_guthaben:
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0}</td>
                                <td style="text-align: right;">{1}</td>
                            </tr>""".format("""<a href="/desk#Form/Payment Entry/{pe}">{pe}</a>""".format(pe=entry.name), "{:,.2f}".format(entry.amount).replace(",", "'"))
        report_data += """</tbody></table>"""
    
    # Zahlungsliste (Verbucht)
    if len(gebuchte_pes) > 0:
        report_data += """<h3>Zahlungsliste (Verbucht)</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Mitgliedschaft</b></td>
                                    <td style="text-align: left;"><b>Details</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                </tr>"""
        for pe in gebuchte_pes:
            pe_doc = frappe.get_doc("Payment Entry", pe.name)
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0}</td>
                                <td style="text-align: left;">{1}</td>
                                <td style="text-align: right;">{2}</td>
                            </tr>""".format("""<a href="/desk#Form/Mitgliedschaft/{0}">""".format(pe_doc.mv_mitgliedschaft) + str(frappe.get_value("Mitgliedschaft", pe_doc.mv_mitgliedschaft, "mitglied_nr")) + """</a>""", \
                            pe_doc.remarks, \
                            "{:,.2f}".format(pe_doc.paid_amount).replace(",", "'"))
        report_data += """</tbody></table>"""
    
    # Zahlungsliste (Unverbucht)
    if len(nicht_gebuchte_pes) > 0:
        report_data += """<h3>Zahlungsliste (Unverbucht)</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Mitgliedschaft</b></td>
                                    <td style="text-align: left;"><b>Details</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                    <td style="text-align: right;"><b>Status</b></td>
                                </tr>"""
        for pe in nicht_gebuchte_pes:
            pe_doc = frappe.get_doc("Payment Entry", pe.name)
            if pe_doc.mv_mitgliedschaft:
                mitgliedschafts_link_string = """<a href="/desk#Form/Mitgliedschaft/{0}">""".format(pe_doc.mv_mitgliedschaft) + str(frappe.get_value("Mitgliedschaft", pe_doc.mv_mitgliedschaft, "mitglied_nr")) + """</a>"""
            else:
                mitgliedschafts_link_string = '---'
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0}</td>
                                <td style="text-align: left;">{1}</td>
                                <td style="text-align: right;">{2}</td>
                                <td style="text-align: right;">{3}</td>
                            </tr>""".format(mitgliedschafts_link_string, \
                            pe_doc.remarks, \
                            "{:,.2f}".format(pe_doc.paid_amount).replace(",", "'"), \
                            'Entwurf' if pe_doc.docstatus == 0 else 'Storniert')
        report_data += """</tbody></table>"""
    
    
    frappe.db.set_value('CAMT Import', camt_import, 'report', report_data)
    
    # setzen Status = Closed wenn verbucht = eingelesen
    if frappe.db.get_value('CAMT Import', camt_import, 'status') != 'Failed':
        if (frappe.db.get_value('CAMT Import', camt_import, 'verbuchte_zahlung_qty') - frappe.db.get_value('CAMT Import', camt_import, 'ueberzahlung_qty')) == frappe.db.get_value('CAMT Import', camt_import, 'eingelesene_zahlungen_qty'):
            frappe.db.set_value('CAMT Import', camt_import, 'status', 'Closed')
        else:
            frappe.db.set_value('CAMT Import', camt_import, 'status', 'Verarbeitet')

@frappe.whitelist()
def mit_spende_ausgleichen(pe):
    payment_entry = frappe.get_doc("Payment Entry", pe)
    mitgliedschaft = payment_entry.mv_mitgliedschaft
    
    # erstelle fr
    from mvd.mvd.doctype.fakultative_rechnung.fakultative_rechnung import create_hv_fr
    fr = create_hv_fr(mitgliedschaft, betrag_spende=payment_entry.unallocated_amount)
    
    # erstelle sinv aus fr
    sinv = create_unpaid_sinv(fr, betrag=payment_entry.unallocated_amount)['sinv']
    
    # match sinv mit pe
    row = payment_entry.append('references', {})
    row.reference_doctype = "Sales Invoice"
    row.reference_name = sinv
    row.due_date = add_days(today(), 30)
    row.total_amount = frappe.get_value("Sales Invoice", sinv, "base_grand_total")
    row.outstanding_amount = frappe.get_value("Sales Invoice", sinv, "outstanding_amount")
    row.allocated_amount = frappe.get_value("Sales Invoice", sinv, "outstanding_amount")
    
    # update unallocated amount
    payment_entry.unallocated_amount -= frappe.get_value("Sales Invoice", sinv, "outstanding_amount")
    payment_entry.camt_status = 'Verbucht'
    payment_entry.save()
    payment_entry.submit()
    
    camt_gebuchte_zahlung_update(payment_entry.camt_import)
    camt_spenden_update(payment_entry.camt_import)
    
    return

@frappe.whitelist()
def rueckzahlung(pe):
    payment_entry = frappe.get_doc("Payment Entry", pe)
    row = payment_entry.append('deductions', {})
    row.amount = payment_entry.unallocated_amount * -1
    row.account = frappe.get_value("Sektion", payment_entry.sektion_id, "zwischen_konto")
    row.cost_center = frappe.get_value("Company", payment_entry.company, "cost_center")
    payment_entry.unallocated_amount = 0
    payment_entry.camt_status = 'Verbucht'
    camt_gebuchte_zahlung_update(payment_entry.camt_import)
    payment_entry.save()
    payment_entry.submit()
    return

@frappe.whitelist()
def als_hv_verbuchen(pe):
    payment_entry = frappe.get_doc("Payment Entry", pe)
    mitgliedschaft = payment_entry.mv_mitgliedschaft
    
    # erstelle fr
    from mvd.mvd.doctype.fakultative_rechnung.fakultative_rechnung import create_hv_fr
    fr = create_hv_fr(mitgliedschaft)
    
    # erstelle sinv aus fr
    sinv = create_unpaid_sinv(fr, 10)['sinv']
    
    # match sinv mit pe
    row = payment_entry.append('references', {})
    row.reference_doctype = "Sales Invoice"
    row.reference_name = sinv
    row.due_date = add_days(today(), 30)
    row.total_amount = frappe.get_value("Sales Invoice", sinv, "base_grand_total")
    row.outstanding_amount = frappe.get_value("Sales Invoice", sinv, "outstanding_amount")
    row.allocated_amount = frappe.get_value("Sales Invoice", sinv, "outstanding_amount")
    
    # update unallocated amount
    payment_entry.unallocated_amount -= frappe.get_value("Sales Invoice", sinv, "outstanding_amount")
    if payment_entry.unallocated_amount == 0:
        payment_entry.camt_status = 'Verbucht'
        camt_gebuchte_zahlung_update(payment_entry.camt_import)
    camt_hv_update(payment_entry.camt_import)
    payment_entry.save()
    if payment_entry.unallocated_amount == 0:
        payment_entry.submit()
    return

@frappe.whitelist()
def fr_bez_ezs(fr, datum, betrag):
    betrag = float(betrag)
    hv_sinv = create_unpaid_sinv(fr, betrag=betrag)['sinv']
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
        'mitgliedschafts_jahr': fr.bezugsjahr if fr.bezugsjahr and fr.bezugsjahr > 0 else int(getdate(today()).strftime("%Y")),
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
def sinv_bez_mit_ezs_oder_bar(sinv, ezs=False, bar=False, hv=False, datum=False, betrag=False):
    sinv = frappe.get_doc("Sales Invoice", sinv)
    betrag = float(betrag)
    if betrag > sinv.outstanding_amount:
        frappe.throw("Der Bezahlte Betrag darf die ausstehende Summe nicht überschreiten")
    if hv:
        hv_sinv = create_unpaid_sinv(hv, betrag=10)['sinv']
    
    customer = sinv.customer
    mitgliedschaft = sinv.mv_mitgliedschaft
    mv_kunde = sinv.mv_kunde
    payment_entry_record = frappe.get_doc({
        'doctype': "Payment Entry",
        'posting_date': datum or today(),
        'party_type': 'Customer',
        'party': customer,
        'mv_mitgliedschaft': mitgliedschaft,
        'mv_kunde': mv_kunde,
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
def mit_folgejahr_ausgleichen(pe):
    payment_entry = frappe.get_doc("Payment Entry", pe)
    try:
        sinv_to_copy_name = frappe.db.sql("""SELECT `name`
                                        FROM `tabSales Invoice`
                                        WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'
                                        AND `ist_mitgliedschaftsrechnung` = 1
                                        AND `docstatus` = 1
                                        ORDER BY `mitgliedschafts_jahr` DESC""".format(mitgliedschaft=payment_entry.mv_mitgliedschaft), as_dict=True)[0].name
        sinv_to_copy = frappe.get_doc("Sales Invoice", sinv_to_copy_name)
        sinv = frappe.copy_doc(sinv_to_copy)
        sinv.mitgliedschafts_jahr = sinv_to_copy.mitgliedschafts_jahr + 1
        sinv.due_date = add_days(today(), 30)
        sinv.set_posting_time = 1
        sinv.posting_date = today()
        sinv.payment_schedule = []
        sinv.insert()
        
        sinv.submit()
        
        # match sinv mit pe
        allocated_amount = payment_entry.unallocated_amount if payment_entry.unallocated_amount <= sinv.outstanding_amount else sinv.outstanding_amount
        row = payment_entry.append('references', {})
        row.reference_doctype = "Sales Invoice"
        row.reference_name = sinv.name
        row.due_date = add_days(today(), 30)
        row.total_amount = sinv.base_grand_total
        row.outstanding_amount = sinv.outstanding_amount
        row.allocated_amount = allocated_amount
        
        # update unallocated amount
        payment_entry.unallocated_amount -= allocated_amount
        if payment_entry.unallocated_amount == 0:
            payment_entry.camt_status = 'Verbucht'
            camt_gebuchte_zahlung_update(payment_entry.camt_import)
        
        payment_entry.save()
        
        if payment_entry.unallocated_amount == 0:
            payment_entry.submit()
    except:
        frappe.throw("Dieses Mitglied besitzt noch keine Rechnung.<br>Bitte erstellen Sie manuell eine Initial-Rechnung")
    
    return

@frappe.whitelist()
def reopen_payment_as_admin(pe):
    frappe.db.sql("""UPDATE `tabPayment Entry` SET `docstatus` = 0 WHERE `name` = '{pe}'""".format(pe=pe), as_list=True)
    return

@frappe.whitelist()
def reopen_sinv_as_admin(sinv):
    frappe.db.sql("""UPDATE `tabSales Invoice` SET `docstatus` = 0 WHERE `name` = '{sinv}'""".format(sinv=sinv), as_list=True)
    return
