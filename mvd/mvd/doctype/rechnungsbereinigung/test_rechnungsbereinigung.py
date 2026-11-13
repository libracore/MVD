# -*- coding: utf-8 -*-
"""Isolierte Tests für UI-Freigaben, Zugriffe und Hintergrundverarbeitung."""
from __future__ import unicode_literals

import datetime
import importlib.util
import json
import os
import sys
import types
import unittest
from unittest.mock import Mock, patch


class Row(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


class FakeDocument(object):
    def __init__(self, **values):
        self.__dict__.update(values)
        self.flags = Row()
        self.before = None
        self.saved = 0

    def __getattr__(self, key):
        return None

    def get(self, key):
        return self.__dict__.get(key)

    def update(self, values):
        self.__dict__.update(values)

    def save(self, **kwargs):
        self.saved += 1

    def is_new(self):
        return False

    def get_doc_before_save(self):
        return self.before


class DeskReviewTest(unittest.TestCase):
    def setUp(self):
        frappe = types.ModuleType('frappe')
        frappe.whitelist = lambda: lambda fn: fn
        frappe.get_roles = Mock(return_value=['System Manager'])
        frappe.local = Row(request=Row(method='POST'))
        frappe.session = Row(user='reviewer@example.test')
        frappe.PermissionError = PermissionError
        def fail(message):
            raise ValueError(message)
        frappe.throw = fail
        frappe.db = Mock()
        frappe.get_doc = Mock()
        frappe.generate_hash = Mock(return_value='TOKEN')
        frappe.as_json = lambda value: json.dumps(value, default=str, sort_keys=True)
        self.frappe = frappe
        document = types.ModuleType('frappe.model.document')
        document.Document = FakeDocument
        utils = types.ModuleType('frappe.utils')
        utils.cint = lambda value: int(value or 0)
        utils.flt = lambda value: float(value or 0)
        utils.now = lambda: '2026-11-05 12:00:00'
        background = types.ModuleType('frappe.utils.background_jobs')
        background.enqueue = Mock()
        self.core = Mock()
        self.core.prepare_review_context.return_value = {'states': {'OLD': {}}}
        package = types.ModuleType('mvd.mvd.data_import')
        package.bereinige_verwaiste_rechnungen = self.core
        stubs = {'frappe': frappe, 'frappe.model.document': document, 'frappe.utils': utils,
            'frappe.utils.background_jobs': background, 'mvd.mvd.data_import': package}
        path = os.path.dirname(__file__)
        self.api = self.load('review_api', os.path.join(path, 'rechnungsbereinigung.py'), stubs)
        self.enqueue = background.enqueue
        key = 'mvd.mvd.doctype.rechnungsbereinigung.rechnungsbereinigung'
        stubs[key] = self.api
        self.case_module = self.load('review_case', os.path.join(path, '..',
            'rechnungsbereinigung_fall', 'rechnungsbereinigung_fall.py'), stubs)
        self.run = FakeDocument(name='RUN-1', status='Bereit', verarbeitet=0)
        self.case_module._run = Mock(return_value=self.run)
        self.frappe.db.get_value.return_value = None
        self.doc = FakeDocument(name='CASE-1', prueflauf='RUN-1', alte_rechnung='OLD',
            ersatzrechnung='NEW', status='Offen')

    def load(self, name, path, stubs):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, stubs):
            spec.loader.exec_module(module)
        return module

    def case_document(self, previous, **changes):
        values = dict(previous)
        values.update(changes)
        doc = self.case_module.RechnungsbereinigungFall(**values)
        doc.before = FakeDocument(**previous)
        doc.meta = Row(get_valid_columns=lambda: list(previous))
        return doc

    def test_every_endpoint_rejects_missing_role(self):
        self.frappe.get_roles.return_value = []
        for method, kwargs in (
                ('start_scan', {'name': 'RUN-1'}), ('review_cases', {'names': ['CASE-1']}),
                ('defer_cases', {'names': ['CASE-1']}), ('start_cleanup', {'name': 'RUN-1'}),
                ('case_details', {'name': 'CASE-1'})):
            with self.subTest(method=method):
                with self.assertRaises(PermissionError):
                    getattr(self.api, method)(**kwargs)
        self.frappe.get_doc.assert_not_called()

    def test_mutating_get_is_rejected(self):
        self.frappe.local.request.method = 'GET'
        with self.assertRaises(PermissionError):
            self.api.start_scan('RUN-1')
        self.enqueue.assert_not_called()

    def test_approval_requires_explicit_confirmation(self):
        with self.assertRaises(ValueError):
            self.api.review_cases(['CASE-1'], approve=True)
        self.core._prepare.assert_not_called()

    def test_approval_records_actor_time_without_live_checks(self):
        with patch.object(self.api, '_case_docs', return_value=(self.run, [self.doc])), \
                patch.object(self.api, '_report', return_value=({}, {'OLD': {'fingerprint': 'SAVED-HASH'}})), \
                patch.object(self.api, '_counts'):
            self.api.review_cases(['CASE-1'], approve=1, confirmed=1)
        self.assertEqual(self.doc.status, 'Freigegeben')
        self.assertEqual(self.doc.freigegeben_von, 'reviewer@example.test')
        self.assertEqual(self.doc.freigegeben_am, '2026-11-05 12:00:00')
        self.assertEqual(self.doc.freigegebener_ersatz, 'NEW')
        self.assertEqual(self.doc.ersatz_fingerprint, 'SAVED-HASH')
        self.core._prepare.assert_not_called()
        self.core.prepare_review_context.assert_not_called()
        self.core.run.assert_not_called()

    def test_blocked_check_clears_old_approval(self):
        self.doc.ersatz_fingerprint = 'OLD-HASH'
        self.core._prepare.side_effect = ValueError('Zahlungsbezug vorhanden')
        self.core.read_snapshots.return_value = {'OLD': {}}
        with patch.object(self.api, '_case_docs', return_value=(self.run, [self.doc])), \
                patch.object(self.api, '_report', return_value=({}, {'OLD': {}})), \
                patch.object(self.api, '_counts'):
            self.api.review_cases(['CASE-1'], approve=0)
        self.assertEqual(self.doc.status, 'Blockiert')
        self.assertIsNone(self.doc.ersatz_fingerprint)
        self.assertIsNone(self.doc.freigegeben_von)

    def test_replacement_edit_revokes_approval(self):
        doc = self.case_document({'status': 'Freigegeben', 'ersatzrechnung': 'NEW',
            'freigegeben_von': 'reviewer', 'freigegeben_am': 'DATE',
            'freigegebener_ersatz': 'NEW', 'ersatz_fingerprint': 'HASH'}, ersatzrechnung='OTHER')
        doc.validate()
        self.assertEqual(doc.status, 'Offen')
        self.assertIsNone(doc.freigegeben_von)
        self.assertIsNone(doc.ersatz_fingerprint)

    def test_busy_or_completed_cases_cannot_change_replacement(self):
        for status, run_status in (('Freigegeben', 'Bereinigung läuft'), ('Bereinigt', 'Bereit')):
            self.run.status = run_status
            doc = self.case_document({'status': status, 'ersatzrechnung': 'NEW'}, ersatzrechnung='OTHER')
            with self.assertRaises(ValueError):
                doc.validate()

    def test_client_cannot_forge_internal_flag_or_approval(self):
        doc = self.case_document({'status': 'Offen', 'ersatzrechnung': 'NEW'}, status='Freigegeben')
        doc.flags.interne_bereinigung = True
        with self.assertRaises(ValueError):
            doc.validate()

    def test_client_cannot_change_source_data(self):
        for field, old, new in (('alte_rechnung', 'OLD', 'OTHER'), ('betrag', 100, 0),
                ('freigegeben_von', None, 'admin')):
            with self.subTest(field=field):
                doc = self.case_document({field: old}, **{field: new})
                with self.assertRaises(ValueError):
                    doc.validate()

    def test_browser_date_serialization_is_not_treated_as_edit(self):
        doc = self.case_document({'buchungsdatum': datetime.date(2021, 10, 29),
            'ersatzrechnung': 'NEW'}, buchungsdatum='2021-10-29')
        doc.validate()

    def test_queue_runs_only_after_request_commit(self):
        self.run.status = 'Neu'
        with patch.object(self.api, '_run', return_value=self.run):
            self.api.start_scan('RUN-1')
        self.assertEqual(self.run.status, 'Wartet auf Prüfung')
        self.assertTrue(self.enqueue.call_args[1]['enqueue_after_commit'])
        self.assertEqual(self.enqueue.call_args[1]['queue'], 'long')
        self.frappe.db.commit.assert_not_called()

    def approved(self):
        self.doc.update({'status': 'Freigegeben', 'freigegeben_von': 'reviewer',
            'freigegeben_am': 'DATE', 'ersatz_fingerprint': 'HASH', 'freigegebener_ersatz': 'NEW'})
        self.run.update({'status': 'Bereinigung läuft', 'job_token': 'TOKEN'})
        self.frappe.get_doc.return_value = self.doc
        self.frappe.get_all = Mock(side_effect=lambda *args, **kwargs: [Row(self.doc.__dict__)])

    def test_worker_includes_ui_status_in_same_transaction(self):
        self.approved()
        self.core.run.return_value = {'status': 'bereinigt', 'sicherung': 'BACKUP',
            'faelle': [{'rechnung': 'OLD', 'status': 'bereinigt'}]}
        with patch.object(self.api, '_run', return_value=self.run), patch.object(self.api, '_counts'):
            self.api._cleanup_batch('RUN-1', 'TOKEN', ['CASE-1'], {})
        self.assertFalse(self.core.run.call_args[1]['commit'])
        self.assertTrue(self.core.run.call_args[1]['trust_report'])
        self.assertEqual(self.core.run.call_args[1]['expected_replacements'], {'OLD': 'HASH'})
        self.assertEqual(self.doc.status, 'Bereinigt')
        self.assertEqual(self.doc.sicherung, 'BACKUP')
        self.frappe.db.commit.assert_called_once_with()

    def test_worker_never_applies_unapproved_or_unrelated_cases(self):
        for field, value in (('status', 'Offen'), ('prueflauf', 'OTHER')):
            with self.subTest(field=field):
                self.approved()
                setattr(self.doc, field, value)
                with patch.object(self.api, '_run', return_value=self.run), patch.object(self.api, '_counts'):
                    self.api._cleanup_batch('RUN-1', 'TOKEN', ['CASE-1'], {})
                self.assertEqual(self.doc.status, 'Blockiert')
        self.core.run.assert_not_called()

    def test_manual_approval_also_works_without_replacement(self):
        self.doc.ersatzrechnung = None
        result = self.api._review_docs([self.doc], {'OLD': {'fingerprint': 'SAVED-HASH'}}, True)
        self.assertEqual(result[0]['status'], 'Freigegeben')
        self.assertIsNone(self.doc.freigegebener_ersatz)
        self.core._prepare.assert_not_called()
        self.core.prepare_review_context.assert_not_called()

    def test_worker_accepts_freigegeben_without_replacement_or_other_approval_fields(self):
        self.approved()
        self.doc.update({'ersatzrechnung': None, 'freigegeben_von': None,
            'freigegeben_am': None, 'ersatz_fingerprint': None, 'freigegebener_ersatz': None})
        self.core.run.return_value = {'status': 'bereinigt', 'sicherung': 'BACKUP',
            'faelle': [{'rechnung': 'OLD', 'status': 'bereinigt'}]}
        with patch.object(self.api, '_run', return_value=self.run), patch.object(self.api, '_counts'):
            self.api._cleanup_batch('RUN-1', 'TOKEN', ['CASE-1'], {})
        self.assertEqual(self.core.run.call_args[1]['replacements'], {'OLD': None})
        self.assertTrue(self.core.run.call_args[1]['trust_report'])
        self.assertEqual(self.doc.status, 'Bereinigt')

    def test_worker_rolls_back_error_and_revokes_approval(self):
        self.approved()
        self.core.run.side_effect = RuntimeError('Simulierter Fehler')
        with patch.object(self.api, '_run', return_value=self.run), patch.object(self.api, '_counts'):
            self.api._cleanup_batch('RUN-1', 'TOKEN', ['CASE-1'], {})
        self.frappe.db.rollback.assert_called_once_with()
        self.assertEqual(self.doc.status, 'Blockiert')
        self.assertIsNone(self.doc.ersatz_fingerprint)

    def test_stale_worker_token_never_runs_cleanup(self):
        self.approved()
        with patch.object(self.api, '_run', return_value=self.run):
            with self.assertRaises(ValueError):
                self.api._cleanup_batch('RUN-1', 'OTHER-TOKEN', ['CASE-1'], {})
        self.core.run.assert_not_called()

    def test_stale_form_cannot_overwrite_a_newer_approval(self):
        doc = self.case_document({'status': 'Offen', 'ersatzrechnung': 'NEW',
            'modified': '2026-11-05 10:00:00', 'notizen': None}, notizen='Notiz')
        self.frappe.db.get_value.return_value = '2026-11-05 11:00:00'
        with self.assertRaises(ValueError):
            doc.validate()

    def test_cleanup_requires_confirmation_and_can_resume_remaining_approvals(self):
        with self.assertRaises(ValueError):
            self.api.start_cleanup('RUN-1')
        self.run.update({'status': 'Fehler', 'report': 'pruefung_verwaiste_rechnungen_X.json'})
        self.frappe.get_all = Mock(return_value=[Row(name='CASE-1')])
        with patch.object(self.api, '_run', return_value=self.run):
            result = self.api.start_cleanup('RUN-1', confirmed=1)
        self.assertEqual(result['anzahl'], 1)
        self.assertEqual(json.loads(self.run.job_auswahl), ['CASE-1'])
        self.assertEqual(self.run.status, 'Wartet auf Bereinigung')
        self.assertTrue(self.enqueue.call_args[1]['enqueue_after_commit'])

    def test_scan_suggestions_never_approve_cases(self):
        self.run.update({'status': 'Wartet auf Prüfung', 'job_token': 'TOKEN'})
        report = {'faelle': [{'rechnung': 'OLD', 'company': 'Bern', 'basiswaehrung': 'CHF',
            'buchungsdatum_von': '2021-10-29', 'kunden': [{'kunde': 'K-1', 'saldoanteil_basiswaehrung': 100}]}]}
        self.core._load_report.return_value = report
        scanner = types.ModuleType('mvd.mvd.data_import.pruefe_verwaiste_rechnungen')
        scanner.run = Mock(return_value={'report': '/private/pruefung_verwaiste_rechnungen_X.json'})
        inserted = []
        def get_doc(values):
            doc = FakeDocument(**values)
            doc.db_insert = lambda: inserted.append(doc)
            return doc
        self.frappe.get_doc.side_effect = get_doc
        with patch.dict(sys.modules, {'mvd.mvd.data_import.pruefe_verwaiste_rechnungen': scanner}), \
                patch.object(self.api, '_run', return_value=self.run), \
                patch.object(self.api, '_suggestions', return_value={'OLD': ['NEW']}), \
                patch.object(self.api, '_counts'):
            self.api.scan_worker('RUN-1', 'TOKEN')
        self.assertEqual(len(inserted), 1)
        self.assertEqual(inserted[0].ersatzrechnung, 'NEW')
        self.assertEqual(inserted[0].status, 'Offen')
        self.assertIsNone(inserted[0].freigegeben_von)
        self.core.run.assert_not_called()

    def test_background_review_queues_2300_without_running_checks(self):
        self.run.report = 'pruefung_verwaiste_rechnungen_X.json'
        rows = [Row(name='CASE-' + str(index), ersatzrechnung='NEW-' + str(index),
            modified='2026-11-05 10:00:00') for index in range(2300)]
        with patch.object(self.api, '_case_rows', return_value=(self.run, rows)) as selected, \
                patch.object(self.api, '_report') as load:
            result = self.api.review_cases([row.name for row in rows], approve=1, confirmed=1, background=1)
        self.assertTrue(result['queued'])
        self.assertEqual(result['anzahl'], 2300)
        self.assertEqual(self.run.status, 'Wartet auf Prüfung')
        selection = json.loads(self.run.job_auswahl)
        self.assertEqual(selection['benutzer'], 'reviewer@example.test')
        self.assertEqual(selection['faelle'][0]['ersatzrechnung'], 'NEW-0')
        self.assertEqual(selected.call_args[1]['limit'], 5000)
        self.assertTrue(self.enqueue.call_args[1]['enqueue_after_commit'])
        self.assertTrue(self.enqueue.call_args[0][0].endswith('review_worker'))
        self.core._prepare.assert_not_called()
        self.core.prepare_review_context.assert_not_called()
        self.frappe.db.commit.assert_not_called()
        load.assert_not_called()

    def test_background_approval_still_requires_confirmation(self):
        with self.assertRaises(ValueError):
            self.api.review_cases(['CASE-1'], approve=1, background=1)
        self.enqueue.assert_not_called()

    def test_review_worker_loads_report_once_and_commits_progress(self):
        rows = [{'name': 'CASE-' + str(index), 'ersatzrechnung': 'NEW', 'modified': 'DATE'}
            for index in range(2300)]
        self.run.update({'status': 'Wartet auf Prüfung', 'job_token': 'TOKEN', 'job_auswahl': json.dumps({
            'art': 'freigabe', 'benutzer': self.frappe.session.user, 'faelle': rows})})
        self.frappe.get_all = Mock(side_effect=lambda doctype, filters, **kwargs: [Row(
            name=name, prueflauf='RUN-1', alte_rechnung='OLD-' + name, ersatzrechnung='NEW',
            modified='DATE', status='Offen') for name in filters['name'][1]])
        self.frappe.get_doc.side_effect = lambda values: FakeDocument(**values)
        with patch.object(self.api, '_run', return_value=self.run), \
                patch.object(self.api, '_report', return_value=({}, {})) as load, \
                patch.object(self.api, '_review_docs') as review, \
                patch.object(self.api, '_counts', side_effect=lambda run, **values: self.api._save(run, **values)):
            self.api.review_worker('RUN-1', 'TOKEN')
        load.assert_called_once_with(self.run)
        self.assertEqual([len(call[0][0]) for call in review.call_args_list], [100] * 23)
        self.assertTrue(all(call[0][2] for call in review.call_args_list))
        self.assertEqual(self.run.verarbeitet, 2300)
        self.assertEqual(self.run.status, 'Bereit')
        self.assertEqual(self.frappe.db.commit.call_count, 25)
        self.core.run.assert_not_called()

    def test_changed_queued_replacement_is_not_approved(self):
        self.doc.modified = 'DATE'
        result = self.api._review_docs([self.doc], {'OLD': {}}, True,
            expected={'CASE-1': {'ersatzrechnung': 'OTHER', 'modified': 'DATE'}})
        self.assertEqual(result[0]['status'], 'Blockiert')
        self.assertIsNone(self.doc.freigegeben_von)
        self.core._prepare.assert_not_called()

    def test_review_worker_stale_token_does_not_process(self):
        self.run.update({'status': 'Wartet auf Prüfung', 'job_token': 'TOKEN'})
        with patch.object(self.api, '_run', return_value=self.run), \
                patch.object(self.api, '_report') as load:
            self.api.review_worker('RUN-1', 'OTHER-TOKEN')
        load.assert_not_called()
        self.frappe.db.commit.assert_not_called()

    def test_review_worker_failure_keeps_completed_batches(self):
        rows = [{'name': 'CASE-' + str(index), 'ersatzrechnung': 'NEW', 'modified': 'DATE'} for index in range(101)]
        self.run.update({'status': 'Wartet auf Prüfung', 'job_token': 'TOKEN', 'job_auswahl': json.dumps({
            'art': 'freigabe', 'benutzer': self.frappe.session.user, 'faelle': rows})})
        self.frappe.get_traceback = Mock(return_value='simulated failure')
        self.frappe.get_all = Mock(side_effect=lambda doctype, filters, **kwargs: [Row(
            name=name, prueflauf='RUN-1', alte_rechnung='OLD', ersatzrechnung='NEW', modified='DATE',
            status='Offen') for name in filters['name'][1]])
        self.frappe.get_doc.side_effect = lambda values: FakeDocument(**values)
        with patch.object(self.api, '_run', return_value=self.run), \
                patch.object(self.api, '_report', return_value=({}, {})), \
                patch.object(self.api, '_review_docs', side_effect=[[], RuntimeError('failed')]), \
                patch.object(self.api, '_counts', side_effect=lambda run, **values: self.api._save(run, **values)):
            with self.assertRaises(RuntimeError):
                self.api.review_worker('RUN-1', 'TOKEN')
        self.assertEqual(self.run.status, 'Fehler')
        self.assertEqual(self.run.verarbeitet, 100)
        self.frappe.db.rollback.assert_called_once_with()
        self.assertEqual(self.frappe.db.commit.call_count, 3)


if __name__ == '__main__':
    unittest.main()
