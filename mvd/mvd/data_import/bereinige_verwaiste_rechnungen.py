# -*- coding: utf-8 -*-
"""Bereinigung bestätigter Ersatzfälle aus einem gespeicherten Prüfbericht.

1. bench execute mvd.mvd.data_import.pruefe_verwaiste_rechnungen.run --kwargs "{'save_report': True}"
2. bench execute mvd.mvd.data_import.bereinige_verwaiste_rechnungen.run --kwargs "{'report': 'pruefung_verwaiste_rechnungen_HASH.json', 'replacements': {'ALT': 'ERSATZ'}}"
3. Derselbe Aufruf mit zusätzlich 'dry_run': False.

Nur in einer eigenen bench execute verwenden. Der Bericht ist keine Freigabe:
replacements enthält die vom Anwender fachlich bestätigten 1:1-Ersatzfälle.
Nur unveränderte, ausgeglichene Buchungen in Basiswährung ohne Fremdbezüge
werden entfernt. Sämtliche ausgewählten Fälle bilden eine DB-Transaktion.

trust_report=True verwendet ausschliesslich die gespeicherten Originalzeilen.
Keine erneuten Beleg-, Saldo-, Perioden-, Konten- oder Budgetprüfungen. Dieser
Modus wird von der UI für bereits freigegebene Fälle verwendet. Gesichert
wird der gespeicherte Prüfbefund, kein neu ausgelesener DB-Zustand.
Eine Ersatzrechnung ist dabei optional: replacements={'ALT': None}.
"""
from __future__ import unicode_literals

import hashlib
import json
import os

import frappe
from frappe.utils import flt, now


REPORT_VERSION = 1
BATCH_SIZE = 200
MARKER = 'Bereinigung verwaiste Rechnung {0}: bestätigter 1:1-Ersatz {1}.'


def save_report(result):
    """Originalzeilen gebündelt ergänzen und Bericht privat speichern; keine DB-Schreibzugriffe."""
    # Die Konsolenausgabe bleibt kompakt; die Datei enthält die vollständigen Snapshots.
    cases = [dict(row) for row in result.get('faelle', [])]
    snapshots = read_snapshots([row['rechnung'] for row in cases])
    for row in cases:
        row['snapshot'] = snapshots[row['rechnung']]
        row['fingerprint'] = fingerprint(row['snapshot'])
    payload = dict(result, faelle=cases, report_version=REPORT_VERSION,
        site=frappe.local.site, erstellt_am=now())
    return _write_private('pruefung_verwaiste_rechnungen', payload)


def fingerprint(state):
    return hashlib.sha256(frappe.as_json(state, indent=None).encode('utf-8')).hexdigest()


def read_snapshots(names, lock=False):
    """Exakte Originalzeilen inkl. aller Rechnungskindtabellen und Fremdbezüge."""
    names = list(set(names))
    if not names or any(not isinstance(name, str) or not name for name in names):
        if not names:
            return {}
        raise ValueError('Ungültige Rechnungsnummer im Bericht.')
    names.sort()
    tables = sorted(set(field.options for field in frappe.get_meta('Sales Invoice').get_table_fields()))
    states = {name: {'gl': [], 'children': {table: [] for table in tables}, 'references': []}
        for name in names}
    suffix = ' FOR UPDATE' if lock else ''
    for offset in range(0, len(names), BATCH_SIZE):
        batch = tuple(names[offset:offset + BATCH_SIZE])
        slots = ', '.join(['%s'] * len(batch))
        for row in frappe.db.sql('''SELECT * FROM `tabGL Entry`
                WHERE voucher_type = 'Sales Invoice' AND voucher_no IN ({0}) ORDER BY name'''.format(
                slots) + suffix, batch, as_dict=True):
            states[row['voucher_no']]['gl'].append(row)
        for table in tables:
            for row in frappe.db.sql('''SELECT * FROM `tab{0}`
                    WHERE parenttype = 'Sales Invoice' AND parent IN ({1}) ORDER BY name'''.format(
                    table, slots) + suffix, batch, as_dict=True):
                states[row['parent']]['children'][table].append(row)
        # Alle Stati berücksichtigen; Fremdbezüge werden niemals automatisch entkoppelt.
        reference_query = '''
            SELECT against_voucher AS rechnung, 'GL Entry' AS doctype, name AS beleg
            FROM `tabGL Entry` WHERE against_voucher_type = 'Sales Invoice'
                AND against_voucher IN ({0})
                AND NOT (voucher_type = 'Sales Invoice' AND voucher_no = against_voucher)
            UNION ALL
            SELECT reference_name AS rechnung, 'Payment Entry' AS doctype, parent AS beleg FROM `tabPayment Entry Reference`
                WHERE reference_doctype = 'Sales Invoice' AND reference_name IN ({0})
            UNION ALL
            SELECT reference_name AS rechnung, 'Journal Entry' AS doctype, parent AS beleg FROM `tabJournal Entry Account`
                WHERE reference_type = 'Sales Invoice' AND reference_name IN ({0})
            UNION ALL
            SELECT amended_from AS rechnung, 'Sales Invoice' AS doctype, name AS beleg FROM `tabSales Invoice` WHERE amended_from IN ({0})
            UNION ALL
            SELECT return_against AS rechnung, 'Sales Invoice' AS doctype, name AS beleg FROM `tabSales Invoice` WHERE return_against IN ({0})
            UNION ALL
            SELECT sales_invoice AS rechnung, 'Fakultative Rechnung' AS doctype, name AS beleg FROM `tabFakultative Rechnung`
                WHERE sales_invoice IN ({0})
            UNION ALL
            SELECT sales_invoice AS rechnung, 'Mahnung' AS doctype, parent AS beleg FROM `tabMahnung Invoices` WHERE sales_invoice IN ({0})
        '''.format(slots)
        if lock:
            # Einzelne SELECTs: aktuelle InnoDB-Lesesperren auch für Fremdbezüge.
            # Ein UNION als normale Snapshot-Lesung könnte neue Bezüge übersehen.
            references = []
            for query in reference_query.split('UNION ALL'):
                references.extend(frappe.db.sql(query + suffix, batch, as_dict=True))
        else:
            references = frappe.db.sql(reference_query, batch * 7, as_dict=True)
        for row in references:
            states[row['rechnung']]['references'].append(row)
    for state in states.values():
        state['references'].sort(key=lambda row: (row['doctype'], row['beleg'] or ''))
    return states


def run(report, replacements, dry_run=True, expected_replacements=None, commit=True, trust_report=False):
    """Ausgewählte, fachlich bestätigte Ersatzfälle prüfen oder gemeinsam bereinigen."""
    if dry_run not in (True, False, '0', '1'):
        raise ValueError('dry_run muss True/False oder 1/0 sein.')
    dry_run = dry_run in (True, '1')
    if trust_report not in (True, False, '0', '1'):
        raise ValueError('trust_report muss True/False oder 1/0 sein.')
    trust_report = trust_report in (True, '1')
    report = _load_report(report)
    if isinstance(replacements, str):
        replacements = json.loads(replacements)
    if not isinstance(replacements, dict) or not replacements or any(
            not isinstance(old, str) or not old or old == new
            or (new is not None and not isinstance(new, str)) or (not trust_report and not new)
            for old, new in replacements.items()):
        raise ValueError('replacements muss freigegebene Rechnungen enthalten; ohne Ersatz ist nur trust_report=True zulässig.')
    replacements = {old: new or None for old, new in replacements.items()}
    cases = {}
    for row in report['faelle']:
        old = row['rechnung']
        if old in replacements:
            if old in cases:
                raise ValueError('Rechnung {0} ist im Bericht nicht eindeutig.'.format(old))
            if fingerprint(row.get('snapshot')) != row.get('fingerprint'):
                raise ValueError('Snapshot-Prüfsumme für {0} stimmt nicht.'.format(old))
            cases[old] = row
    if set(cases) != set(replacements):
        raise ValueError('Mindestens eine ausgewählte Rechnung fehlt im gespeicherten Bericht.')
    if trust_report:
        return _run_saved(cases, replacements, dry_run, commit, expected_replacements)

    backup = None
    try:
        states = read_snapshots(list(cases), lock=not dry_run)
        rows, plans = [], []
        for old in sorted(cases):
            new = replacements[old]
            row = {'rechnung': old, 'ersatz': new}
            try:
                plan = _prepare(cases[old], new, states[old], lock=not dry_run)
                if (plan['result']['status'] == 'bereit' and expected_replacements is not None
                        and replacement_fingerprint(plan) != expected_replacements.get(old)):
                    raise ValueError('Die Ersatzrechnung wurde seit der Freigabe geändert. Erneut freigeben.')
                row.update(plan['result'])
                if row['status'] == 'bereit':
                    plans.append(plan)
            except ValueError as error:
                row.update(status='blockiert', grund=str(error))
            rows.append(row)
        result = {'dry_run': dry_run, 'faelle': rows, 'anz_ausgewaehlt': len(rows)}
        if any(row['status'] == 'blockiert' for row in rows):
            if not dry_run:
                frappe.db.rollback()
            result['status'] = 'blockiert'
            return result
        result['status'] = 'bereit' if plans else 'bereits_bereinigt'
        if dry_run or not plans:
            if not dry_run and commit:
                frappe.db.rollback()  # Lesesperren eines Wiederholungsaufrufs freigeben.
            return result

        from erpnext.accounts.general_ledger import delete_gl_entries, validate_accounting_period
        for plan in plans:
            validate_accounting_period([frappe._dict(row) for row in plan['state']['gl']])
        before = _balances(plans)
        backup = _write_private('bereinigung_verwaiste_rechnungen', {
            'site': frappe.local.site, 'zeitpunkt': now(), 'benutzer': frappe.session.user,
            'plaene': plans, 'salden_vorher': before
        })
        for plan in plans:
            old = plan['old']
            delete_gl_entries(voucher_type='Sales Invoice', voucher_no=old, update_outstanding='No')
            for table, children in plan['state']['children'].items():
                if children:
                    frappe.db.sql('DELETE FROM `tab{0}` WHERE parent = %s AND parenttype = %s'.format(
                        table), (old, 'Sales Invoice'))

        remaining = read_snapshots([plan['old'] for plan in plans], lock=True)
        after = _balances(plans)
        for key, balance in before.items():
            delta = sum(plan['amount'] for plan in plans if _balance_key(plan) == key)
            if not _equal(after[key], balance - delta):
                raise ValueError('Kundensaldo weicht von der erwarteten Änderung ab: {0}'.format(key))
        for plan in plans:
            old, new = plan['old'], plan['new']
            if not _empty(remaining[old]) or remaining[old]['references']:
                raise ValueError('Es sind Restdaten oder neue Bezüge zu {0} vorhanden.'.format(old))
            if _header(old, lock=True):
                raise ValueError('Der ursprüngliche Rechnungskopf existiert wieder: {0}'.format(old))
            _unchanged_replacement(plan)
            frappe.get_doc('Sales Invoice', new).add_comment('Info', text=(
                '{0} Verwaiste Hauptbuch- und Kindzeilen entfernt. '
                'Entfernte Kundenbelastung: {1} {2:.2f}. Sicherung: {3}'
            ).format(MARKER.format(old, new), plan['currency'], plan['amount'], os.path.basename(backup)))
        if commit:
            frappe.db.commit()
        for row in rows:
            if row['status'] == 'bereit':
                row['status'] = 'bereinigt'
        result.update(status='bereinigt', sicherung=backup, salden_vorher=before, salden_nachher=after)
        return result
    except Exception:
        if not dry_run:
            frappe.db.rollback()
            if backup:
                print('DB-Änderungen zurückgerollt. Ausgangszustand gesichert: {0}'.format(backup))
        raise


def _run_saved(cases, replacements, dry_run, commit, approval_fingerprints):
    """Exakt gespeicherte Zeilen löschen; keine aktuellen Geschäftsdaten lesen."""
    allowed = set(field.options for field in frappe.get_meta('Sales Invoice').get_table_fields())
    targets = {'GL Entry': []}
    results = []
    for old in sorted(cases):
        state = cases[old]['snapshot']
        # Nur Dateiformat und Zielzuordnung prüfen, keine erneute fachliche Prüfung.
        for row in state['gl']:
            if not row.get('name') or row.get('voucher_type') != 'Sales Invoice' or row.get('voucher_no') != old:
                raise ValueError('Ungültige Hauptbuch-Zielzeile im gespeicherten Befund: {0}'.format(old))
            targets['GL Entry'].append(row['name'])
        for table, rows in state['children'].items():
            if table not in allowed:
                raise ValueError('Unbekannte Rechnungskindtabelle im gespeicherten Befund: {0}'.format(table))
            for row in rows:
                if not row.get('name') or row.get('parent') != old or row.get('parenttype') != 'Sales Invoice':
                    raise ValueError('Ungültige Kind-Zielzeile im gespeicherten Befund: {0}'.format(old))
                targets.setdefault(table, []).append(row['name'])
        customers = set(row.get('party') for row in state['gl']
            if row.get('party_type') == 'Customer' and row.get('party'))
        results.append({'rechnung': old, 'ersatz': replacements[old], 'status': 'bereit',
            'kunde': next(iter(customers)) if len(customers) == 1 else None,
            'hauptbuchzeilen': len(state['gl']),
            'kindzeilen': sum(len(rows) for rows in state['children'].values())})
    result = {'dry_run': dry_run, 'datenbasis': 'gespeicherter_pruefbefund',
        'status': 'bereit', 'anz_ausgewaehlt': len(results), 'faelle': results}
    if dry_run:
        return result

    backup = None
    try:
        backup = _write_private('bereinigung_verwaiste_rechnungen', {
            'site': frappe.local.site, 'zeitpunkt': now(), 'benutzer': frappe.session.user,
            'datenbasis': 'gespeicherter_pruefbefund_ohne_erneute_db_pruefung',
            'faelle': list(cases.values()), 'ersatzzuordnungen': replacements,
            'freigabe_pruefsummen': approval_fingerprints
        })
        owners = tuple(sorted(cases))
        owner_slots = ', '.join(['%s'] * len(owners))
        for table, names in targets.items():
            names = sorted(set(names))
            for offset in range(0, len(names), BATCH_SIZE):
                batch = tuple(names[offset:offset + BATCH_SIZE])
                slots = ', '.join(['%s'] * len(batch))
                if table == 'GL Entry':
                    query = '''DELETE FROM `tabGL Entry` WHERE voucher_type = 'Sales Invoice'
                        AND voucher_no IN ({0}) AND name IN ({1})'''.format(owner_slots, slots)
                else:
                    query = '''DELETE FROM `tab{0}` WHERE parenttype = 'Sales Invoice'
                        AND parent IN ({1}) AND name IN ({2})'''.format(table, owner_slots, slots)
                frappe.db.sql(query, owners + batch)
                # Das Ergebnis der Schreiboperation prüfen, ohne erneut Daten zu lesen.
                if frappe.db._cursor.rowcount != len(batch):
                    raise ValueError('In {0} wurden {1} statt {2} gespeicherte Zielzeilen gelöscht. '
                        'Der Stapel wird zurückgerollt.'.format(table, frappe.db._cursor.rowcount, len(batch)))
        _saved_comments(results, backup)
        if commit:
            frappe.db.commit()
        for row in results:
            row['status'] = 'bereinigt'
        result.update(status='bereinigt', sicherung=backup)
        return result
    except Exception:
        frappe.db.rollback()
        if backup:
            print('DB-Änderungen zurückgerollt. Gespeicherter Prüfbefund gesichert: {0}'.format(backup))
        raise


def _saved_comments(rows, backup):
    # Info-Kommentare benötigen keinen _comments-Cache am Rechnungsdokument.
    # Direkt gesammelt schreiben, ohne dafür alle Ersatzrechnungen zu laden.
    columns = ('name', 'creation', 'modified', 'modified_by', 'owner', 'docstatus',
        'comment_type', 'comment_email', 'reference_doctype', 'reference_name', 'content')
    timestamp, user = now(), frappe.session.user
    values = []
    for row in rows:
        if row['ersatz']:
            marker = MARKER.format(row['rechnung'], row['ersatz'])
            reference_doctype, reference_name = 'Sales Invoice', row['ersatz']
        else:
            marker = 'Bereinigung verwaiste Rechnung {0}: manuell freigegeben, ohne Ersatzrechnung.'.format(row['rechnung'])
            reference_doctype = 'Customer' if row['kunde'] else 'Sales Invoice'
            reference_name = row['kunde'] or row['rechnung']
        content = ('{0} Gemäss freigegebenem Prüfbefund ohne erneute Datenprüfung entfernt: '
            '{1} Hauptbuchzeilen, {2} Kindzeilen. Sicherung des Prüfbefunds: {3}').format(
                marker, row['hauptbuchzeilen'],
                row['kindzeilen'], os.path.basename(backup))
        values.extend((frappe.generate_hash(length=10), timestamp, timestamp, user, user, 0,
            'Info', user, reference_doctype, reference_name, content))
    placeholders = '(' + ', '.join(['%s'] * len(columns)) + ')'
    frappe.db.sql('INSERT INTO `tabComment` ({0}) VALUES {1}'.format(
        ', '.join('`{0}`'.format(column) for column in columns),
        ', '.join([placeholders] * len(rows))), tuple(values))


def replacement_fingerprint(plan):
    """Bindet eine UI-Freigabe an die tatsächlich geprüfte Ersatzrechnung."""
    return fingerprint({'header': plan['replacement'], 'gl': plan['replacement_gl'],
        'children': plan['replacement_children']})


def prepare_review_context(names):
    """Lesedaten für eine ganze Freigabeauswahl; keine Abfrage pro Ersatzrechnung."""
    names = sorted(set(names))
    context = {'states': read_snapshots(names), 'headers': {}, 'comments': {}, 'currencies': {}}
    for offset in range(0, len(names), BATCH_SIZE):
        batch = tuple(names[offset:offset + BATCH_SIZE])
        slots = ', '.join(['%s'] * len(batch))
        for row in frappe.db.sql('SELECT * FROM `tabSales Invoice` WHERE name IN ({0})'.format(
                slots), batch, as_dict=True):
            context['headers'][row['name']] = row
        for row in frappe.db.sql('''SELECT reference_name, content FROM `tabComment`
                WHERE reference_doctype = 'Sales Invoice' AND comment_type = 'Info'
                AND reference_name IN ({0}) AND content LIKE %s'''.format(slots),
                batch + ('Bereinigung verwaiste Rechnung %',), as_dict=True):
            context['comments'].setdefault(row['reference_name'], []).append(row['content'])
    companies = sorted(set(row['company'] for state in context['states'].values() for row in state['gl']))
    if companies:
        for row in frappe.db.sql('SELECT name, default_currency FROM `tabCompany` WHERE name IN ({0})'.format(
                ', '.join(['%s'] * len(companies))), tuple(companies), as_dict=True):
            context['currencies'][row['name']] = row['default_currency']
    return context


def _prepare(case, new, state, lock=False, context=None):
    if context is not None and lock:
        raise ValueError('Gebündelte Lesedaten dürfen nur für die Vorschau/Freigabe verwendet werden.')
    old = case['rechnung']
    if (context['headers'].get(old) if context is not None else _header(old, lock)):
        raise ValueError('Der ursprüngliche Rechnungskopf existiert wieder.')
    replacement = context['headers'].get(new) if context is not None else _header(new, lock)
    if not replacement:
        raise ValueError('Die Ersatzrechnung fehlt.')
    if context is not None:
        marker = any(content.startswith(MARKER.format(old, new)) for content in context['comments'].get(new, []))
    else:
        marker = frappe.db.exists('Comment', {'reference_doctype': 'Sales Invoice',
            'reference_name': new, 'comment_type': 'Info', 'content': ['like', MARKER.format(old, new) + '%']})
    if marker and _empty(state) and not state['references']:
        return {'result': {'status': 'bereits_bereinigt'}}
    if marker:
        raise ValueError('Bereinigungsvermerk vorhanden, aber weiterhin Restdaten.')
    if fingerprint(state) != case['fingerprint']:
        raise ValueError('Originalzeilen oder Bezüge haben sich seit der Prüfung geändert. Neu prüfen.')
    if state['references']:
        raise ValueError('Fremdbezüge vorhanden: {0}'.format(state['references']))
    gl = state['gl']
    companies = set(row['company'] for row in gl)
    if companies != {case['company']} or not gl:
        raise ValueError('Der Buchungssatz fehlt oder betrifft mehrere Firmen.')
    currency = context['currencies'].get(case['company']) if context is not None else frappe.db.get_value(
        'Company', case['company'], 'default_currency')
    if not currency or any(row['account_currency'] != currency for row in gl):
        raise ValueError('Fremdwährungsfälle benötigen eine separate Prüfung.')
    parties = [row for row in gl if row.get('party') or row.get('party_type')]
    if len(parties) != 1 or parties[0]['party_type'] != 'Customer' or not parties[0].get('party'):
        raise ValueError('Es muss genau eine eindeutige Kundenbuchung vorhanden sein.')
    party = parties[0]
    amount = flt(party['debit']) - flt(party['credit'])
    if amount <= 0 or flt(party['credit']) or not _equal(sum(flt(row['debit']) - flt(row['credit'])
            for row in gl), 0):
        raise ValueError('Keine positive Kundenforderung oder unausgeglichener Buchungssatz.')
    for row in gl:
        if (row['voucher_type'] != 'Sales Invoice' or row['voucher_no'] != old
                or not _equal(row['debit'], row['debit_in_account_currency'])
                or not _equal(row['credit'], row['credit_in_account_currency'])
                or flt(row['debit']) < 0 or flt(row['credit']) < 0):
            raise ValueError('Unerwartete Beträge oder Belegzuordnungen im Hauptbuch.')
        if row.get('against_voucher') and (row.get('against_voucher_type') != 'Sales Invoice'
                or row['against_voucher'] != old):
            raise ValueError('Der Buchungssatz verweist auf einen anderen Beleg.')
    if (replacement['docstatus'] != 1 or replacement['customer'] != party['party']
            or replacement['company'] != case['company'] or replacement['currency'] != currency
            or any(flt(replacement.get(field)) for field in (
                'is_return', 'is_pos', 'update_stock', 'paid_amount', 'total_advance', 'write_off_amount'))):
        raise ValueError('Ersatzrechnung hat einen anderen Kunden/Firma/Währung oder ist ein Sonderfall.')
    if not _equal(replacement.get('rounded_total') or replacement.get('grand_total'), amount):
        raise ValueError('Der Rechnungsbetrag der Ersatzrechnung stimmt nicht mit der Forderung überein.')
    new_state = context['states'][new] if context is not None else read_snapshots([new], lock=lock)[new]
    if _gl_signature(gl, old) != _gl_signature(new_state['gl'], new):
        raise ValueError('Der Hauptbuch-Buchungssatz der Ersatzrechnung stimmt nicht überein.')
    if not state['children'].get('Sales Invoice Item') or _item_signature(state) != _item_signature(new_state):
        raise ValueError('Artikel, Mengen oder Beträge der Ersatzrechnung stimmen nicht überein.')
    return {'old': old, 'new': new, 'state': state, 'replacement': replacement,
        'replacement_gl': new_state['gl'], 'replacement_children': new_state['children'],
        'company': case['company'], 'customer': party['party'], 'currency': currency, 'amount': amount,
        'result': {'status': 'bereit', 'kunde': party['party'], 'firma': case['company'],
            'waehrung': currency, 'entfernte_kundenbelastung': amount}}


def _gl_signature(rows, invoice):
    fields = ('company', 'posting_date', 'account', 'account_currency', 'party_type', 'party',
        'cost_center', 'project', 'is_opening', 'finance_book')
    signatures = []
    for row in rows:
        values = [str(row.get(field) or '') for field in fields]
        values += [flt(row.get(field), 6) for field in (
            'debit', 'credit', 'debit_in_account_currency', 'credit_in_account_currency')]
        values += [row.get('against_voucher_type') or '',
            'SELF' if row.get('against_voucher') == invoice else row.get('against_voucher') or '']
        signatures.append(values)
    return sorted(signatures)


def _item_signature(state):
    return sorted([(row.get('item_code') or '',) + tuple(flt(row.get(field), 6)
        for field in ('qty', 'rate', 'amount', 'base_amount'))
        for row in state['children'].get('Sales Invoice Item', [])])


def _unchanged_replacement(plan):
    if _header(plan['new'], lock=True) != plan['replacement']:
        raise ValueError('Die Ersatzrechnung wurde zwischenzeitlich geändert.')
    state = read_snapshots([plan['new']], lock=True)[plan['new']]
    if state['gl'] != plan['replacement_gl'] or state['children'] != plan['replacement_children']:
        raise ValueError('Buchungen oder Positionen der Ersatzrechnung wurden verändert.')


def _header(invoice, lock=False):
    rows = frappe.db.sql('SELECT * FROM `tabSales Invoice` WHERE name = %s' + (
        ' FOR UPDATE' if lock else ''), (invoice,), as_dict=True)
    return rows[0] if rows else None


def _empty(state):
    return not state['gl'] and not any(state['children'].values())


def _balance_key(plan):
    return json.dumps([plan['company'], plan['customer']], ensure_ascii=False)


def _balances(plans):
    balances = {}
    for plan in plans:
        key = _balance_key(plan)
        if key not in balances:
            balances[key] = flt(frappe.db.sql('''
                SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0)
                FROM `tabGL Entry` WHERE party_type = 'Customer' AND party = %s AND company = %s
            ''', (plan['customer'], plan['company']))[0][0], 6)
    return balances


def _equal(left, right):
    return abs(flt(left) - flt(right)) < 0.000001


def _load_report(report):
    if isinstance(report, str):
        root = os.path.realpath(frappe.get_site_path('private'))
        # Ein Dateiname ist relativ zu private; get_site_path kann dagegen
        # bereits einen vollständigen, aber arbeitsverzeichnisrelativen Pfad liefern.
        path = os.path.realpath(os.path.join(root, report) if os.path.basename(report) == report else report)
        if os.path.dirname(path) != root or not os.path.basename(path).startswith('pruefung_verwaiste_rechnungen_'):
            raise ValueError('Nur Prüfberichte im private-Verzeichnis dieser Site sind zulässig.')
        with open(path, encoding='utf-8') as source:
            report = json.load(source)
    if (not isinstance(report, dict) or report.get('report_version') != REPORT_VERSION
            or report.get('site') != frappe.local.site or not isinstance(report.get('faelle'), list)):
        raise ValueError('Kein passender gespeicherter Prüfbericht dieser Site.')
    return report


def _write_private(prefix, data):
    path = os.path.realpath(frappe.get_site_path('private', '{0}_{1}.json'.format(
        prefix, frappe.generate_hash(length=12))))
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
        output.write(frappe.as_json(data))
    return path
