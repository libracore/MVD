# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from mvd.mvd.doctype.camt_import.reset_protokoll import lade, normalisiere, fingerprint


REIHENFOLGE = [
    'File',
    'Email Queue',
    'ToDo',
    'Communication',
    'Status Change',
    'Korrespondenz',
    'Payment Entry',
    'Journal Entry',
    'Sales Invoice',
    'Fakultative Rechnung'
]

def _legacy_faks(payments):
    references = set()
    for pe in payments:
        references.update(row.reference_name for row in pe.references if row.reference_doctype == 'Sales Invoice')
        if pe.get('camt_verrechnung_rechnung'):
            references.add(pe.camt_verrechnung_rechnung)
    
    if not references:
        return []
    
    return frappe.get_all('Fakultative Rechnung', filters={'status': 'Paid', 'bezahlt_via': ['in', list(references)]}, fields=['name', 'bezahlt_via', 'qrr_referenz'])

def _fak_vorzustand(row, current, records):
    before = row.get('vorher')
    after = row.get('nachher')
    if not before or not after or current is None:
        return None
    
    fields = [field for field in before if field not in ('modified', 'modified_by')]
    if not fields:
        return None
    
    if any(current.get(field) not in (before.get(field), after.get(field)) for field in fields):
        return None
    
    changed_links = [field for field in ('bezahlt_via', 'sales_invoice') if field in before and after.get(field) and before.get(field) != after.get(field)]
    if any(('Sales Invoice', after[field]) not in records for field in changed_links):
        return None
    
    if any(before.get(field) != after.get(field) for field in fields) and not changed_links:
        return None
    
    values = dict((field, before[field]) for field in fields)
    if all(current.get(field) == after.get(field) for field in ('modified', 'modified_by')):
        values.update((field, before[field]) for field in ('modified', 'modified_by') if field in before)
    
    return values

def _nachgewiesener_eigener_storno(camt, invoice):
    if invoice.doctype != 'Sales Invoice' or not invoice.meta or not invoice.meta.track_changes:
        return False

    pairs = frappe.db.sql("""
        SELECT je.creation
        FROM `tabJournal Entry` je
        INNER JOIN `tabJournal Entry Account` ref ON ref.parent = je.name
        INNER JOIN `tabPayment Entry` pe ON pe.name = je.camt_verrechnung_zahlung
        WHERE ref.reference_type = 'Sales Invoice'
        AND ref.reference_name = %s
        AND je.docstatus = 2
        AND pe.docstatus = 2
        AND pe.camt_import = %s
        AND pe.camt_verrechnung_journal = je.name
        AND pe.camt_verrechnung_rechnung = %s
        AND je.company = %s
        ORDER BY je.creation ASC LIMIT 1
    """, (invoice.name, camt.name, invoice.name, invoice.company), as_dict=True)

    if not pairs:
        return False
    
    versions = frappe.db.sql("""
        SELECT data FROM `tabVersion`
        WHERE ref_doctype = 'Sales Invoice' AND docname = %s AND creation >= %s
    """, (invoice.name, pairs[0].creation), as_dict=True)

    for version in versions:
        try:
            changes = json.loads(version.data or '{}')
        except (TypeError, ValueError):
            return False
        
        if not isinstance(changes, dict) or any(changes.get(key) for key in ('added', 'removed', 'row_changed')):
            return False
        
        if any(row[0] not in ('status', 'outstanding_amount', 'modified', 'modified_by') for row in changes.get('changed', [])):
            return False
    
    return True

def _plan(camt, fortschritt=None):
    data = lade(camt.name) or {'vorher': [], 'erstellt': [], 'vollstaendig': False}
    if data.get('offen'):
        frappe.throw('Ein CAMT-Verarbeitungsschritt wurde nicht vollständig abgeschlossen. Bitte prüfen Sie zuerst dessen Fehlerprotokoll.')
    
    payment_rows = frappe.get_all('Payment Entry', filters={'camt_import': camt.name}, fields=['name'], order_by='creation desc')
    payments = []
    for index, row in enumerate(payment_rows):
        payments.append(frappe.get_doc('Payment Entry', row.name))
        if fortschritt:
            fortschritt(10 * (index + 1) / max(1, len(payment_rows)), 'Lade Zahlungen ({0}/{1})'.format(index + 1, len(payment_rows)))
    
    records = dict((('Payment Entry', pe.name), pe) for pe in payments)
    restore = []
    hinweise = []
    mitglied_konflikte = set()
    members = set(pe.mv_mitgliedschaft for pe in payments if pe.mv_mitgliedschaft)
    for pe in payments:
        if pe.get('camt_verrechnung_journal'):
            journal = frappe.get_doc('Journal Entry', pe.camt_verrechnung_journal)
            if journal.get('camt_verrechnung_zahlung') != pe.name:
                frappe.throw('Die Firmenverrechnung {0} hat widersprüchliche Belegverknüpfungen.'.format(pe.name))
            
            records[('Journal Entry', journal.name)] = journal
        
        for ref in pe.references:
            if ref.reference_doctype == 'Sales Invoice':
                member = frappe.db.get_value('Sales Invoice', ref.reference_name, 'mv_mitgliedschaft')
                if member:
                    members.add(member)
    
    for row in data['erstellt']:
        key = (row['doctype'], row['name'])
        if row['doctype'] not in REIHENFOLGE:
            frappe.throw('Das Rücksetzprotokoll enthält eine nicht unterstützte Belegart.')
        
        if not frappe.db.exists(*key):
            continue
            
        frappe.db.sql('SELECT name FROM `tab{0}` WHERE name=%s FOR UPDATE'.format(key[0]), (key[1],))
        doc = frappe.get_doc(*key)
        records[key] = doc

        if row['doctype'] not in ('Payment Entry', 'Journal Entry', 'Email Queue'):
            matches = bool(row.get('fingerprint') and fingerprint(doc) == row['fingerprint'])
            conflict = row.get('konflikt')
            if conflict and matches:
                conflict = not _nachgewiesener_eigener_storno(camt, doc)
            if conflict or not matches:
                frappe.throw('Der erzeugte Beleg {0} {1} wurde nachträglich verändert. Bitte prüfen Sie ihn vor dem Reset.'.format(*key))
    
    for row in data['vorher']:
        key = (row['doctype'], row['name'])
        if key[0] not in ('Mitgliedschaft', 'Mitglied Main Naming', 'Fakultative Rechnung'):
            frappe.throw('Das Rücksetzprotokoll enthält einen nicht unterstützten Vorzustand.')
        
        frappe.db.sql('SELECT name FROM `tab{0}` WHERE name=%s FOR UPDATE'.format(key[0]), (key[1],))
        current = normalisiere(frappe.db.get_value(key[0], key[1], list(row['vorher']), as_dict=True))
        if key[0] == 'Fakultative Rechnung':
            values = _fak_vorzustand(row, current, records)
            if values is None:
                frappe.throw('Die Rechnungsverknüpfung oder andere protokollierte FAK-Daten von {0} weichen vom eigenen CAMT-Vorgang ab. Bitte prüfen Sie die FAK vor dem Reset.'.format(key[1]))
            
            restored = dict(row)
            restored['vorher'] = values
            restore.append(restored)
            continue

        if not row.get('konflikt') and current == row.get('nachher'):
            restore.append(row)
            if key[0] == 'Mitgliedschaft':
                members.discard(key[1])
        elif key[0] in ('Mitgliedschaft', 'Mitglied Main Naming'):
            hinweise.append('{0} {1}: spätere Änderungen vorhanden; Vorzustand nicht wiederhergestellt.'.format(*key))
            mitglied = key[1] if key[0] == 'Mitgliedschaft' else frappe.db.get_value(key[0], key[1], 'mitglied_id')
            mitglied_konflikte.add(str(mitglied))
            members.discard(mitglied)
        else:
            frappe.throw('Der Vorzustand von {0} {1} kann wegen späterer Änderungen nicht sicher wiederhergestellt werden.'.format(*key))

    restore = [row for row in restore if not (row['doctype'] == 'Mitgliedschaft' and row['name'] in mitglied_konflikte or row['doctype'] == 'Mitglied Main Naming' and str(frappe.db.get_value(row['doctype'], row['name'], 'mitglied_id')) in mitglied_konflikte)]
    
    for fak in _legacy_faks(payments):
        key = ('Sales Invoice', fak.bezahlt_via)
        if key not in records:
            hinweise.append('FAK {0} / Rechnung {1}: kein Herkunftsnachweis im Rücksetzprotokoll; Rechnung bleibt offen bestehen.'.format(fak.name, fak.bezahlt_via))

    hinweise.extend('Mitgliedschaft {0}: kein verlässlicher Vorzustand vorhanden; bitte Zahlungsdaten und Beitritt prüfen.'.format(member) for member in sorted(members))

    for key, doc in records.items():
        doc.check_permission('delete')
        if doc.docstatus == 1:
            doc.check_permission('cancel')
        if key[0] == 'Email Queue' and doc.status == 'Sending':
            frappe.throw('Eine zugehörige E-Mail wird gerade versendet. Bitte warten Sie vor dem Reset.')
    
    return records, restore, hinweise

def _pruefe_abhaengigkeiten(records, restore):
    from frappe.model.rename_doc import get_link_fields
    from frappe.model.dynamic_links import get_dynamic_link_map
    from frappe.model.delete_doc import doctypes_to_skip
    allowed_changes = dict(((row['doctype'], row['name']), row['vorher']) for row in restore)

    def pruefe(doctype, field, item, target, dynamic=False):
        owner = (item.parenttype, item.parent) if item.get('parent') else (doctype, item.name)
        if doctype in ('GL Entry', 'Stock Ledger Entry'):
            owner = (item.voucher_type, item.voucher_no)
        
        if owner in records or (dynamic and item.docstatus == 2):
            return
        
        if allowed_changes.get(owner, {}).get(field, target.name) != target.name:
            return
        
        if doctype == 'Mitgliedschaft' and field == 'begruessung_massendruck_dokument':
            allowed_changes.setdefault(owner, {})[field] = None
            return
        
        frappe.throw('Reset nicht möglich: {0} {1} verweist ausserhalb dieses Imports auf {2} {3}.'.format(owner[0], owner[1], target.doctype, target.name))

    grouped = {}
    for doc in records.values():
        grouped.setdefault(doc.doctype, {})[doc.name] = doc
    
    for target_doctype, targets in grouped.items():
        names = list(targets)
        for df in get_link_fields(target_doctype):
            if df.parent in doctypes_to_skip:
                continue

            meta = frappe.get_meta(df.parent)
            if meta.issingle:
                value = frappe.db.get_single_value(df.parent, df.fieldname)
                if value in targets:
                    frappe.throw('Reset nicht möglich: {0} verweist auf {1}.'.format(df.parent, value))
                continue

            fields = ['name', 'parent', 'parenttype', 'docstatus', df.fieldname]
            if df.parent in ('GL Entry', 'Stock Ledger Entry'):
                fields += ['voucher_type', 'voucher_no']
            
            for start in range(0, len(names), 200):
                for item in frappe.get_all(df.parent, filters={df.fieldname: ['in', names[start:start + 200]]}, fields=fields, ignore_ifnull=True, order_by='name'):
                    pruefe(df.parent, df.fieldname, item, targets[item.get(df.fieldname)])
        
        for df in get_dynamic_link_map().get(target_doctype, []):
            if df.parent in doctypes_to_skip:
                continue

            meta = frappe.get_meta(df.parent)
            if meta.issingle:
                values = frappe.db.get_singles_dict(df.parent)
                if values.get(df.options) == target_doctype and values.get(df.fieldname) in targets:
                    frappe.throw('Reset nicht möglich: {0} verweist auf {1}.'.format(df.parent, values.get(df.fieldname)))

                continue

            fields = ['name', 'parent', 'parenttype', 'docstatus', df.fieldname]
            if df.parent in ('GL Entry', 'Stock Ledger Entry'):
                fields += ['voucher_type', 'voucher_no']
            
            for start in range(0, len(names), 200):
                for item in frappe.get_all(
                    df.parent,
                    filters={
                        df.options: target_doctype,
                        df.fieldname: ['in', names[start:start + 200]]
                    },
                    fields=fields,
                    ignore_ifnull=True,
                    order_by='name'
                ):
                    pruefe(df.parent, df.fieldname, item, targets[item.get(df.fieldname)], dynamic=True)
    
    return allowed_changes

def _leere_import(camt):
    for df in camt.meta.fields:
        if df.read_only and df.fieldtype in ('Int', 'Currency', 'Float'):
            camt.set(df.fieldname, 0)
        elif df.read_only and df.fieldtype in ('Code', 'Date') and df.fieldname != 'reset_protokoll':
            camt.set(df.fieldname, None)
    
    camt.status = 'Open'
    camt.reset_protokoll = None
    camt.save()

def zuruecksetzen(camt):
    if 'System Manager' not in frappe.get_roles() or frappe.local.request.method != 'POST':
        frappe.throw('Nur System Manager dürfen einen CAMT-Reset per POST ausführen.', frappe.PermissionError)
    
    return _zuruecksetzen(camt)

def _zuruecksetzen(camt, reset_token=None, fortschritt=None):
    if 'System Manager' not in frappe.get_roles():
        frappe.throw('Nur System Manager dürfen einen CAMT-Reset ausführen.', frappe.PermissionError)
    
    frappe.db.sql('SELECT name FROM `tabCAMT Import` WHERE name=%s FOR UPDATE', (camt,))
    doc = frappe.get_doc('CAMT Import', camt)
    doc.check_permission('write')
    data = lade(camt) or {}
    eigener_reset = reset_token and (data.get('reset_auftrag') or {}).get('token') == reset_token

    if reset_token and not eigener_reset:
        frappe.throw('Der CAMT-Reset gehört nicht mehr zum aktuellen Auftrag.')
    
    if doc.status == 'In Verarbeitung' and not eigener_reset:
        frappe.throw('Bitte warten Sie, bis die CAMT-Verarbeitung abgeschlossen ist.')
    
    records, restore, hinweise = _plan(doc, fortschritt=fortschritt)
    if fortschritt:
        fortschritt(15, 'Prüfe Belegverknüpfungen und Abhängigkeiten')
    
    changes = _pruefe_abhaengigkeiten(records, restore)
    old_skip = frappe.flags.get('skip_mitgliedschaft_zahlungsdaten')
    old_reset = frappe.flags.get('camt_reset_in_arbeit')
    old_guard = frappe.flags.get('camt_verrechnung_in_arbeit')
    frappe.flags.skip_mitgliedschaft_zahlungsdaten = True
    frappe.flags.camt_reset_in_arbeit = True

    try:
        payments = [pe for key, pe in records.items() if key[0] == 'Payment Entry']
        for index, pe in enumerate(payments):
            if pe.get('camt_verrechnung_journal'):
                journal = records[('Journal Entry', pe.camt_verrechnung_journal)]
                frappe.flags.camt_verrechnung_in_arbeit = pe.name
                pe.db_set('camt_verrechnung_journal', None)
                if journal.docstatus == 1:
                    journal.cancel()
            
            if pe.docstatus == 1:
                pe.cancel()
            
            if fortschritt:
                fortschritt(30 + 25 * (index + 1) / max(1, len(payments)), 'Storniere Zahlungen ({0}/{1})'.format(index + 1, len(payments)))
        
        for key, values in changes.items():
            frappe.db.set_value(key[0], key[1], values, update_modified=False)
        
        for key, record in records.items():
            for field in ('camt_verrechnung_journal', 'camt_verrechnung_rechnung', 'camt_verrechnung_zahlung', 'amended_from'):
                if record.get(field):
                    record.db_set(field, None)
            if key[0] == 'Fakultative Rechnung':
                record.db_set({'bezahlt_via': None, 'sales_invoice': None})
        
        deleted = 0
        for doctype in REIHENFOLGE:
            for key, record in records.items():
                if key[0] != doctype:
                    continue

                record = frappe.get_doc(*key)
                if record.docstatus == 1:
                    if doctype == 'Journal Entry':
                        frappe.flags.camt_verrechnung_in_arbeit = record.get('camt_verrechnung_zahlung')
                    record.cancel()
                
                if doctype == 'Email Queue':
                    frappe.delete_doc(doctype, record.name, ignore_on_trash=True)
                else:
                    record.delete()
                
                deleted += 1

                if fortschritt:
                    fortschritt(60 + 39 * deleted / max(1, len(records)), 'Entferne Belege ({0}/{1})'.format(deleted, len(records)))
        
        _leere_import(frappe.get_doc('CAMT Import', camt))

        return {
            'geloeschte_belege': len(records),
            'hinweise': hinweise,
            'externe_aktionen': 'Bereits versendete E-Mails, Nextcloud-Aktionen und verbrauchte Nummern können nicht zurückgeholt werden.'
        }
    except Exception:
        frappe.db.rollback()
        raise
    
    finally:
        frappe.flags.skip_mitgliedschaft_zahlungsdaten = old_skip
        frappe.flags.camt_reset_in_arbeit = old_reset
        frappe.flags.camt_verrechnung_in_arbeit = old_guard
