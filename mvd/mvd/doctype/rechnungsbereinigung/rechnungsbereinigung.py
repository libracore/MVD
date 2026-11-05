# -*- coding: utf-8 -*-
"""Frappe-Desk-Prüfläufe für verwaiste Rechnungen; keine automatische Freigabe."""
from __future__ import unicode_literals

import hashlib
import json
import os

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, now
from frappe.utils.background_jobs import enqueue

from mvd.mvd.data_import import bereinige_verwaiste_rechnungen as core


RUN = 'Rechnungsbereinigung'
CASE = 'Rechnungsbereinigung Fall'
BUSY = ('Wartet auf Prüfung', 'Prüfung läuft', 'Wartet auf Bereinigung', 'Bereinigung läuft')
BATCH_SIZE = 25
REVIEW_BATCH_SIZE = 100
REVIEW_SELECTION_LIMIT = 5000
METHOD = 'mvd.mvd.doctype.rechnungsbereinigung.rechnungsbereinigung.'
INTERNAL = object()


class Rechnungsbereinigung(Document):
    def validate(self):
        if self.flags.get('interne_bereinigung') is INTERNAL:
            return
        previous = self.get_doc_before_save()
        if self.is_new():
            if self.status not in (None, '', 'Neu') or self.report or self.job_token:
                frappe.throw('Neue Prüfläufe müssen den Status Neu besitzen.')
            self.status = 'Neu'
        elif previous:
            _protect_fields(self, previous, ('company',))
            current = frappe.db.sql('SELECT modified FROM `tabRechnungsbereinigung` '
                'WHERE name = %s FOR UPDATE', (self.name,))
            if current and not _same_value(current[0][0], previous.modified):
                frappe.throw('Der Prüflauf wurde inzwischen geändert. Bitte neu laden.')
            if self.company != previous.company and previous.status != 'Neu':
                frappe.throw('Die Firma eines gestarteten Prüflaufs kann nicht geändert werden.')


def _authorize(write=False):
    # v12 unterstützt noch kein whitelist(methods=['POST']).
    if 'System Manager' not in frappe.get_roles():
        raise frappe.PermissionError('Nur System Manager dürfen Rechnungsbereinigungen bearbeiten.')
    request = getattr(frappe.local, 'request', None)
    if write and request and request.method != 'POST':
        raise frappe.PermissionError('Diese Aktion benötigt einen POST-Aufruf.')


def _protect_fields(doc, previous, editable):
    for field in doc.meta.get_valid_columns():
        if field not in tuple(editable) + ('modified', 'modified_by', '_user_tags', '_comments',
                '_assign', '_liked_by', '_seen') and not _same_value(doc.get(field), previous.get(field)):
            frappe.throw('Das Feld {0} wird ausschliesslich durch die Prüfung gesetzt.'.format(field))


def _same_value(left, right):
    return left == right or (left in (None, '') and right in (None, '')) or (
        frappe.as_json(left) == frappe.as_json(right))


def _save(doc, **values):
    doc.flags.interne_bereinigung = INTERNAL
    doc.update(values)
    doc.save(ignore_permissions=True)


def _run(name, lock=False):
    if lock:
        frappe.db.sql('SELECT name FROM `tabRechnungsbereinigung` WHERE name = %s FOR UPDATE', (name,))
    return frappe.get_doc(RUN, name)


def _case_rows(names, lock=False, limit=100):
    if isinstance(names, str):
        names = json.loads(names)
    if not isinstance(names, list) or not names or len(names) > limit or any(
            not isinstance(name, str) for name in names):
        frappe.throw('Bitte 1 bis {0} Fälle desselben Prüflaufs auswählen.'.format(limit))
    names = sorted(set(names))
    rows = frappe.get_all(CASE, filters={'name': ['in', names]},
        fields=['name', 'prueflauf', 'alte_rechnung', 'ersatzrechnung', 'status', 'modified'], order_by='name')
    if len(rows) != len(names) or len(set(row.prueflauf for row in rows)) != 1:
        frappe.throw('Die Auswahl muss aus vorhandenen Fällen desselben Prüflaufs bestehen.')
    run = _run(rows[0].prueflauf, lock=lock)
    if run.status in BUSY:
        frappe.throw('Dieser Prüflauf wird gerade verarbeitet. Bitte warten.')
    if lock:
        frappe.db.sql('SELECT name FROM `tabRechnungsbereinigung Fall` WHERE name IN ({0}) '
            'ORDER BY name FOR UPDATE'.format(', '.join(['%s'] * len(names))), tuple(names))
    return run, rows


def _case_docs(names, lock=False):
    run, rows = _case_rows(names, lock=lock)
    return run, [frappe.get_doc(CASE, row.name) for row in rows]


def _report(run):
    report = core._load_report(run.report)
    cases = {}
    for row in report['faelle']:
        # Mehrfirmenfälle blockiert _prepare anhand des vollständigen Buchungssatzes.
        # Sie dürfen die Sichtung anderer Rechnungen desselben Berichts nicht verhindern.
        cases.setdefault(row['rechnung'], row)
    return report, cases


def _clear_approval():
    return {'freigegeben_von': None, 'freigegeben_am': None, 'freigegebener_ersatz': None,
        'ersatz_fingerprint': None}


def _counts(run, **updates):
    rows = frappe.db.sql('''SELECT status, COUNT(*) AS anzahl
        FROM `tabRechnungsbereinigung Fall` WHERE prueflauf = %s GROUP BY status''', (run.name,), as_dict=True)
    counts = {row.status: row.anzahl for row in rows}
    values = {'anzahl': sum(counts.values()), 'freigegeben': counts.get('Freigegeben', 0),
        'bereinigt': counts.get('Bereinigt', 0), 'blockiert': counts.get('Blockiert', 0),
        'offen': counts.get('Offen', 0) + counts.get('Prüfbar', 0),
        'zurueckgestellt': counts.get('Zurückgestellt', 0)}
    values.update(updates)
    _save(run, **values)


@frappe.whitelist()
def start_scan(name):
    _authorize(write=True)
    run = _run(name, lock=True)
    if run.status != 'Neu':
        frappe.throw('Für eine neue Prüfung bitte einen neuen Prüflauf erstellen.')
    token = frappe.generate_hash(length=20)
    _save(run, status='Wartet auf Prüfung', job_token=token, gestartet_von=frappe.session.user,
        gestartet_am=now(), fehler=None)
    enqueue(METHOD + 'scan_worker', queue='long', timeout=7200, enqueue_after_commit=True,
        name=name, token=token)
    return {'status': run.status}


def scan_worker(name, token):
    _authorize()
    run = _run(name, lock=True)
    if run.job_token != token or run.status != 'Wartet auf Prüfung':
        return
    _save(run, status='Prüfung läuft')
    frappe.db.commit()
    try:
        from mvd.mvd.data_import.pruefe_verwaiste_rechnungen import run as scan
        result = scan(company=run.company or None, save_report=True)
        report = core._load_report(result['report'])
        suggestions = _suggestions([row['rechnung'] for row in report['faelle']])
        for row in report['faelle']:
            customers = row.get('kunden') or []
            customer = customers[0].get('kunde') if len(customers) == 1 else None
            candidates = suggestions.get(row['rechnung'], [])
            document = frappe.get_doc({
                'doctype': CASE,
                'name': 'RBF-' + hashlib.sha256((name + '\n' + row['company'] + '\n' + row['rechnung']).encode('utf-8')).hexdigest()[:24],
                'prueflauf': name, 'company': row['company'], 'alte_rechnung': row['rechnung'],
                'kunde': customer, 'waehrung': row.get('basiswaehrung'),
                'betrag': sum(flt(item.get('saldoanteil_basiswaehrung')) for item in customers),
                'buchungsdatum': row.get('buchungsdatum_von'), 'status': 'Offen',
                'ersatzrechnung': candidates[0] if len(candidates) == 1 else None,
                'anz_kandidaten': len(candidates), 'kandidaten': json.dumps(candidates),
                'pruefhinweis': 'Vorschlag anhand Kunde, Firma, Datum und Betrag; fachlich prüfen.',
                'owner': frappe.session.user
            })
            # Reine Prüfdaten; ein INSERT pro Fall statt Rechnungs-/Mitgliedschafts-Hooks.
            document.db_insert()
        _save(run, report=os.path.basename(result['report']), status='Bereit', beendet_am=now())
        _counts(run)
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        run = _run(name, lock=True)
        _save(run, status='Fehler', fehler=frappe.get_traceback(), beendet_am=now())
        frappe.db.commit()
        raise


def _suggestions(names):
    result = {}
    names = sorted(set(names))
    for offset in range(0, len(names), 200):
        batch = tuple(names[offset:offset + 200])
        if not batch:
            continue
        rows = frappe.db.sql('''SELECT DISTINCT gl.voucher_no AS alte_rechnung, si.name
            FROM `tabGL Entry` gl INNER JOIN `tabSales Invoice` si
              ON si.customer = gl.party AND si.company = gl.company AND si.posting_date = gl.posting_date
              AND si.docstatus = 1 AND si.is_return = 0
              AND COALESCE(NULLIF(si.rounded_total, 0), si.grand_total) = gl.debit - gl.credit
            WHERE gl.voucher_type = 'Sales Invoice' AND gl.party_type = 'Customer'
              AND gl.voucher_no IN ({0}) ORDER BY gl.voucher_no, si.name'''.format(
                ', '.join(['%s'] * len(batch))), batch, as_dict=True)
        for row in rows:
            result.setdefault(row.alte_rechnung, []).append(row.name)
    return result


@frappe.whitelist()
def review_cases(names, approve=False, confirmed=False, background=False):
    _authorize(write=True)
    approve = bool(cint(approve))
    if approve and not cint(confirmed):
        frappe.throw('Die Freigabe zur Bereinigung muss ausdrücklich bestätigt werden.')
    if cint(background):
        return _queue_review(names, approve)
    run, docs = _case_docs(names, lock=True)
    report, cases = _report(run)
    result = _review_docs(docs, cases, approve)
    _counts(run)
    return result


def _review_docs(docs, cases, approve, expected=None):
    active = [doc for doc in docs if doc.status != 'Bereinigt']
    names = [doc.alte_rechnung for doc in active] + [doc.ersatzrechnung for doc in active if doc.ersatzrechnung]
    context = core.prepare_review_context(names) if not approve else None
    result = []
    for doc in docs:
        if doc.status == 'Bereinigt':
            continue
        values = _clear_approval()
        try:
            if expected is not None:
                selection = expected.get(doc.name)
                if (not selection or not _same_value(doc.ersatzrechnung, selection['ersatzrechnung'])
                        or not _same_value(doc.modified, selection['modified'])):
                    raise ValueError('Der Fall wurde seit der Auswahl geändert. Bitte erneut prüfen und freigeben.')
            if approve:
                values.update(status='Freigegeben', freigegeben_von=frappe.session.user, freigegeben_am=now(),
                    freigegebener_ersatz=doc.ersatzrechnung or None,
                    ersatz_fingerprint=cases[doc.alte_rechnung]['fingerprint'],
                    pruefhinweis='Manuell zur Bereinigung gemäss gespeichertem Prüfbefund freigegeben.')
            else:
                if not doc.ersatzrechnung:
                    raise ValueError('Kein Ersatzvergleich möglich. Der Fall kann trotzdem manuell freigegeben werden.')
                plan = core._prepare(cases[doc.alte_rechnung], doc.ersatzrechnung,
                    context['states'][doc.alte_rechnung], context=context)
                if plan['result']['status'] == 'bereits_bereinigt':
                    values.update(status='Bereinigt', pruefhinweis='Bereits durch die Bereinigungslogik erledigt.')
                else:
                    values.update(status='Prüfbar', pruefhinweis='Buchungssatz und Positionen stimmen überein.')
        except (ValueError, KeyError) as error:
            values.update(status='Blockiert', pruefhinweis=str(error))
        _save(doc, **values)
        result.append({'name': doc.name, 'status': doc.status, 'hinweis': doc.pruefhinweis})
    return result


def _queue_review(names, approve):
    # Nur eine gebündelte Fallabfrage; hier noch keine fachlichen Prüfungen oder Freigaben.
    run, rows = _case_rows(names, lock=True, limit=REVIEW_SELECTION_LIMIT)
    if run.status not in ('Bereit', 'Fehler') or not run.report:
        frappe.throw('Der Prüflauf ist nicht bereit.')
    selection = {'art': 'freigabe' if approve else 'pruefung', 'benutzer': frappe.session.user,
        'faelle': [{key: row.get(key) for key in ('name', 'ersatzrechnung', 'modified')} for row in rows]}
    token = frappe.generate_hash(length=20)
    _save(run, status='Wartet auf Prüfung', job_token=token, verarbeitet=0, fehler=None,
        job_auswahl=frappe.as_json(selection))
    enqueue(METHOD + 'review_worker', queue='long', timeout=7200, enqueue_after_commit=True,
        name=run.name, token=token)
    return {'queued': True, 'anzahl': len(rows), 'prueflauf': run.name}


def review_worker(name, token):
    _authorize()
    run = _run(name, lock=True)
    if run.job_token != token or run.status != 'Wartet auf Prüfung':
        return
    try:
        selection = json.loads(run.job_auswahl)
        if selection.get('art') not in ('freigabe', 'pruefung') or selection.get('benutzer') != frappe.session.user:
            frappe.throw('Der Prüf-/Freigabeauftrag ist nicht gültig.')
        _save(run, status='Prüfung läuft')
        frappe.db.commit()
        unused, cases = _report(run)  # Grosse JSON-Datei nur einmal je Auftrag laden.
        rows = selection['faelle']
        for offset in range(0, len(rows), REVIEW_BATCH_SIZE):
            batch = rows[offset:offset + REVIEW_BATCH_SIZE]
            run = _run(name, lock=True)
            if run.job_token != token or run.status != 'Prüfung läuft':
                frappe.throw('Der Prüf-/Freigabeauftrag ist nicht mehr gültig.')
            names = [row['name'] for row in batch]
            frappe.db.sql('SELECT name FROM `tabRechnungsbereinigung Fall` WHERE name IN ({0}) '
                'ORDER BY name FOR UPDATE'.format(', '.join(['%s'] * len(names))), tuple(names))
            data = frappe.get_all(CASE, filters={'name': ['in', names], 'prueflauf': name},
                fields=['*'], order_by='name')
            if len(data) != len(names):
                frappe.throw('Ein ausgewählter Fall fehlt oder gehört zu einem anderen Prüflauf.')
            # Aus gebündelt geladenen Zeilen erzeugen, statt pro Fall erneut zu laden.
            docs = [frappe.get_doc(dict(row, doctype=CASE)) for row in data]
            _review_docs(docs, cases, selection['art'] == 'freigabe',
                expected={row['name']: row for row in batch})
            _counts(run, verarbeitet=cint(run.verarbeitet) + len(batch))
            frappe.db.commit()
        run = _run(name, lock=True)
        _counts(run, status='Bereit', beendet_am=now())
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        run = _run(name, lock=True)
        _save(run, status='Fehler', fehler=frappe.get_traceback(), beendet_am=now())
        frappe.db.commit()
        raise


@frappe.whitelist()
def defer_cases(names):
    _authorize(write=True)
    run, docs = _case_docs(names, lock=True)
    for doc in docs:
        if doc.status != 'Bereinigt':
            values = _clear_approval()
            values.update(status='Zurückgestellt')
            _save(doc, **values)
    _counts(run)


@frappe.whitelist()
def start_cleanup(name, names=None, confirmed=False):
    _authorize(write=True)
    if not cint(confirmed):
        frappe.throw('Die Bereinigung muss ausdrücklich bestätigt werden.')
    run = _run(name, lock=True)
    if run.status not in ('Bereit', 'Fehler') or not run.report:
        frappe.throw('Der Prüflauf ist nicht bereit.')
    if names:
        selected_run, docs = _case_docs(names, lock=True)
        if selected_run.name != name or any(doc.status != 'Freigegeben' for doc in docs):
            frappe.throw('Bitte ausschliesslich freigegebene Fälle dieses Prüflaufs auswählen.')
        selected = [doc.name for doc in docs]
    else:
        selected = [row.name for row in frappe.get_all(CASE,
            filters={'prueflauf': name, 'status': 'Freigegeben'}, fields=['name'], order_by='name')]
    if not selected:
        frappe.throw('Es sind keine freigegebenen Fälle vorhanden.')
    token = frappe.generate_hash(length=20)
    _save(run, status='Wartet auf Bereinigung', job_token=token,
        job_auswahl=json.dumps(selected), verarbeitet=0, fehler=None)
    enqueue(METHOD + 'cleanup_worker', queue='long', timeout=7200, enqueue_after_commit=True,
        name=name, token=token)
    return {'anzahl': len(selected)}


def cleanup_worker(name, token):
    _authorize()
    run = _run(name, lock=True)
    if run.job_token != token or run.status != 'Wartet auf Bereinigung':
        return
    _save(run, status='Bereinigung läuft')
    frappe.db.commit()
    try:
        report, unused = _report(run)
        names = json.loads(run.job_auswahl)
        for offset in range(0, len(names), BATCH_SIZE):
            _cleanup_batch(name, token, names[offset:offset + BATCH_SIZE], report)
        run = _run(name, lock=True)
        _counts(run, status='Bereit', beendet_am=now())
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        run = _run(name, lock=True)
        _save(run, status='Fehler', fehler=frappe.get_traceback(), beendet_am=now())
        frappe.db.commit()
        raise


def _cleanup_batch(name, token, names, report):
    run = _run(name, lock=True)
    if run.job_token != token or run.status != 'Bereinigung läuft':
        frappe.throw('Der Bereinigungsauftrag ist nicht mehr gültig.')
    frappe.db.sql('SELECT name FROM `tabRechnungsbereinigung Fall` WHERE name IN ({0}) '
        'ORDER BY name FOR UPDATE'.format(', '.join(['%s'] * len(names))), tuple(names))
    data = frappe.get_all(CASE, filters={'name': ['in', names], 'prueflauf': name},
        fields=['*'], order_by='name')
    if len(data) != len(names):
        frappe.throw('Ein ausgewählter Bereinigungsfall fehlt oder gehört zu einem anderen Prüflauf.')
    docs = [frappe.get_doc(dict(row, doctype=CASE)) for row in data]
    try:
        if any(doc.prueflauf != name or doc.status != 'Freigegeben' for doc in docs):
            raise ValueError('Mindestens ein Fall ist nicht freigegeben.')
        result = core.run(report=report, replacements={doc.alte_rechnung: doc.ersatzrechnung for doc in docs},
            dry_run=False, expected_replacements={doc.alte_rechnung: doc.ersatz_fingerprint for doc in docs},
            commit=False, trust_report=True)
        by_invoice = {row['rechnung']: row for row in result['faelle']}
        for doc in docs:
            row = by_invoice[doc.alte_rechnung]
            if row['status'] in ('bereinigt', 'bereits_bereinigt'):
                _save(doc, status='Bereinigt', bereinigt_von=frappe.session.user, bereinigt_am=now(),
                    sicherung=result.get('sicherung'), pruefhinweis='Bereinigung erfolgreich.')
            elif row['status'] == 'blockiert':
                values = _clear_approval()
                values.update(status='Blockiert', pruefhinweis=row['grund'])
                _save(doc, **values)
            else:
                _save(doc, pruefhinweis='Stapel wegen eines blockierten Falls nicht bereinigt. Freigabe bleibt bestehen.')
    except Exception as error:
        frappe.db.rollback()
        run = _run(name, lock=True)
        for item in names:
            doc = frappe.get_doc(CASE, item)
            values = _clear_approval()
            values.update(status='Blockiert', pruefhinweis='Stapel zurückgerollt: {0}'.format(error))
            _save(doc, **values)
    _counts(run, verarbeitet=cint(run.verarbeitet) + len(names))
    frappe.db.commit()


@frappe.whitelist()
def case_details(name):
    _authorize()
    doc = frappe.get_doc(CASE, name)
    run = _run(doc.prueflauf)
    unused, cases = _report(run)
    state = cases[doc.alte_rechnung]['snapshot']
    new_state = core.read_snapshots([doc.ersatzrechnung])[doc.ersatzrechnung] if doc.ersatzrechnung else None
    return {'original': _detail_rows(state), 'ersatz': _detail_rows(new_state) if new_state else None,
        'kandidaten': json.loads(doc.kandidaten or '[]'), 'pruefhinweis': doc.pruefhinweis}


def _detail_rows(state):
    return {'hauptbuch': [{key: row.get(key) for key in ('account', 'posting_date', 'party',
        'account_currency', 'debit', 'credit')} for row in state['gl']],
        'positionen': [{key: row.get(key) for key in ('item_code', 'item_name', 'qty', 'rate', 'amount')}
            for row in state['children'].get('Sales Invoice Item', [])], 'bezuege': state['references']}
