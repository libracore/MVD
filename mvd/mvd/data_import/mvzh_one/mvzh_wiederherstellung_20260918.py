# -*- coding: utf-8 -*-
"""
    Reparatur der MVZH-Fehlstornos vom Bereinigungslauf mit Stichtag 18.10.

    Nur mit dem damaligen Kommentar markierte, stornierte Rechnungen mit
    creation >= 18.09.2026 und creation < 18.10.2026 werden berücksichtigt.

    Vorschau (Anzahl):
        bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_one.mvzh_wiederherstellung_20260918.run

    Vollständige Vorschau mit Fortschritt, einzelnen Belegen und Blockierungsgründen:
        bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_one.mvzh_wiederherstellung_20260918.run --kwargs "{'details': True}"

    Live Run:
        bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_one.mvzh_wiederherstellung_20260918.run --kwargs "{'dry_run': False}"

    Ablauf:
        Stornierte Sinv -> prüfung ob bereits rekonstruiert -> docstatus 0 -> sinv.submit()

    Unterdrückung Mitgliedschaftsmanipulationen:
        frappe.flags.skip_mitgliedschaft_zahlungsdaten unterdrückt ihre Neuberechnung
"""
from __future__ import unicode_literals

import frappe
from frappe.utils import cint, flt, get_datetime
from tqdm import tqdm


SEKTION = 'MVZH'
VON = '2026-09-18'
BIS = '2026-10-18'
STORNO_KOMMENTAR = 'MVZH-Bereinigung: offene Rechnung erstellt vor dem 18.10.2026.'
REPARATUR_KOMMENTAR = 'MVZH-Wiederherstellung wegen falschem Bereinigungsstichtag (18.10. statt 18.09.2026).'
DOCTYPES = ('Sales Invoice', 'Fakultative Rechnung')


def run(dry_run=True, details=False):
    """Vorschau oder kontrollierte Wiederbuchung in einer eigenen bench execute."""
    dry_run = bool(cint(dry_run))
    candidates = {doctype: _get_candidates(doctype) for doctype in DOCTYPES}
    result = {
        'sektion_id': SEKTION,
        'von_inklusive': VON,
        'bis_exklusive': BIS,
        'anz_sales_invoices': len(candidates['Sales Invoice']),
        'anz_frs': len(candidates['Fakultative Rechnung'])
    }
    if dry_run and not cint(details):
        return result

    result.update({
        'bereit': 0,
        'bereits_berichtigt': 0,
        'blockiert': 0,
        'wiederhergestellt': 0,
        'fehler': 0
    })
    rows = []
    available = {}
    key = 'skip_mitgliedschaft_zahlungsdaten'
    previous = frappe.flags.get(key)
    if not dry_run:
        frappe.flags[key] = True
    try:
        # sinv zuerst, danach die fak's
        for doctype in DOCTYPES:
            for row in tqdm(candidates[doctype], desc='MVZH: {0}'.format(doctype), unit=' Rechnung'):
                item = {'doctype': doctype, 'name': row.name}
                try:
                    if not dry_run:
                        frappe.db.rollback()
                    
                    source = frappe.get_doc(doctype, row.name)
                    _check_source(source)

                    existing = _existing_amendment(source)
                    if existing:
                        item.update(status='bereits_berichtigt', ersatz=existing)
                    else:
                        _check_unpaid(source)
                        linked = _resolve_sinv(source, available, planning=dry_run) if doctype == 'Fakultative Rechnung' else None
                        if dry_run:
                            item['status'] = 'bereit'
                        else:
                            _restore(source, linked)
                            frappe.db.commit()
                            item['status'] = 'wiederhergestellt'
                    
                    if doctype == 'Sales Invoice':
                        available[source.name] = existing or source.name
                    
                except Exception as error:
                    if not dry_run:
                        frappe.db.rollback()
                    
                    item.update(status='blockiert' if dry_run else 'fehler', grund=str(error))
                
                result[item['status']] += 1
                rows.append(item)
    finally:
        if not dry_run:
            if previous is None:
                frappe.flags.pop(key, None)
            else:
                frappe.flags[key] = previous
    
    if cint(details) or not dry_run:
        result['details'] = rows
    
    return result


def _get_candidates(doctype):
    return frappe.db.sql('''
        SELECT invoice.`name`
        FROM `tab{doctype}` invoice
        WHERE invoice.`sektion_id` = %s
        AND invoice.`docstatus` = 2
        AND invoice.`creation` >= %s
        AND invoice.`creation` < %s
        AND EXISTS (
            SELECT 1 FROM `tabComment` c
            WHERE c.`reference_doctype` = %s
            AND c.`reference_name` = invoice.`name`
            AND c.`comment_type` = 'Comment'
            AND c.`content` = %s
        )
        ORDER BY invoice.`creation`, invoice.`name`
    '''.format(doctype=doctype), (SEKTION, VON, BIS, doctype, STORNO_KOMMENTAR), as_dict=True)


def _check_source(source):
    if (
        source.doctype not in DOCTYPES
        or source.sektion_id != SEKTION
        or source.docstatus != 2
        or not (get_datetime(VON) <= get_datetime(source.creation) < get_datetime(BIS))
    ):
        raise ValueError('Rechnung liegt ausserhalb der MVZH-Fehlstorno-Auswahl.')
    
    if not frappe.db.exists('Comment', {'reference_doctype': source.doctype, 'reference_name': source.name, 'comment_type': 'Comment', 'content': STORNO_KOMMENTAR}):
        raise ValueError('Der ursprüngliche Bereinigungskommentar fehlt.')


def _existing_amendment(source):
    amendments = frappe.get_all(source.doctype, filters={'amended_from': source.name}, fields=['name', 'docstatus', 'sektion_id'])
    if not amendments:
        return None
    
    if len(amendments) == 1 and amendments[0].docstatus == 1 and amendments[0].sektion_id == SEKTION:
        return amendments[0].name
    
    raise ValueError('Es existieren bereits Entwürfe, stornierte oder mehrere Berichtigungen: {0}'.format(', '.join(row.name for row in amendments)))


def _check_unpaid(source):
    if source.doctype == 'Fakultative Rechnung':
        if source.status != 'Unpaid' or source.get('bezahlt_via'):
            raise ValueError('Fakultative Rechnung ist bezahlt oder besitzt eine Zahlungsrechnung.')
        
        if source.get('qrr_referenz') and frappe.db.exists('Fakultative Rechnung', {'qrr_referenz': source.qrr_referenz, 'docstatus': 1}):
            raise ValueError('Es gibt bereits eine gebuchte FR mit derselben QR-Referenz.')
        
        return
    
    if (
        cint(source.is_return)
        or cint(source.is_pos)
        or cint(source.update_stock)
        or source.get('inter_company_invoice_reference') or source.get('redeem_loyalty_points')
        or source.get('advances') or flt(source.get('paid_amount'))
        or flt(source.get('total_advance')) or flt(source.get('write_off_amount'))
    ):
        raise ValueError('Zahlungs-, Lager- oder Sonderfall: manuelle Prüfung erforderlich.')
    
    if flt(source.grand_total) <= 0:
        raise ValueError('Kein positiver Rechnungsbetrag.')
    
    total = flt(source.get('rounded_total') or source.grand_total)
    if source.get('party_account_currency') != source.currency:
        total *= flt(source.conversion_rate)
    
    if flt(source.get('outstanding_amount')) > 0 and abs(flt(source.outstanding_amount) - total) > 0.00001:
        raise ValueError('Gespeicherter Restbetrag weicht vom Gesamtbetrag ab: mögliche Teilzahlung.')

    # Zahlungszuordnungen können beim Storno bereits entkoppelt worden sein.
    # Deshalb auch offene Kundenguthaben und Zahlungen mit gleicher QR-Referenz prüfen.
    linked = frappe.db.sql('''
        SELECT `parent` AS name
        FROM `tabPayment Entry Reference`
        WHERE `reference_doctype` = 'Sales Invoice'
        AND `reference_name` = %s
        AND `docstatus` < 2
        UNION ALL
        SELECT `parent` AS name
        FROM `tabJournal Entry Account`
        WHERE `reference_type` = 'Sales Invoice'
        AND `reference_name` = %s
        AND `docstatus` < 2
        UNION ALL
        SELECT `name` FROM `tabPayment Entry`
        WHERE `party_type` = 'Customer'
        AND `party` = %s
        AND `company` = %s
        AND `docstatus` = 1
        AND (
            `unallocated_amount` > 0
            OR
            (%s != '' AND REPLACE(COALESCE(`esr_reference`, ''), ' ', '') = %s)
        )
        UNION ALL
        SELECT `parent` AS name FROM `tabJournal Entry Account`
        WHERE `party_type` = 'Customer'
        AND `party` = %s
        AND `docstatus` = 1
        AND COALESCE(`reference_name`, '') = ''
        AND `credit_in_account_currency` > 0
        UNION ALL
        SELECT `name` FROM `tabSales Invoice`
        WHERE `docstatus` = 1
        AND %s != ''
        AND REPLACE(COALESCE(`esr_reference`, ''), ' ', '') = %s
        UNION ALL
        SELECT `voucher_no` AS name FROM `tabGL Entry`
        WHERE (
            `voucher_type` = 'Sales Invoice'
            AND `voucher_no` = %s
        ) OR (
            `against_voucher_type` = 'Sales Invoice'
            AND `against_voucher` = %s
        )
    ''', (source.name, source.name, source.customer, source.company,
        (source.get('esr_reference') or '').replace(' ', ''),
        (source.get('esr_reference') or '').replace(' ', ''), source.customer,
        (source.get('esr_reference') or '').replace(' ', ''),
        (source.get('esr_reference') or '').replace(' ', ''), source.name, source.name), as_dict=True)
    
    if linked:
        raise ValueError('Zahlungen, Ersatzrechnungen oder verbleibende Buchungen vorhanden: {0}'.format(
            ', '.join(sorted(set(row.name for row in linked)))))


def _resolve_sinv(source, available, planning=False):
    name = source.get('sales_invoice')
    if not name:
        raise ValueError('Die Verknüpfung zur Sales Invoice fehlt.')
    
    linked = frappe.get_doc('Sales Invoice', name)

    if linked.sektion_id != SEKTION:
        raise ValueError('Die verknüpfte Sales Invoice gehört nicht zu MVZH.')
    
    if linked.docstatus == 1:
        return linked.name
    
    if linked.docstatus == 2:
        existing = _existing_amendment(linked)
        if existing:
            return existing
    
        if planning and name in available:
            return available[name]
    
    raise ValueError('Die verknüpfte Sales Invoice {0} ist noch nicht wieder gebucht.'.format(name))


def _restore(source, linked_sinv=None):
    expected = source.as_dict()
    _reset_to_draft(source)
    source.clear_cache()
    source.reload()
    source.flags.ignore_permissions = True

    if source.doctype == 'Sales Invoice':
        source.flags.create_mitgliedschaftsrechnung_block = True
        source.set_posting_time = 1
        source.allocate_advances_automatically = 0
    else:
        source.sales_invoice = linked_sinv
        source.status = 'Unpaid'
    
    source.submit()

    if source.doctype == 'Fakultative Rechnung' and expected.get('qrr_referenz'):
        # before_submit erzeugt eine Referenz. QR-Referenzen müssen
        # auch bei der erneuten Buchung des Originalbelegs erhalten bleiben.
        if source.qrr_referenz != expected['qrr_referenz']:
            frappe.db.set_value(source.doctype, source.name, 'qrr_referenz', expected['qrr_referenz'])
    
    source.reload()
    _check_restored(source, expected, linked_sinv)
    source.add_comment('Comment', text=REPARATUR_KOMMENTAR + ' Originalbeleg erneut gebucht.')

    return source


def _reset_to_draft(source):
    if source.doctype not in DOCTYPES:
        raise ValueError('Nicht unterstützter Rechnungstyp.')
    
    frappe.db.sql('''
        UPDATE `tab{doctype}`
        SET
            `docstatus` = 0,
            `status` = %s
        WHERE `name` = %s
        AND `docstatus` = 2
        AND `sektion_id` = %s
        AND `creation` >= %s AND `creation` < %s
    '''.format(doctype=source.doctype), ('Draft' if source.doctype == 'Sales Invoice' else 'Unpaid', source.name, SEKTION, VON, BIS))

    if frappe.db.sql('SELECT ROW_COUNT()')[0][0] != 1:
        raise ValueError('Der stornierte Originalbeleg wurde zwischenzeitlich geändert.')
    
    for field in source.meta.get_table_fields():
        table = field.options.replace('`', '``')
        frappe.db.sql('''
            UPDATE `tab{table}`
            SET `docstatus` = 0
            WHERE `parent` = %s
            AND `parenttype` = %s
            AND `parentfield` = %s
        '''.format(table=table), (source.name, source.doctype, field.fieldname))


def _check_restored(source, expected, linked_sinv):
    if source.docstatus != 1 or any(row.docstatus != 1 for row in source.get_all_children()):
        raise ValueError('Originalbeleg oder Kindzeilen sind nicht vollständig gebucht.')
    
    fields = ['name', 'creation', 'amended_from', 'posting_date', 'due_date', 'mv_mitgliedschaft', 'company']

    if source.doctype == 'Sales Invoice':
        fields += ['customer', 'currency', 'party_account_currency', 'esr_reference', 'posting_time']
        amounts = ('grand_total', 'base_grand_total', 'rounded_total', 'base_rounded_total', 'conversion_rate')
        total = flt(expected.get('rounded_total') or expected['grand_total'])

        if expected.get('party_account_currency') != expected.get('currency'):
            total *= flt(expected.get('conversion_rate'))

        if abs(flt(source.outstanding_amount) - total) > 0.00001 or source.status in ('Draft', 'Cancelled', 'Paid'):
            raise ValueError('Restbetrag oder Rechnungsstatus nach der Wiederbuchung ist nicht korrekt.')
        
        if not frappe.db.exists('GL Entry', {'voucher_type': source.doctype, 'voucher_no': source.name}):
            raise ValueError('Die Buchhaltungseinträge der wieder gebuchten Rechnung fehlen.')
    else:
        amounts = ('betrag',)
        if source.sales_invoice != linked_sinv or source.status != 'Unpaid':
            raise ValueError('Verknüpfung oder Status der fakultativen Rechnung ist nicht korrekt.')
        
        if expected.get('qrr_referenz'):
            fields.append('qrr_referenz')

    for field in fields:
        if str(source.get(field) or '') != str(expected.get(field) or ''):
            raise ValueError('Feld {0} hat sich geändert; Wiederbuchung wird zurückgerollt.'.format(field))
        
    for field in amounts:
        if abs(flt(source.get(field)) - flt(expected.get(field))) > 0.00001:
            raise ValueError('Betrag {0} hat sich geändert; Wiederbuchung wird zurückgerollt.'.format(field))
