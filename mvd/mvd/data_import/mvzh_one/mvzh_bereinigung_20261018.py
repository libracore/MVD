# -*- coding: utf-8 -*-
"""Einmalige MVZH-Bereinigung; standardmässig ausschliesslich Vorschau.

Aufruf über bench execute:
    mvd.mvd.data_import.mvzh_one.mvzh_bereinigung_20261018.run
    mvd.mvd.data_import.mvzh_one.mvzh_bereinigung_20261018.run --kwargs "{'dry_run': False}"

Erstellt = creation, strikt vor 18.10.2026 (00:00 Uhr).
Gebuchte, teilbezahlte Sales Invoices mit positivem Restbetrag sind offen.
Entwürfe, bezahlte Rechnungen und Gutschriften werden nicht storniert.
Fakultative Rechnungen werden nur mit vorhandener verknüpfter Sales Invoice storniert.
Erfolgreiche Stornos werden einzeln bestätigt; Fehler stehen im Ergebnis.
Bestehende Frappe-Hooks können Teiländerungen bereits vorher bestätigen.
"""
from __future__ import unicode_literals

import frappe
from frappe.utils import cint, flt, get_datetime, now
from tqdm import tqdm


SEKTION = 'MVZH'
STICHTAG = '2026-10-18'
KOMMENTAR = 'MVZH-Bereinigung: offene Rechnung erstellt vor dem 18.10.2026.'


def run(dry_run=True):
    dry_run = bool(cint(dry_run))
    filters = {'sektion_id': SEKTION, 'creation': ['<', STICHTAG], 'docstatus': 1}
    sinvs = frappe.get_all('Sales Invoice',
        filters=dict(filters, outstanding_amount=['>', 0], is_return=0),
        fields=['name'], order_by='creation, name')
    frs = frappe.db.sql('''
        SELECT fr.`name`
        FROM `tabFakultative Rechnung` fr
        INNER JOIN `tabSales Invoice` sinv ON sinv.`name` = fr.`sales_invoice`
        WHERE fr.`sektion_id` = %s AND fr.`creation` < %s
            AND fr.`docstatus` = 1 AND fr.`status` = 'Unpaid'
        ORDER BY fr.`creation`, fr.`name`
    ''', (SEKTION, STICHTAG), as_dict=True)
    if dry_run:
        return {
            'sektion_id': SEKTION,
            'stichtag_exklusiv': STICHTAG,
            'anz_sales_invoices': len(sinvs),
            'anz_frs': len(frs)
        }

    result = {
        'dry_run': dry_run,
        'sektion_id': SEKTION,
        'stichtag_exklusiv': STICHTAG,
        'mitgliedschaften': frappe.get_all('Mitgliedschaft',
            filters=[
                ['sektion_id', '=', SEKTION],
                ['datum_zahlung_mitgliedschaft', '<', STICHTAG],
                ['datum_zahlung_mitgliedschaft', 'is', 'set']
            ],
            fields=['name', 'datum_zahlung_mitgliedschaft'], order_by='name'),
        'sales_invoices': [row.name for row in sinvs],
        'fakultative_rechnungen': [row.name for row in frs],
        'anz_sales_invoices': len(sinvs),
        'anz_frs': len(frs),
        'storniert': [],
        'mahnungen_storniert': [],
        'uebersprungen': [],
        'fehler': [],
        'zahlungsdaten_geleert': 0
    }
    # Zuerst FR stornieren, damit unlink_fr keine fremden/neuen FR verändert
    # und keinen Zwischenstand innerhalb eines Rechnungsstornos committet.
    for doctype, rows in (('Fakultative Rechnung', frs), ('Sales Invoice', sinvs)):
        for row in tqdm(rows, desc='MVZH: {0} stornieren'.format(doctype),
                unit=' Rechnung', total=len(rows)):
            try:
                reminders = []
                document = frappe.get_doc(doctype, row.name)
                if not _is_open_target(document):
                    result['uebersprungen'].append({'doctype': doctype, 'name': row.name})
                    continue
                if doctype == 'Sales Invoice':
                    reminders = _cancel_dependencies(document)
                    # Mahnungsstornos speichern die verknüpften Rechnungen.
                    document.reload()
                    if not _is_open_target(document):
                        frappe.throw('Rechnung {0} wurde zwischenzeitlich geändert.'.format(row.name))
                document.cancel()
                document.add_comment('Comment', text=KOMMENTAR)
                frappe.db.commit()
                result['storniert'].append({'doctype': doctype, 'name': row.name})
                result['mahnungen_storniert'].extend(reminders)
            except Exception as error:
                frappe.db.rollback()
                result['fehler'].append({
                    'doctype': doctype, 'name': row.name, 'fehler': str(error)
                })

    # Zuletzt leeren: Die normalen Rechnungs-/Mahnungs-Hooks können das
    # Zahlungsdatum anhand bezahlter Rechnungen erneut setzen.
    try:
        frappe.db.sql('''
            UPDATE `tabMitgliedschaft`
            SET `datum_zahlung_mitgliedschaft` = NULL,
                `modified` = %s, `modified_by` = %s
            WHERE `sektion_id` = %s
                AND `datum_zahlung_mitgliedschaft` < %s
        ''', (now(), frappe.session.user, SEKTION, STICHTAG))
        result['zahlungsdaten_geleert'] = frappe.db.sql('SELECT ROW_COUNT()')[0][0]
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise
    return result


def _is_open_target(document):
    if (document.sektion_id != SEKTION or document.docstatus != 1
            or get_datetime(document.creation) >= get_datetime(STICHTAG)):
        return False
    if document.doctype == 'Sales Invoice':
        return not cint(document.is_return) and flt(document.outstanding_amount) > 0
    return (document.status == 'Unpaid' and bool(document.sales_invoice)
        and bool(frappe.db.exists('Sales Invoice', document.sales_invoice)))


def _check_membership(invoice):
    # sinv_update aktualisiert auch die verknüpfte Mitgliedschaft.
    if (invoice.mv_mitgliedschaft and frappe.db.get_value(
            'Mitgliedschaft', invoice.mv_mitgliedschaft, 'sektion_id') != SEKTION):
        frappe.throw('Rechnung {0}: verknüpfte Mitgliedschaft gehört nicht zu MVZH.'.format(invoice.name))


def _cancel_dependencies(invoice):
    _check_membership(invoice)
    if frappe.db.exists('Fakultative Rechnung', {'sales_invoice': invoice.name, 'docstatus': 1}):
        frappe.throw('Rechnung {0}: noch gebuchte fakultative Rechnung verknüpft. '
            'Diese wird nicht automatisch entkoppelt.'.format(invoice.name))

    reminders = frappe.db.sql('''
        SELECT DISTINCT `parent`
        FROM `tabMahnung Invoices`
        WHERE `sales_invoice` = %s AND `docstatus` = 1
            AND `parenttype` = 'Mahnung' AND `parentfield` = 'sales_invoices'
    ''', (invoice.name,), as_dict=True)
    # Alle Abhängigkeiten prüfen, bevor der erste Mahnungsstorno ausgeführt wird.
    documents = []
    for row in reminders:
        reminder = frappe.get_doc('Mahnung', row.parent)
        if reminder.docstatus != 1:
            continue
        if reminder.sektion_id != SEKTION:
            frappe.throw('Mahnung {0} gehört nicht zu MVZH.'.format(reminder.name))
        for entry in reminder.sales_invoices:
            linked = frappe.get_doc('Sales Invoice', entry.sales_invoice)
            if not _is_open_target(linked):
                frappe.throw('Mahnung {0} enthält Rechnung {1} ausserhalb der Auswahl.'.format(
                    reminder.name, linked.name))
            _check_membership(linked)
        documents.append(reminder)
    for reminder in documents:
        reminder.cancel()
        reminder.add_comment('Comment', text=KOMMENTAR)
    return [reminder.name for reminder in documents]
