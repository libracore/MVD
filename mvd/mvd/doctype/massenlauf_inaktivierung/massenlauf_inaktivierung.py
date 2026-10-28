# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint, escape_html
from frappe.utils.data import now, getdate
from frappe.utils.background_jobs import enqueue
from rq.timeouts import JobTimeoutException
import hashlib
import time

from mvd.mvd.doctype.retouren.retouren import close_open_retouren
from mvd.mvd.utils import rg_massenlauf_log


DOCTYPE = 'Massenlauf Inaktivierung'
CHILD_DOCTYPE = 'Massenlauf Inaktivierung Mitgliedschaften'
BATCH_SIZE = 20
BATCH_SECONDS = 120
JOB_TIMEOUT = 5000


class MassenlaufInaktivierung(Document):
    def before_save(self):
        if self.mitgliedschaften:
            return

        filters = []
        values = {'sektion': self.sektion_id}
        if cint(self.relevantes_mitgliedschaftsjahr) > 0:
            filters.append('AND sinv.`mitgliedschafts_jahr` = %(jahr)s')
            values['jahr'] = self.relevantes_mitgliedschaftsjahr
            if cint(self.ausnahme_folgejahr) == 1 and cint(self.ausnahme_jahr) > 0:
                filters.append('''AND ms.`name` NOT IN (
                    SELECT `name` FROM `tabMitgliedschaft`
                    WHERE `bezahltes_mitgliedschaftsjahr` = %(ausnahme_jahr)s
                )''')
                values['ausnahme_jahr'] = self.ausnahme_jahr

        mitgliedschaften = frappe.db.sql('''
            SELECT DISTINCT ms.`name` AS mv_mitgliedschaft,
                ms.`vorname_1` AS vorname, ms.`nachname_1` AS nachname,
                ms.`firma`, ms.`mitglied_nr`, ms.`nachname_2`, ms.`vorname_2`,
                ms.`strasse`, ms.`nummer`, ms.`plz`, ms.`ort`,
                ms.`eintrittsdatum` AS eintritt
            FROM `tabSales Invoice` sinv
            INNER JOIN `tabMitgliedschaft` ms ON ms.`name` = sinv.`mv_mitgliedschaft`
            WHERE sinv.`outstanding_amount` > 0
                AND sinv.`docstatus` = 1
                AND sinv.`sektion_id` = %(sektion)s
                AND sinv.`ist_mitgliedschaftsrechnung` = 1
                AND sinv.`status` = 'Overdue'
                AND ms.`status_c` = 'Regulär'
                AND ms.`kuendigung` IS NULL
                {filters}
        '''.format(filters='\n'.join(filters)), values, as_dict=True)
        for mitgliedschaft in mitgliedschaften:
            self.append('mitgliedschaften', mitgliedschaft)

    def before_submit(self):
        self.status = 'Vorgemerkt'
        _enqueue(self.name)

def _enqueue(doc, after_commit=True):
    return enqueue(
        'mvd.mvd.doctype.massenlauf_inaktivierung.massenlauf_inaktivierung.start_massenlauf_inaktivierung',
        queue='long',
        job_name='Massenlauf Inaktivierung ({0})'.format(doc),
        timeout=JOB_TIMEOUT,
        enqueue_after_commit=after_commit,
        doc=doc
    )

def _enqueue_committed(doc):
    # Sicherstellung dass verzögerte Jobs garantiert enqueued werden
    try:
        _enqueue(doc, after_commit=False)
    except Exception as error:
        traceback = frappe.get_traceback()
        frappe.db.rollback()
        _update_progress(doc, 'Fehlgeschlagen')
        _add_comment(doc, 'Der Backgroundjob konnte nicht erstellt werden: {0}'.format(str(error)))
        frappe.log_error(message=traceback, title='Massenlauf Inaktivierung ({0})'.format(doc))
        frappe.db.commit()
        raise

def _lock_name(doc):
    key = '{0}:{1}'.format(frappe.local.site, doc).encode('utf-8')
    return 'mvd.inaktivierung.' + hashlib.sha1(key).hexdigest()

def _acquire_lock(doc):
    # Verbindungssperre
    return frappe.db.sql('SELECT GET_LOCK(%s, 0)', (_lock_name(doc),))[0][0] == 1

def _release_lock(doc):
    frappe.db.sql('SELECT RELEASE_LOCK(%s)', (_lock_name(doc),))

def _get_run(doc):
    # Den grossen Beleg mit allen Adress-/Kinddaten nicht pro Paket erneut laden.
    return frappe.db.get_value(DOCTYPE, doc, [
            'name',
            'docstatus',
            'status',
            'ausschluss',
            'sektion_id',
            'grund',
            'rg_storno',
            'm_w_retouren_schliessen'
        ],
        as_dict=True
    )


@frappe.whitelist()
def fortsetzen(doc):
    massenlauf = frappe.get_doc(DOCTYPE, doc)
    massenlauf.check_permission('write')
    if massenlauf.docstatus != 1 or massenlauf.status == 'Abgeschlossen':
        frappe.throw('Nur gebuchte und nicht abgeschlossene Läufe können fortgesetzt werden.')
    if not _acquire_lock(doc):
        frappe.throw('Der Massenlauf wird gerade verarbeitet. Bitte später erneut versuchen.')
    try:
        # Nach dem setzen der Sperre den Massenlauf neu laden, denn der vorherige Worker könnte den Massenlauf inzwischen abgeschlossen haben
        frappe.db.rollback()
        massenlauf = _get_run(doc)
        if not massenlauf or massenlauf.docstatus != 1 or massenlauf.status == 'Abgeschlossen':
            frappe.throw('Nur gebuchte, nicht abgeschlossene Läufe können fortgesetzt werden.')

        frappe.db.sql('''
            UPDATE `tabMassenlauf Inaktivierung Mitgliedschaften`
            SET
                `verarbeitungsstatus` = '',
                `verarbeitungsfehler` = ''
            WHERE `parent` = %s
            AND `parenttype` = %s
            AND `parentfield` = 'mitgliedschaften'
            AND `verarbeitungsstatus` IN ('Fehlgeschlagen', 'In Arbeit')
        ''', (doc, DOCTYPE))
        _update_progress(doc, 'Vorgemerkt')
        frappe.db.commit()
    finally:
        _release_lock(doc)
    _enqueue_committed(doc)


def start_massenlauf_inaktivierung(doc):
    if not _acquire_lock(doc):
        return

    more = False
    row = None
    try:
        massenlauf = _get_run(doc)
        if not massenlauf or massenlauf.docstatus != 1 or massenlauf.status == 'Abgeschlossen':
            return
        rows = frappe.db.sql('''
                SELECT
                    `name`,
                    `mv_mitgliedschaft`,
                    `ausschluss_vollzogen`,
                    `ausschluss_begonnen`,
                    `verarbeitungsschritt`
                FROM `tabMassenlauf Inaktivierung Mitgliedschaften`
                WHERE `parent` = %s
                AND `parenttype` = %s
                AND `parentfield` = 'mitgliedschaften'
                AND COALESCE(`verarbeitungsstatus`, '') = ''
                ORDER BY `idx`, `name`
                LIMIT %s
            ''',
            (doc, DOCTYPE, BATCH_SIZE),
            as_dict=True
        )

        _update_progress(doc, 'In Arbeit')
        frappe.db.commit()

        started = time.monotonic()
        for row in rows:
            # Abbruch wenn der Massenlauf in der Zwischenzeit storniert wurde
            if frappe.db.get_value(DOCTYPE, doc, 'docstatus') != 1:
                return
            try:
                _process_membership(massenlauf, row)
            except JobTimeoutException:
                raise
            except Exception as error:
                _record_error(doc, row, error, frappe.get_traceback())
            row = None
            if time.monotonic() - started >= BATCH_SECONDS:
                break

        counts = _update_progress(doc)
        more = bool(counts.offen)

        if not more:
            status = 'Fehlgeschlagen' if counts.fehler or counts.in_arbeit else 'Abgeschlossen'
            _update_progress(doc, status)
            _add_comment(doc, 'Massenlauf beendet: {0}'.format(_progress_text(counts)))

        frappe.db.commit()
    except Exception as error:
        traceback = frappe.get_traceback()
        if row:
            _record_error(doc, row, error, traceback)
        else:
            frappe.db.rollback()
            frappe.log_error(message=traceback, title='Massenlauf Inaktivierung ({0})'.format(doc))

        if frappe.db.get_value(DOCTYPE, doc, 'docstatus') == 1:
            _update_progress(doc, 'Fehlgeschlagen')
            _add_comment(doc, 'Massenlauf unterbrochen: {0}'.format(str(error)))

        frappe.db.commit()
        raise
    finally:
        _release_lock(doc)

    if more:
        # Nächster Backgroundjob starten
        _enqueue_committed(doc)

def _set_row(row, **values):
    frappe.db.set_value(CHILD_DOCTYPE, row.name, values, update_modified=False)
    row.update(values)

def _set_step(massenlauf, row, step):
    _set_row(row, verarbeitungsstatus='In Arbeit', verarbeitungsschritt=step, verarbeitungsfehler='')
    frappe.db.set_value(DOCTYPE, massenlauf.name, 'letzte_aktivitaet', now())
    frappe.db.commit()

def _process_membership(massenlauf, row):
    _set_step(massenlauf, row, 'Mitgliedschaft laden')
    ms = frappe.get_doc('Mitgliedschaft', row.mv_mitgliedschaft)
    if not cint(row.ausschluss_vollzogen):
        if ms.status_c in ('Ausschluss', 'Inaktiv'):
            if cint(row.ausschluss_begonnen):
                frappe.throw('Mitgliedschaft {0}: Ausschluss wurde begonnen, aber nicht als vollständig gespeichert bestätigt. Bitte Teilschritte manuell prüfen.'.format(ms.name))
            _set_row(row, verarbeitungsstatus='Übersprungen', verarbeitungsschritt='Bereits ausgeschlossen oder inaktiv')
            _add_comment(massenlauf.name, 'Mitgliedschaft {0} ist bereits ausgeschlossen respektive inaktiv.'.format(ms.mitglied_nr))
            frappe.db.commit()
            return

        _set_row(row, ausschluss_begonnen=1)
        _set_step(massenlauf, row, 'Ausschluss speichern')
        _exclude_membership(massenlauf, ms)
        _set_row(row, ausschluss_vollzogen=1)
        frappe.db.commit()
    elif ms.status_c not in ('Ausschluss', 'Inaktiv'):
        frappe.throw('Mitgliedschaft {0}: Status wurde nach dem Ausschluss geändert. Bitte vor dem Fortsetzen prüfen.'.format(ms.name))

    if cint(massenlauf.m_w_retouren_schliessen) == 1:
        _set_step(massenlauf, row, 'M+W-Retouren schliessen')
        close_open_retouren(ms.name)
        frappe.db.commit()

    if cint(massenlauf.rg_storno) == 1:
        _cancel_invoices(massenlauf, row, ms.name)

    _set_row(row, verarbeitungsstatus='Abgeschlossen', verarbeitungsschritt='Fertig', verarbeitungsfehler='')
    frappe.db.commit()

def _exclude_membership(massenlauf, ms):
    change = ms.append('status_change', {})
    change.datum = now()
    change.status_alt = ms.status_c
    change.status_neu = 'Ausschluss'
    change.grund = massenlauf.grund
    ms.austritt = massenlauf.ausschluss
    ms.status_c = 'Ausschluss'
    ms.wichtig = 'Ausschluss:\n{0}\n\n{1}'.format(massenlauf.grund, ms.wichtig or '')
    ms.adressen_gesperrt = 1
    ms.letzte_bearbeitung_von = 'User'
    for field in (
            'validierung_notwendig', 'kuendigung_verarbeiten',
            'interessent_innenbrief_mit_ez', 'anmeldung_mit_ez',
            'zuzug_massendruck', 'rg_massendruck_vormerkung',
            'begruessung_massendruck', 'begruessung_via_zahlung',
            'zuzugs_rechnung', 'zuzug_korrespondenz', 'kuendigung_druckvorlage',
            'rg_massendruck', 'begruessung_massendruck_dokument'):
        ms.set(field, None)
    ms.save()
    ms.add_comment('Comment', text='Ausschluss vollzogen ({0} {1} ({2}))'.format(
        massenlauf.ausschluss, massenlauf.sektion_id, massenlauf.name))
    rg_massenlauf_log(mitglied=ms.name, sinv=None, vormerkung=0)


def _cancel_invoices(massenlauf, row, mitgliedschaft):
    curr_year = getdate(now()).year
    _set_step(massenlauf, row, 'Offene Mitgliedschaftsrechnungen laden')
    sinvs = frappe.db.sql('''
            SELECT
                `name`
            FROM `tabSales Invoice`
            WHERE `ist_mitgliedschaftsrechnung` = 1
            AND `mitgliedschafts_jahr` >= %s
            AND `docstatus` = 1
            AND `mv_mitgliedschaft` = %s
            AND `status` != 'Paid'
        ''',
        (curr_year, mitgliedschaft),
        as_dict=True
    )

    for sinv in sinvs:
        mahnungen = frappe.db.sql('''
                SELECT DISTINCT `parent`
                FROM `tabMahnung Invoices`
                WHERE `sales_invoice` = %s
                AND `docstatus` = 1
            ''',
            (sinv.name,),
            as_dict=True
        )

        for mahnung in mahnungen:
            _cancel_document(massenlauf, row, 'Mahnung', mahnung.parent)
        _cancel_document(massenlauf, row, 'Sales Invoice', sinv.name)

    _set_step(massenlauf, row, 'Offene fakultative Rechnungen laden')
    frs = frappe.db.sql('''
            SELECT
                `name`
            FROM `tabFakultative Rechnung`
            WHERE `bezugsjahr` >= %s
            AND `docstatus` = 1
            AND `mv_mitgliedschaft` = %s
            AND `status` != 'Paid'
        ''',
        (curr_year, mitgliedschaft),
        as_dict=True
    )

    for fr in frs:
        _cancel_document(massenlauf, row, 'Fakultative Rechnung', fr.name)

def _cancel_document(massenlauf, row, doctype, name):
    _set_step(massenlauf, row, '{0} {1} stornieren'.format(doctype, name))
    document = frappe.get_doc(doctype, name)
    if document.docstatus == 2:
        return
    # Prüfung ob bezahlt nochmals durchführen, da zB paralell ein CAMT-Import laufen könnte.
    if doctype != 'Mahnung' and document.status == 'Paid':
        return
    document.cancel()
    document.add_comment('Comment', text='Storniert aufgrund Ausschluss ({0} {1} ({2}))'.format(
        massenlauf.ausschluss, massenlauf.sektion_id, massenlauf.name)
    )
    frappe.db.commit()


def _record_error(doc, row, error, traceback):
    frappe.db.rollback()
    message = '{0}: {1}\n{2}'.format(row.verarbeitungsschritt or 'Unbekannter Schritt', str(error), traceback)
    _set_row(row, verarbeitungsstatus='Fehlgeschlagen', verarbeitungsfehler=message)
    frappe.log_error(message='{0}\n{1}'.format(row.mv_mitgliedschaft, message), title='Massenlauf Inaktivierung ({0})'.format(doc))
    _add_comment(doc, 'Fehlgeschlagen: {0} / {1}: {2}'.format(row.mv_mitgliedschaft, row.verarbeitungsschritt, str(error)))
    frappe.db.commit()


def _progress_text(counts):
    return '{0} von {1} verarbeitet ({2} Fehler, {3} übersprungen)'.format(
        cint(counts.total - counts.offen - counts.in_arbeit),
        cint(counts.total),
        cint(counts.fehler),
        cint(counts.uebersprungen)
    )


def _update_progress(doc, status=None):
    counts = frappe.db.sql('''
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(COALESCE(`verarbeitungsstatus`, '') = ''), 0) AS offen,
                COALESCE(SUM(`verarbeitungsstatus` = 'In Arbeit'), 0) AS in_arbeit,
                COALESCE(SUM(`verarbeitungsstatus` = 'Fehlgeschlagen'), 0) AS fehler,
                COALESCE(SUM(`verarbeitungsstatus` = 'Übersprungen'), 0) AS uebersprungen
            FROM `tabMassenlauf Inaktivierung Mitgliedschaften`
            WHERE `parent` = %s
            AND `parenttype` = %s
            AND `parentfield` = 'mitgliedschaften'
        ''',
        (doc, DOCTYPE),
        as_dict=True
    )[0]
    timestamp = now()
    values = {'fortschritt': _progress_text(counts), 'letzte_aktivitaet': timestamp}

    if status:
        values['status'] = status

    frappe.db.set_value(DOCTYPE, doc, values, modified=timestamp)
    frappe.publish_realtime('doc_update', {
            'doctype': DOCTYPE,
            'name': doc,
            'modified': timestamp
        },
        doctype=DOCTYPE,
        docname=doc,
        after_commit=True
    )

    return counts


def _add_comment(doc, text):
    frappe.get_doc({
        'doctype': 'Comment',
        'comment_type': 'Comment',
        'reference_doctype': DOCTYPE,
        'reference_name': doc,
        'content': escape_html(text)
    }).insert(ignore_permissions=True)
