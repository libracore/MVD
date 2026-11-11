# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.utils.rechnungs_bankkonto import set_lauf_bankkonto
from frappe.model.document import Document
from frappe.utils.csvutils import to_csv as make_csv
from frappe.utils.data import now, getdate, add_days, today
from frappe.utils.background_jobs import enqueue
from mvd.mvd.doctype.rechnungs_jahresversand.utils import get_csv_header, get_csv_rows

class RechnungsJahresversand(Document):
    def validate(self):
        if self.docstatus == 0:
            set_lauf_bankkonto(self)
        if not self.jahr:
            self.jahr = int(getdate(now()).strftime("%Y")) + 1
        if not self.counter or self.counter == 0:
            highest_counter = frappe.db.sql("""SELECT `counter` FROM `tabRechnungs Jahresversand` WHERE `sektion_id` = '{0}' ORDER BY `counter` DESC LIMIT 1""".format(self.sektion_id), as_dict=True)
            if len(highest_counter) > 0:
                self.counter = highest_counter[0].counter + 1
            else:
                self.counter = 1
        
        self.title = 'Jahresversand-{sektion_id}-{jahr}'.format(sektion_id=self.sektion_id, jahr=self.jahr)
    
    def start_csv_and_invoices(self):
        args = {
            'jahresversand': self.name
        }
        enqueue("mvd.mvd.doctype.rechnungs_jahresversand.utils.create_invoices_as_json", queue='long', job_name='Erstellung Rechnungsdaten & CSV {0}'.format(self.name), timeout=6000, **args)
        return

def run_jahresversand_verbuchung():
    pausiert = frappe.db.sql("""SELECT `name` FROM `tabRechnungs Jahresversand` WHERE `status` = 'Pausiert' AND `docstatus` = 1 ORDER BY `geplant_am` ASC""", as_dict=True)
    if len(pausiert) > 0:
        args = {
            'jahresversand': pausiert[0].name
        }
        enqueue("mvd.mvd.doctype.rechnungs_jahresversand.utils.create_invoices_from_json", queue='long', job_name='Erstellung Rechnungen {0}'.format(pausiert[0].name), timeout=23500, **args)
    else:
        ready_to_run = frappe.db.sql("""SELECT `name` FROM `tabRechnungs Jahresversand` WHERE `status` = 'Vorgemerkt für Rechnungsverbuchung' AND `docstatus` = 1 ORDER BY `geplant_am` ASC""", as_dict=True)
        if len(ready_to_run) > 0:
            args = {
                'jahresversand': ready_to_run[0].name
            }
            enqueue("mvd.mvd.doctype.rechnungs_jahresversand.utils.create_invoices_from_json", queue='long', job_name='Erstellung Rechnungen {0}'.format(ready_to_run[0].name), timeout=23500, **args)


@frappe.whitelist()
def start_rechnungsverbuchung(jahresversand, retry=False):
    jahresversand = frappe.get_doc("Rechnungs Jahresversand", jahresversand)
    jahresversand.status = 'Vorgemerkt für Rechnungsverbuchung'
    bereits_geplant = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabRechnungs Jahresversand` WHERE `status` = 'Vorgemerkt für Rechnungsverbuchung' AND `docstatus` = 1""", as_dict=True)[0].qty + 1
    geplant_fuer = getdate(add_days(today(), bereits_geplant)).strftime('%Y-%m-%d') + " 01:00:00"
    jahresversand.geplant_am = geplant_fuer
    if retry:
        jahresversand.is_retry = 1
    jahresversand.save()
    return

@frappe.whitelist()
def get_csv(jahresversand, bg_job=False):
    jahresversand = frappe.get_doc("Rechnungs Jahresversand", jahresversand)
    try:
        if bg_job:
            jahresversand.add_comment('Comment', text='Das CSV wird neu generiert...')
            frappe.db.commit()
            args = {
                'jahresversand': jahresversand.name
            }
            enqueue("mvd.mvd.doctype.rechnungs_jahresversand.rechnungs_jahresversand.get_csv", queue='long', job_name='CSV Neugenerierung {0}'.format(jahresversand), timeout=6000, **args)
            return

        data = [get_csv_header()]
        rechnungen = frappe.db.sql("""SELECT
                                            `name`,
                                            `mv_mitgliedschaft`
                                        FROM `tabSales Invoice`
                                        WHERE `docstatus` = 1
                                        AND `rechnungs_jahresversand` = '{rechnungs_jahresversand}'""".format(rechnungs_jahresversand=jahresversand.name), as_dict=True)
        
        for rechnung in rechnungen:
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", rechnung.mv_mitgliedschaft)
            sinv = frappe.get_doc("Sales Invoice", rechnung.name)
            hv_rechnungen = frappe.db.sql("""SELECT
                                                `name`
                                            FROM `tabFakultative Rechnung`
                                            WHERE `sales_invoice` = %s
                                            AND `docstatus` = 1""", (sinv.name,), as_dict=True)
            hv = None
            if hv_rechnungen:
                hv = frappe.get_doc("Fakultative Rechnung", hv_rechnungen[0].name).as_dict()

            rechnungsdaten = sinv.as_dict()
            rechnungsdaten["renaming_series"] = sinv.name
            
            data.extend(get_csv_rows(jahresversand, mitgliedschaft, rechnungsdaten, hv,
                mitgliederzeile=bool(mitgliedschaft.unabhaengiger_debitor)))

        csv_file = make_csv(data)
        file_name = "{titel}_{datetime}.csv".format(titel='Jahresversand-{sektion_id}-{jahr}'.format(sektion_id=jahresversand.sektion_id, jahr=jahresversand.jahr), datetime=now().replace(" ", "_"))
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home/Attachments",
            "is_private": 1,
            "content": csv_file,
            "attached_to_doctype": 'Rechnungs Jahresversand',
            "attached_to_name": jahresversand.name
        })
        
        _file.save()
        
        jahresversand.add_comment('Comment', text='CSV erstellt.')
        frappe.db.commit()
        
        return 'done'
    except frappe.DuplicateEntryError:
        jahresversand.add_comment('Comment', text='Identisches CSV existiert bereits.')
        frappe.db.commit()
        
        return 'done'

@frappe.whitelist()
def is_job_running(jobname):
    from frappe.utils.background_jobs import get_jobs
    running = get_info(jobname)
    return running

def get_info(jobname):
    from rq import Queue, Worker
    from frappe.utils.background_jobs import get_redis_conn
    from frappe.utils import format_datetime, cint, convert_utc_to_user_timezone
    colors = {
        'queued': 'orange',
        'failed': 'red',
        'started': 'blue',
        'finished': 'green'
    }
    conn = get_redis_conn()
    queues = Queue.all(conn)
    workers = Worker.all(conn)
    jobs = []
    show_failed=False

    def add_job(j, name):
        if j.kwargs.get('site')==frappe.local.site:
            jobs.append({
                'job_name': j.kwargs.get('kwargs', {}).get('playbook_method') \
                    or str(j.kwargs.get('job_name')),
                'status': j.status, 'queue': name,
                'creation': format_datetime(convert_utc_to_user_timezone(j.created_at)),
                'color': colors[j.status]
            })
            if j.exc_info:
                jobs[-1]['exc_info'] = j.exc_info

    for w in workers:
        j = w.get_current_job()
        if j:
            add_job(j, w.name)

    for q in queues:
        if q.name != 'failed':
            for j in q.get_jobs(): add_job(j, q.name)

    if cint(show_failed):
        for q in queues:
            if q.name == 'failed':
                for j in q.get_jobs()[:10]: add_job(j, q.name)
    
    found_job = 'refresh'
    for job in jobs:
        if job['job_name'] == jobname:
            found_job = True

    return found_job

