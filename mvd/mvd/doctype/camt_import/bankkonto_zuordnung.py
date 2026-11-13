# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import hashlib
import json
import frappe
from frappe.utils import flt
from mvd.mvd.doctype.camt_import.helpers import get_matching_bankkonto, get_matching_abweichung
from mvd.mvd.doctype.camt_import.reset_protokoll import mit_protokoll, markiere_beleg
from mvd.mvd.doctype.camt_import.verrechnung import _zugriff, _eintraege, _eintrag, _offene_eintraege, _konto, _aktualisiere_report
from mvd.mvd.doctype.camt_import.utils import create_unpaid_sinv, weise_rechnung_zu

"""
    Manuelle Kontowahl bei reinen Bankkonto-Abweichungen innerhalb einer Sektion
"""

def _kontext(camt, payment_entry, sperren=False):
    entries = _eintrag(camt, payment_entry)
    if len(entries) != 1:
        frappe.throw('Diese Zahlung ist nicht eindeutig als blockierter Rechnungstreffer erfasst.')
    
    entry = entries[0]
    doctype = entry['reference_doctype']
    if doctype not in ['Sales Invoice', 'Fakultative Rechnung']:
        frappe.throw('Die hinterlegte Rechnungsart wird nicht unterstützt.')
    
    if sperren:
        frappe.db.sql('SELECT name FROM `tabPayment Entry` WHERE name=%s FOR UPDATE', (payment_entry,))
        frappe.db.sql('SELECT name FROM `tab{0}` WHERE name=%s FOR UPDATE'.format(doctype), (entry['reference_name'],))
    
    pe = frappe.get_doc('Payment Entry', payment_entry)
    pe.check_permission('write')
    target = frappe.get_doc(doctype, entry['reference_name'])
    target.check_permission('read')

    if pe.camt_import != camt.name or pe.docstatus != 0 or pe.payment_type != 'Receive':
        frappe.throw('Es kann nur eine ungebuchte Eingangszahlung dieses CAMT-Imports zugeordnet werden.')
    
    if pe.references or pe.deductions or pe.get('camt_verrechnung_journal'):
        frappe.throw('Die Zahlung wurde bereits bearbeitet. Bitte prüfen Sie ihre Referenzen und Abzüge.')
    
    if pe.company != camt.company or pe.sektion_id != camt.sektion_id or pe.paid_to != camt.account:
        frappe.throw('Firma, Sektion und Eingangskonto der Zahlung müssen weiterhin dem CAMT-Import entsprechen.')
    
    if target.docstatus != 1 or (doctype == 'Sales Invoice' and flt(target.outstanding_amount) <= 0) or (doctype == 'Fakultative Rechnung' and target.status != 'Unpaid'):
        frappe.throw('Die Zielrechnung muss gebucht und noch offen sein.')
    
    difference = get_matching_abweichung(target, camt)
    if not difference or any(row['feld'] != 'Bankkonto' for row in difference['matching_abweichungen']):
        frappe.throw('Die Kontowahl ist nur möglich, wenn ausschliesslich das Bankkonto abweicht. Firma und Sektion müssen übereinstimmen.')
    
    reference = target.esr_reference if doctype == 'Sales Invoice' else target.qrr_referenz
    payment_reference = (pe.remarks or '').split(', ')[0].replace('QRR: ', '')
    if not reference or reference.replace(' ', '') != payment_reference.replace(' ', ''):
        frappe.throw('Die Zahlungsreferenz stimmt nicht mehr mit der Rechnung überein. Bitte matchen Sie die Zahlungen erneut.')
    
    if flt(pe.received_amount) <= 0 or flt(pe.received_amount) != flt(pe.camt_amount):
        frappe.throw('Es muss der unveränderte positive CAMT-Zahlungsbetrag zugeordnet werden.')
    
    company = frappe.get_cached_doc('Company', camt.company)
    currency = pe.paid_to_account_currency or company.default_currency
    _konto(camt.account, camt.company, currency, account_type='Bank')
    invoice_bank = get_matching_bankkonto(target)
    invoice_bank_available = False

    if invoice_bank:
        try:
            _konto(invoice_bank, camt.company, currency, account_type='Bank')
            invoice_bank_available = True
        except (frappe.ValidationError, frappe.PermissionError):
            frappe.clear_messages()
    
    info = {
        'payment_entry': pe.name, 'reference_doctype': doctype, 'reference_name': target.name,
        'company': camt.company, 'sektion': camt.sektion_id,
        'import_bankkonto': camt.account, 'rechnungs_bankkonto': invoice_bank,
        'rechnungskonto_verfuegbar': invoice_bank_available,
        'amount': flt(pe.received_amount), 'currency': currency,
        'payment_modified': str(pe.modified), 'invoice_modified': str(target.modified),
        'outstanding_amount': flt(target.outstanding_amount) if doctype == 'Sales Invoice' else flt(target.betrag)
    }
    info['token'] = hashlib.sha256(json.dumps(info, sort_keys=True, ensure_ascii=True).encode('utf-8')).hexdigest()

    return pe, target, info

def _kandidaten(camt, nur_erster=False):
    result = []
    for entry in _offene_eintraege(camt, firmenwechsel=False):
        try:
            result.append(_kontext(camt, entry['payment_entry'])[2])
            if nur_erster:
                break
        except (frappe.ValidationError, frappe.PermissionError):
            frappe.clear_messages()
    
    return result

@frappe.whitelist()
def kandidaten(camt_import):
    return _kandidaten(_zugriff(camt_import))

@frappe.whitelist()
def verfuegbar(camt_import):
    try:
        return bool(_kandidaten(_zugriff(camt_import), nur_erster=True))
    except (frappe.ValidationError, frappe.PermissionError):
        frappe.clear_messages()
        return False

@frappe.whitelist()
@mit_protokoll
def zuordnen(camt_import, payment_entry, bankkonto_quelle, token):
    camt = _zugriff(camt_import, schreiben=True)
    pe, target, info = _kontext(camt, payment_entry, sperren=True)

    if token != info['token']:
        frappe.throw('Die Daten haben sich seit der Auswahl geändert. Bitte öffnen Sie die Kontowahl erneut.')
    
    if bankkonto_quelle not in ['CAMT-Import', 'Rechnung']:
        frappe.throw('Bitte wählen Sie das Bankkonto aus dem CAMT-Import oder aus der Rechnung.')
    
    if bankkonto_quelle == 'Rechnung' and not info['rechnungskonto_verfuegbar']:
        frappe.throw('Das Rechnungskonto fehlt oder ist kein zugängliches aktives Bankkonto derselben Firma und Währung.')
    
    account = info['import_bankkonto'] if bankkonto_quelle == 'CAMT-Import' else info['rechnungs_bankkonto']
    markiere_beleg('Payment Entry', pe.name)

    if target.doctype == 'Fakultative Rechnung':
        target.check_permission('write')
        invoice = frappe.get_doc({'doctype': 'Sales Invoice', 'company': target.company, 'sektion_id': target.sektion_id})
        invoice.check_permission('create')
        invoice.check_permission('submit')

        # Nur den Bankvergleich freigeben. Firma und Sektion werden weiterhin geprüft
        # die erzeugte Rechnung behält das Konto der ursprünglichen FAK
        data = create_unpaid_sinv(target.name, pe.received_amount, camt_import=camt, commit=False, bankkonto_abweichung_erlaubt=True)
        if not data or data.get('matching_abweichungen'):
            frappe.throw('Die fakultative Rechnung konnte nicht eindeutig umgewandelt werden.')
        
        target = frappe.get_doc('Sales Invoice', data['sinv'])
        if target.company != camt.company or target.sektion_id != camt.sektion_id:
            frappe.throw('Die erzeugte Rechnung gehört nicht zur Firma und Sektion des CAMT-Imports.')
    else:
        data = {
            'sinv': target.name,
            'customer': target.customer,
            'mv_mitgliedschaft': target.mv_mitgliedschaft,
            'mv_kunde': target.mv_kunde,
            'outstanding_amount': target.outstanding_amount
        }
    
    # Bereits zugeordnete Entwürfe berücksichtigen, wie beim automatischen Matching...
    reserved = frappe.db.sql("""
        SELECT COALESCE(SUM(ref.allocated_amount), 0)
        FROM `tabPayment Entry Reference` ref
        INNER JOIN `tabPayment Entry` pe ON pe.name = ref.parent
        WHERE ref.parenttype = 'Payment Entry'
        AND ref.reference_doctype = 'Sales Invoice'
        AND ref.reference_name = %s
        AND pe.docstatus = 0
        AND pe.name != %s
    """, (target.name, pe.name))[0][0]

    pe.paid_to = account
    pe.paid_to_account_currency = None
    pe.paid_to_account_balance = None

    weise_rechnung_zu(pe, data, camt.name, {target.name: flt(reserved)} if reserved else {}, ignore_permissions=False)

    pe.add_comment('Comment', text='Bankkonto manuell gewählt: {0} ({1}); Rechnung {2}.'.format(account, bankkonto_quelle, target.name))
    entries = [row for row in _eintraege(camt) if row['payment_entry'] != pe.name]
    frappe.db.set_value('CAMT Import', camt.name, 'matching_abweichungen', json.dumps(entries, ensure_ascii=False))

    if pe.camt_status == 'Rechnungs Match' and camt.status == 'Verarbeitet':
        frappe.db.set_value('CAMT Import', camt.name, 'status', 'Zahlungen zugeordnet')
    
    _aktualisiere_report(camt.name)

    return {
        'payment_entry': pe.name,
        'sales_invoice': target.name,
        'bankkonto': account,
        'camt_status': pe.camt_status
    }
