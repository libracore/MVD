# -*- coding: utf-8 -*-
"""Rein lesende Suche nach Sales-Invoice-Buchungen ohne Rechnungskopf.

Alle Firmen, Zusammenfassung:
    bench --site SITE execute mvd.mvd.data_import.pruefe_verwaiste_rechnungen.run

Einzelfälle mit Positionen und Zahlungsbezügen:
    bench --site SITE execute mvd.mvd.data_import.pruefe_verwaiste_rechnungen.run --kwargs "{'details': True}"

Optional company auf den exakten Firmennamen einschränken. Keine DB-Änderungen,
kein Commit. Mit save_report=True wird die Detailprüfung mit Originalzeilen
privat als JSON gespeichert und kann an bereinige_verwaiste_rechnungen.run
übergeben werden. Ohne diese Option werden keine Dateien geschrieben.
Die Treffer sind Dateninkonsistenzen, aber kein
Nachweis für Doppelrechnungen oder automatisch entfernbare Buchungen.

Prüfumfang: eigene Sales-Invoice-Hauptbuchzeilen ohne zugehörige Rechnung.
Reine Positionsreste ohne Hauptbuch und Fehler bei vorhandenen Rechnungsköpfen
sind nicht Bestandteil dieser Prüfung. Keine Datums-/Statuseinschränkung.
"""
from __future__ import unicode_literals

import frappe
from frappe.utils import cint, flt


BATCH_SIZE = 200


def run(company=None, details=False, save_report=False):
    save_report = bool(cint(save_report))
    details = bool(cint(details)) or save_report
    condition = ' AND gl.company = %s' if company else ''
    values = (company,) if company else ()
    # Nicht nach Saldo filtern: vollständige Doppelbuchungen sind ausgeglichen.
    cases = frappe.db.sql('''
        SELECT gl.company, gl.voucher_no AS rechnung,
            c.default_currency AS basiswaehrung,
            MIN(gl.posting_date) AS buchungsdatum_von,
            MAX(gl.posting_date) AS buchungsdatum_bis,
            COUNT(*) AS hauptbuchzeilen,
            SUM(gl.debit) AS soll_basiswaehrung,
            SUM(gl.credit) AS haben_basiswaehrung
        FROM `tabGL Entry` gl
        LEFT JOIN `tabSales Invoice` si ON si.name = gl.voucher_no
        LEFT JOIN `tabCompany` c ON c.name = gl.company
        WHERE gl.voucher_type = 'Sales Invoice' AND si.name IS NULL
    ''' + condition + '''
        GROUP BY gl.company, gl.voucher_no, c.default_currency
        ORDER BY gl.company, gl.voucher_no
    ''', values, as_dict=True)

    result = {'nur_lesend': True, 'firma_filter': company,
        'anz_faelle': len(cases), 'firmen': [],
        'hinweis': 'Fehlender Rechnungskopf ist bestätigt; Ersatz und Berechtigung der Forderung pro Fall prüfen.'}
    if not cases:
        if details:
            result['faelle'] = []
        if save_report:
            _save_report(result)
        return result

    customers = frappe.db.sql('''
        SELECT gl.company, gl.voucher_no AS rechnung, gl.party AS kunde,
            gl.account_currency AS kontowaehrung,
            SUM(gl.debit_in_account_currency) - SUM(gl.credit_in_account_currency)
                AS saldoanteil_kontowaehrung,
            SUM(gl.debit) - SUM(gl.credit) AS saldoanteil_basiswaehrung
        FROM `tabGL Entry` gl
        LEFT JOIN `tabSales Invoice` si ON si.name = gl.voucher_no
        WHERE gl.voucher_type = 'Sales Invoice' AND si.name IS NULL
            AND gl.party_type = 'Customer'
    ''' + condition + '''
        GROUP BY gl.company, gl.voucher_no, gl.party, gl.account_currency
        ORDER BY gl.company, gl.voucher_no, gl.party, gl.account_currency
    ''', values, as_dict=True)

    by_case = {(row.company, row.rechnung): row for row in cases}
    for row in cases:
        row['kunden'] = []
        row['buchung_ausgeglichen'] = abs(flt(row.soll_basiswaehrung)
            - flt(row.haben_basiswaehrung)) < 0.000001
    for row in customers:
        by_case[(row.company, row.rechnung)]['kunden'].append(row)

    summaries = {}
    for row in cases:
        summary = summaries.setdefault(row.company, {
            'firma': row.company, 'basiswaehrung': row.basiswaehrung,
            'anz_faelle': 0, 'anz_ohne_kundenzuordnung': 0,
            'anz_unbalancierte_buchungen': 0, 'kunden_saldoanteil_basiswaehrung': 0
        })
        summary['anz_faelle'] += 1
        summary['anz_ohne_kundenzuordnung'] += int(not row.kunden)
        summary['anz_unbalancierte_buchungen'] += int(not row.buchung_ausgeglichen)
        summary['kunden_saldoanteil_basiswaehrung'] += sum(
            flt(customer.saldoanteil_basiswaehrung) for customer in row.kunden)
    for name in sorted(summaries):
        summary = summaries[name]
        summary['kunden_saldoanteil_basiswaehrung'] = flt(
            summary['kunden_saldoanteil_basiswaehrung'], 6)
        result['firmen'].append(summary)

    if details:
        # Gebündelte Abfragen statt einzelner DB-Aufrufe pro Rechnung.
        names = sorted(set(row.rechnung for row in cases if row.rechnung))
        extra = {}
        for offset in range(0, len(names), BATCH_SIZE):
            _read_details(names[offset:offset + BATCH_SIZE], extra)
        for row in cases:
            info = extra.get(row.rechnung, {})
            row['positionen'] = info.get('positionen', [])
            # Bezüge können auch aus anderen Firmen/Kunden stammen.
            row['fremde_hauptbuchbezuege'] = info.get('gl_bezuege', [])
            row['zahlungszuordnungen'] = info.get('zuordnungen', [])
        result['faelle'] = cases
    if save_report:
        _save_report(result)
    return result


def _save_report(result):
    from mvd.mvd.data_import.bereinige_verwaiste_rechnungen import save_report
    result['report'] = save_report(result)


def _read_details(names, extra):
    placeholders = ', '.join(['%s'] * len(names))
    values = tuple(names)
    items = frappe.db.sql('''
        SELECT parent AS rechnung, item_code, item_name, COUNT(*) AS positionen,
            SUM(qty) AS menge, SUM(amount) AS betrag, SUM(base_amount) AS basisbetrag
        FROM `tabSales Invoice Item`
        WHERE parenttype = 'Sales Invoice' AND parent IN ({0})
        GROUP BY parent, item_code, item_name
        ORDER BY parent, item_code, item_name
    '''.format(placeholders), values, as_dict=True)
    references = frappe.db.sql('''
        SELECT against_voucher AS rechnung, company, voucher_type, voucher_no,
            party_type, party, account_currency AS kontowaehrung,
            SUM(debit) - SUM(credit) AS saldo_basiswaehrung,
            SUM(debit_in_account_currency) - SUM(credit_in_account_currency)
                AS saldo_kontowaehrung
        FROM `tabGL Entry`
        WHERE against_voucher_type = 'Sales Invoice' AND against_voucher IN ({0})
            AND NOT (voucher_type = 'Sales Invoice' AND voucher_no = against_voucher)
        GROUP BY against_voucher, company, voucher_type, voucher_no,
            party_type, party, account_currency
        ORDER BY against_voucher, company, voucher_type, voucher_no
    '''.format(placeholders), values, as_dict=True)
    allocations = frappe.db.sql('''
        SELECT reference_name AS rechnung, 'Payment Entry' AS doctype,
            parent AS beleg, docstatus, COUNT(*) AS zuordnungen
        FROM `tabPayment Entry Reference`
        WHERE reference_doctype = 'Sales Invoice' AND reference_name IN ({0})
        GROUP BY reference_name, parent, docstatus
        UNION ALL
        SELECT reference_name AS rechnung, 'Journal Entry' AS doctype,
            parent AS beleg, docstatus, COUNT(*) AS zuordnungen
        FROM `tabJournal Entry Account`
        WHERE reference_type = 'Sales Invoice' AND reference_name IN ({0})
        GROUP BY reference_name, parent, docstatus
        ORDER BY rechnung, doctype, beleg, docstatus
    '''.format(placeholders), values * 2, as_dict=True)
    for key, rows in (('positionen', items), ('gl_bezuege', references),
            ('zuordnungen', allocations)):
        for row in rows:
            extra.setdefault(row.rechnung, {}).setdefault(key, []).append(row)
