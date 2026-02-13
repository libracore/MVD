# -*- coding: utf-8 -*-
# Copyright (c) 2022-2024, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from bs4 import BeautifulSoup
import six
from frappe.utils.data import add_days, today, getdate
from mvd.mvd.doctype.camt_import.helpers import *

QRR_SINVS = {}
def preload_qrr_sinvs():
    sinvs = frappe.db.sql("""SELECT
                                `name` AS `sinv`,
                                `customer`,
                                `mv_mitgliedschaft`,
                                `mv_kunde`,
                                `outstanding_amount`,
                                `sektion_id` AS `sektion`,
                                `company`,
                                REPLACE(`esr_reference`, ' ', '') AS `esr_reference`
                            FROM `tabSales Invoice`
                            WHERE `docstatus` = 1
                            AND `outstanding_amount` > 0""", as_dict=True)
    for sinv in sinvs:
        QRR_SINVS[sinv.esr_reference] = sinv

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
            spenden_artikel_details = frappe.get_doc("Item", sektion.spenden_artikel)
            item = [{
                "item_code": sektion.spenden_artikel,
                "qty": 1, "rate": betrag,
                "conversion_factor": 1,
                "description": spenden_artikel_details.description,
                "uom": spenden_artikel_details.stock_uom,
                "income_account": spenden_artikel_details.item_defaults[0].income_account,
                "cost_center": spenden_artikel_details.item_defaults[0].selling_cost_center
            }]
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
            "esr_reference": fak_doc.qrr_referenz
        })
        sinv.insert(ignore_permissions=True)
        
        # submit workaround weil submit ignore_permissions=True nicht kennt
        sinv.docstatus = 1
        sinv.save(ignore_permissions=True)
        
        fak_doc.status = 'Paid'
        fak_doc.bezahlt_via = sinv.name
        fak_doc.save(ignore_permissions=True)

        frappe.db.commit()
        
        return {
                'sinv': sinv.name,
                'customer': sinv.customer,
                'mv_mitgliedschaft': sinv.mv_mitgliedschaft,
                'mv_kunde': sinv.mv_kunde,
                'outstanding_amount': sinv.outstanding_amount,
                'sektion': sinv.sektion_id,
                'company': sinv.company
            }
    else:
        # Fakultative Rechnung wurde bereits beglichen -> erzeuge ungebuchte, aber zugewiesene Zahlung
        return False

def zahlungen_einlesen(camt_file, camt_import, nachladen=False):
    """
    Diese Funktion list das CAMT-File aus und erzeugt für alle darin enthaltenen Eingangszahlungen einen Payment Entry
    """
    camt_import = frappe.get_doc("CAMT Import", camt_import)
    account = camt_import.account
    sektion = camt_import.sektion_id
    company = camt_import.company
    
    commit_counter = 1
    
    transaction_entries = camt_file.find_all('ntry')
    
    # Set/Reset CAMT Base Data
    frappe.db.set_value('CAMT Import', camt_import.name, 'camt_file_datum', frappe.utils.get_datetime(camt_file.document.bktocstmrdbtcdtntfctn.grphdr.credttm.get_text().split("T")[0]).strftime('%Y-%m-%d'))
    frappe.db.set_value('CAMT Import', camt_import.name, 'camt_taxen', 0)
    frappe.db.set_value('CAMT Import', camt_import.name, 'camt_amount', 0)

    for entry in transaction_entries:
        entry_soup = BeautifulSoup(six.text_type(entry), 'lxml')
        date = entry_soup.bookgdt.dt.get_text().split("+")[0]
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
                    if not nachladen:
                        erfasse_ausgelesene_zahlungen(transaction_reference, unique_reference, date, amount, camt_import.name)
                    
                    # erfasse Payment Entry
                    erstelle_zahlung(date=date, to_account=account, received_amount=amount, 
                        transaction_id=unique_reference, remarks="QRR: {0}, {1}, {2}, IBAN: {3}".format(
                        transaction_reference, customer_name, customer_address, customer_iban), company=company, sektion=sektion, qrr=transaction_reference, camt_import=camt_import.name, nachladen=nachladen)
                    
                    if commit_counter == 100:
                        frappe.db.commit()
                        commit_counter = 1
                    else:
                        commit_counter += 1
                    
            except Exception as e:
                # Zahlung konnte nicht ausgelesen werden, entsprechender Errorlog im CAMT-File wird erzeugt
                erfasse_fehlgeschlagenes_auslesen(six.text_type(transaction), e, camt_import.name)
                pass
    
    camt_status_update(camt_import.name, 'Zahlungen eingelesen - verbuche Matches')
    frappe.db.commit()
    return

def zahlungen_matchen(camt_import):
    preload_qrr_sinvs()
    payment_entries = frappe.db.sql("""
                                    SELECT `name`,
                                    `remarks`,
                                    `received_amount`
                                    FROM `tabPayment Entry`
                                    WHERE `camt_import` = '{camt_import}'
                                    AND `docstatus` = 0
                                    AND (`mv_mitgliedschaft` IS NULL OR `mv_mitgliedschaft` = '')
                                    AND (`mv_kunde` IS NULL OR `mv_kunde` = '')""".format(camt_import=camt_import), as_dict=True)
    commit_counter = 1
    double_payment_control = {}
    for payment_entry in payment_entries:
        transaction_reference = payment_entry.remarks.split(", ")[0].replace("QRR: ", "")
        received_amount = payment_entry.received_amount
        if len(transaction_reference) > 26:
            sinv_lookup_data = sinv_lookup(transaction_reference, received_amount, QRR_SINVS)
            if sinv_lookup_data:
                pe = frappe.get_doc("Payment Entry", payment_entry.name)
                pe.party = sinv_lookup_data.get('customer')
                pe.mv_mitgliedschaft = sinv_lookup_data.get('mv_mitgliedschaft')
                pe.mv_kunde = sinv_lookup_data.get('mv_kunde')
                    
                row = pe.append('references', {})
                row.reference_doctype = 'Sales Invoice'
                row.reference_name = sinv_lookup_data.get('sinv')
                
                if sinv_lookup_data.get('sinv') not in double_payment_control:
                    double_payment_control[sinv_lookup_data.get('sinv')] = received_amount
                    double_payment = False
                else:
                    if (double_payment_control[sinv_lookup_data.get('sinv')] + received_amount) <= sinv_lookup_data.get('outstanding_amount'):
                        double_payment_control[sinv_lookup_data.get('sinv')] = double_payment_control[sinv_lookup_data.get('sinv')] + received_amount
                        double_payment = False
                    else:
                        double_payment = True

                if (received_amount <= sinv_lookup_data.get('outstanding_amount')) and not double_payment:
                    pe.camt_status = 'Rechnungs Match'
                    row.allocated_amount = pe.paid_amount
                else:
                    if not double_payment:
                        pe.camt_status = 'Überbezahlt'
                        row.allocated_amount = sinv_lookup_data.get('outstanding_amount')
                    else:
                        pe.camt_status = 'Überbezahlt'
                        bereits_erfasste_zahlungen = double_payment_control[sinv_lookup_data.get('sinv')]
                        sinv_outstanding = sinv_lookup_data.get('outstanding_amount')
                        diff = sinv_outstanding - bereits_erfasste_zahlungen
                        row.allocated_amount = diff if diff > 0 else 0
                    camt_ueberzahlung_update(camt_import)
                
                # see #1101
                if pe.sektion_id != sinv_lookup_data.get('sektion'):
                    pe.sektion_id = sinv_lookup_data.get('sektion')
                    pe.company = sinv_lookup_data.get('company')
                    pe.paid_to = frappe.db.get_value('Sektion', pe.sektion_id, 'account')
                    pe.paid_from = frappe.db.get_value('Company', pe.company, 'default_receivable_account')
                
                pe.save(ignore_permissions=True)
                erfasse_rg_match(camt_import)
            else:
                # Könnte Doppelzahlung sein - versuche Zahlung zuzuweisen
                mitgliedschaft = suche_mitgliedschaft_aus_pe(payment_entry.name, mitglied_only=True)
                if mitgliedschaft:
                    mitgliedschaft_data = mitgliedschaft_zuweisen(mitgliedschaft=mitgliedschaft)
                    pe = frappe.get_doc("Payment Entry", payment_entry.name)
                    pe.mv_mitgliedschaft= mitgliedschaft_data.get("mitgliedschaft")
                    pe.party = mitgliedschaft_data.get("customer")
                    pe.camt_status = 'Zugewiesen'
                    pe.save(ignore_permissions=True)
                
        if commit_counter == 100:
            frappe.db.commit()
            commit_counter = 1
        else:
            commit_counter += 1
    frappe.db.commit()
    return

def verbuche_matches(camt_import):
    """
    Diese Funktion verbucht alle Payment Entries mit dem Status 'Rechnungs Match' welche einer Sales Invoice zugeordnet werden konnten
    """
    pes = frappe.db.sql("""SELECT
                                `name`
                            FROM `tabPayment Entry`
                            WHERE `docstatus` = 0
                            AND `camt_import` = '{camt_import}'
                            AND `camt_status` = 'Rechnungs Match'""".format(camt_import=camt_import), as_dict=True)
    
    for pe in pes:
        pe_doc = frappe.get_doc("Payment Entry", pe.name)
        if len(pe_doc.references) > 0:
            sinv_doc = frappe.get_doc("Sales Invoice", pe_doc.references[0].reference_name)
            if sinv_doc.ist_mitgliedschaftsrechnung:
                camt_mitgliedschaften_update(camt_import)
            elif sinv_doc.ist_hv_rechnung:
                camt_hv_update(camt_import)
            elif sinv_doc.ist_spenden_rechnung:
                camt_spenden_update(camt_import)
            elif sinv_doc.ist_sonstige_rechnung:
                camt_produkte_update(camt_import)
            pe_doc.camt_status = 'Verbucht'
            pe_doc.save(ignore_permissions=True)
            pe_doc.submit()
            frappe.db.commit()
            camt_gebuchte_zahlung_update(camt_import)
    
    camt_status_update(camt_import, 'Verarbeitet')
    frappe.db.commit()
    return

@frappe.whitelist()
def suche_mitgliedschaft_aus_pe(payment_entry, mitglied_only=False):
    data = []
    pe = frappe.get_doc("Payment Entry", payment_entry)
    pe_sektion = pe.sektion_id
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
                if mitglied_only:
                    return other_pes[0].mitgliedschaft
                
                for entry in other_pes:
                    unabhaengiger_debitor = frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'unabhaengiger_debitor')
                    if pe_sektion == frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'sektion_id'):
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
        if mitglied_only:
            return alte_rechnungen[0].mitgliedschaft
        
        for entry in alte_rechnungen:
            unabhaengiger_debitor = frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'unabhaengiger_debitor')
            if pe_sektion == frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'sektion_id'):
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
        if mitglied_only:
            return alte_rechnungen[0].mitgliedschaft
        
        for entry in alte_rechnungen:
            unabhaengiger_debitor = frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'unabhaengiger_debitor')
            if pe_sektion == frappe.db.get_value('Mitgliedschaft', entry.mitgliedschaft, 'sektion_id'):
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
    if mitglied_only:
        return False
    
    return data

@frappe.whitelist()
def mitgliedschaft_zuweisen(mitgliedschaft, faktura=False, pe_sektion=None):
    if not faktura:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
        if pe_sektion and pe_sektion != mitgliedschaft.sektion_id:
            frappe.throw("Die Sektion der Mitgliedschaft stimmt nicht mit der Sektion der Zahlung überein!")
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
    else:
        faktura = frappe.get_doc("Kunden", mitgliedschaft)
        if pe_sektion and pe_sektion != faktura.sektion_id:
            frappe.throw("Die Sektion des Faktura-Kunden stimmt nicht mit der Sektion der Zahlung überein!")
        if faktura.mv_mitgliedschaft:
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", faktura.mv_mitgliedschaft)
            if mitgliedschaft.rg_kunde:
                return {
                    'mitgliedschaft': mitgliedschaft.name,
                    'customer': mitgliedschaft.rg_kunde,
                    'faktura': faktura.name
                }
            else:
                return {
                    'mitgliedschaft': mitgliedschaft.name,
                    'customer': mitgliedschaft.kunde_mitglied,
                    'faktura': faktura.name
                }
        else:
            if faktura.rg_kunde:
                return {
                    'mitgliedschaft': '',
                    'customer': faktura.rg_kunde,
                    'faktura': faktura.name
                }
            else:
                return {
                    'mitgliedschaft': '',
                    'customer': faktura.kunde_kunde,
                    'faktura': faktura.name
                }

@frappe.whitelist()
def mit_spende_ausgleichen(pe, spendenlauf_referenz=None):
    payment_entry = frappe.get_doc("Payment Entry", pe)
    mitgliedschaft = payment_entry.mv_mitgliedschaft
    
    # erstelle fr
    from mvd.mvd.doctype.fakultative_rechnung.fakultative_rechnung import create_hv_fr
    fr = create_hv_fr(mitgliedschaft, betrag_spende=payment_entry.unallocated_amount, spendenlauf_referenz=spendenlauf_referenz)
    
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
        "esr_reference": fr.qrr_referenz
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
        sinv.naming_series = 'R-.{sektions_code}.#####'
        sinv.rechnungs_jahresversand = None
        sinv.renaming_series = None
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
def reset_camt(camt):
    payments = frappe.db.sql("""SELECT `name` FROM `tabPayment Entry` WHERE `camt_import` = '{camt}'""".format(camt=camt), as_dict=True)
    for payment in payments:
        pe = frappe.get_doc("Payment Entry", payment.name)
        if pe.docstatus == 0:
            pe.delete()
        elif pe.docstatus == 1:
            pe.cancel()
            pe.delete()
        elif pe.docstatus == 2:
            pe.delete()
    
    camt_import = frappe.get_doc("CAMT Import", camt)
    camt_import.ausgelesene_zahlungen_qty = 0
    camt_import.eingelesene_zahlungen_qty = 0
    camt_import.rg_match_qty = 0
    camt_import.verbuchte_zahlung_qty = 0
    camt_import.stornierte_zahlungen_qty = 0
    camt_import.fehlgeschlagenes_auslesen_qty = 0
    camt_import.nicht_eingelesene_zahlungen_qty = 0
    camt_import.anz_unmatched_payments = 0
    camt_import.zugewiesen_unverbucht_qty = 0
    camt_import.hv_qty = 0
    camt_import.produkte_qty = 0
    camt_import.ueberzahlung_qty = 0
    camt_import.mitgliedschaften_qty = 0
    camt_import.spenden_qty = 0
    camt_import.guthaben_qty = 0
    camt_import.ausgelesene_zahlungen = ''
    camt_import.eingelesene_zahlungen = ''
    camt_import.camt_taxen = 0
    camt_import.camt_amount = 0
    camt_import.save()
    frappe.db.commit()
    aktualisiere_camt_uebersicht(camt_import.name)

def erstelle_zahlung(date, to_account, received_amount, transaction_id, remarks, company, sektion, qrr, camt_import, nachladen=False):
    """
    Diese Funktion erzeugt einen Payment Entry, insofern noch kein Payment Entry mit der selben Transaktions-ID der Bank vorhanden ist
    """
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
        erfasse_eingelesene_zahlungen(qrr, transaction_id, date, received_amount, camt_import)
        if nachladen:
            entferne_nicht_eingelesene_zahlungen(camt_import)
        return
    else:
        # erfasse nicht eingelesene Zahlung in CAMT-Import
        if not nachladen:
            erfasse_nicht_eingelesene_zahlungen(qrr, transaction_id, date, received_amount, camt_import)
        return