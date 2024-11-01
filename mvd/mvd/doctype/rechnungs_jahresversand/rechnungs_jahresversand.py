# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.csvutils import to_csv as make_csv
from frappe.utils.data import now, getdate, add_days, today
from frappe.utils.background_jobs import enqueue

class RechnungsJahresversand(Document):
    def validate(self):
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
    from mvd.mvd.doctype.rechnungs_jahresversand.utils import create_invoices_from_json
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
        
        data = []
        header = [
            'firma',
            'zusatz_firma',
            'anrede',
            'briefanrede',
            'vorname_1',
            'nachname_1',
            'vorname_2',
            'nachname_2',
            'zusatz_adresse',
            'strasse',
            'postfach',
            'postfach_plz',
            'postfach_ort',
            'plz',
            'ort',
            'betrag_1',
            'ref_nr_1',
            'kz_1',
            'betrag_2',
            'ref_nr_2',
            'kz_2',
            'faktura_nr',
            'mitglied_nr',
            'jahr_ausweis',
            'mitgliedtyp_c',
            'sektion_c',
            'region_c',
            'hat_email',
            'e_mail_1',
            'e_mail_2',
            'zeilen_art',
            'ausweis_vorname_1',
            'ausweis_nachname_1',
            'ausweis_vorname_2',
            'ausweis_nachname_2',
            'bezahlt_fuer_firma',
            'bezahlt_fuer_name',
            'bezahlt_von_firma',
            'bezahlt_von_name',
            'spezielles'
        ]
        data.append(header)
        
        rechnungen = frappe.db.sql("""SELECT
                                            `name`,
                                            `mv_mitgliedschaft`
                                        FROM `tabSales Invoice`
                                        WHERE `docstatus` = 1
                                        AND `rechnungs_jahresversand` = '{rechnungs_jahresversand}'""".format(rechnungs_jahresversand=jahresversand.name), as_dict=True)
        
        for rechnung in rechnungen:
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", rechnung.mv_mitgliedschaft)
            
            # ------------------------------------------------------------------------------------
            # ------------------------------------------------------------------------------------
            '''
                Geschenkmitgliedschaften sowie Gratis Mitgliedschaften werden NICHT berücksichtigt
            '''
            # ------------------------------------------------------------------------------------
            skip = False
            if mitgliedschaft.ist_geschenkmitgliedschaft:
                skip = True
            if mitgliedschaft.reduzierte_mitgliedschaft and not mitgliedschaft.reduzierter_betrag > 0:
                skip = True
            # ------------------------------------------------------------------------------------
            # ------------------------------------------------------------------------------------
            
            if not skip:
                row_data = []
                pseudo_zeile = False
                
                if mitgliedschaft.unabhaengiger_debitor and mitgliedschaft.abweichende_rechnungsadresse:
                    # fremdzahler
                    if mitgliedschaft.rg_kundentyp == 'Unternehmen':
                        row_data.append(mitgliedschaft.rg_firma or '')
                        row_data.append(mitgliedschaft.rg_zusatz_firma or '')
                    else:
                        row_data.append("")
                        row_data.append("")
                    row_data.append(mitgliedschaft.rg_anrede or '')
                    row_data.append(mitgliedschaft.rg_briefanrede or '')
                    row_data.append(mitgliedschaft.rg_vorname or '')
                    row_data.append(mitgliedschaft.rg_nachname or '')
                    row_data.append("")
                    row_data.append("")
                else:
                    # selbstzahler
                    if mitgliedschaft.kundentyp == 'Unternehmen':
                        row_data.append(mitgliedschaft.firma or '')
                        row_data.append(mitgliedschaft.zusatz_firma or '')
                    else:
                        row_data.append("")
                        row_data.append("")
                    row_data.append(mitgliedschaft.anrede_c or '')
                    row_data.append(mitgliedschaft.rg_briefanrede or '')
                    row_data.append(mitgliedschaft.vorname_1 or '')
                    row_data.append(mitgliedschaft.nachname_1 or '')
                    if mitgliedschaft.hat_solidarmitglied:
                        row_data.append(mitgliedschaft.vorname_2 or '')
                        row_data.append(mitgliedschaft.nachname_2 or '')
                    else:
                        row_data.append("")
                        row_data.append("")
                
                if mitgliedschaft.abweichende_rechnungsadresse:
                    row_data.append(mitgliedschaft.rg_zusatz_adresse or '')
                    strasse = ''
                    strasse += mitgliedschaft.rg_strasse or ''
                    strasse += " " + str(mitgliedschaft.rg_nummer or '')
                    strasse += mitgliedschaft.rg_nummer_zu or ''
                    row_data.append(strasse)
                    if mitgliedschaft.rg_postfach:
                        row_data.append("Postfach {0}".format(mitgliedschaft.rg_postfach_nummer or ''))
                        row_data.append("")
                        row_data.append("")
                    else:
                        row_data.append("")
                        row_data.append("")
                        row_data.append("")
                    row_data.append(mitgliedschaft.rg_plz or '')
                    row_data.append(mitgliedschaft.rg_ort or '')
                else:
                    row_data.append(mitgliedschaft.zusatz_adresse or '')
                    strasse = ''
                    strasse += mitgliedschaft.strasse or ''
                    strasse += " " + str(mitgliedschaft.nummer or '')
                    strasse += mitgliedschaft.nummer_zu or ''
                    row_data.append(strasse)
                    if mitgliedschaft.postfach:
                        row_data.append("Postfach {0}".format(mitgliedschaft.postfach_nummer or ''))
                        row_data.append("")
                        row_data.append("")
                    else:
                        row_data.append("")
                        row_data.append("")
                        row_data.append("")
                    row_data.append(mitgliedschaft.plz or '')
                    row_data.append(mitgliedschaft.ort or '')
                
                sinv = frappe.get_doc("Sales Invoice", rechnung.name)
                hv_rechnungen = frappe.db.sql("""SELECT
                                                    `name`
                                                FROM `tabFakultative Rechnung`
                                                WHERE `sales_invoice` = '{sinv}'
                                                AND `docstatus` = 1""".format(sinv=sinv.name), as_dict=True)
                hv = False
                if len(hv_rechnungen) > 0:
                    hv = frappe.get_doc("Fakultative Rechnung", hv_rechnungen[0].name)
                
                row_data.append(sinv.outstanding_amount or 0.00)
                row_data.append(sinv.esr_reference or '')
                row_data.append('')
                row_data.append(hv.betrag if hv else '')
                row_data.append(hv.qrr_referenz if hv else '')
                row_data.append('')
                row_data.append(sinv.name or '')
                
                row_data.append(mitgliedschaft.mitglied_nr or '')
                row_data.append(jahresversand.jahr or '')
                row_data.append(mitgliedschaft.mitgliedtyp_c or '')
                row_data.append(mitgliedschaft.sektion_id or '')
                row_data.append('')
                row_data.append('')
                row_data.append(mitgliedschaft.e_mail_1 or '')
                row_data.append(mitgliedschaft.e_mail_2 or '')
                row_data.append('')
                row_data.append(mitgliedschaft.vorname_1 or '')
                row_data.append(mitgliedschaft.nachname_1 or '')
                
                if mitgliedschaft.hat_solidarmitglied:
                    row_data.append(mitgliedschaft.vorname_2 or '')
                    row_data.append(mitgliedschaft.nachname_2 or '')
                else:
                    row_data.append("")
                    row_data.append("")
                
                if mitgliedschaft.unabhaengiger_debitor:
                    pseudo_zeile = True
                    if mitgliedschaft.kundentyp == 'Unternehmen':
                        # bezahlt_fuer_firma
                        bezahlt_fuer_firma = mitgliedschaft.firma or ''
                        bezahlt_fuer_firma += ' ' if mitgliedschaft.firma else ''
                        bezahlt_fuer_firma += mitgliedschaft.zusatz_firma or ''
                        row_data.append(bezahlt_fuer_firma)
                        # bezahlt_fuer_name
                        bezahlt_fuer_name = mitgliedschaft.anrede_c or ''
                        bezahlt_fuer_name += ' ' if mitgliedschaft.anrede_c else ''
                        bezahlt_fuer_name += mitgliedschaft.vorname_1 or ''
                        bezahlt_fuer_name += ' ' if mitgliedschaft.vorname_1 else ''
                        bezahlt_fuer_name += mitgliedschaft.nachname_1 or ''
                        row_data.append(bezahlt_fuer_name)
                    else:
                        # bezahlt_fuer_name
                        row_data.append('')
                        bezahlt_fuer_name = mitgliedschaft.anrede_c or ''
                        bezahlt_fuer_name += ' ' if mitgliedschaft.anrede_c else ''
                        bezahlt_fuer_name += mitgliedschaft.vorname_1 or ''
                        bezahlt_fuer_name += ' ' if mitgliedschaft.vorname_1 else ''
                        bezahlt_fuer_name += mitgliedschaft.nachname_1 or ''
                        row_data.append(bezahlt_fuer_name)
                else:
                    # bezahlt_fuer_firma
                    row_data.append('')
                    # bezahlt_fuer_name
                    row_data.append('')
                
                # bezahlt_von_firma
                row_data.append('')
                # bezahlt_von_name
                row_data.append('')
                
                if pseudo_zeile:
                    if mitgliedschaft.ist_geschenkmitgliedschaft:
                        row_data.append('Geschenkmitgliedschaft')
                    else:
                        row_data.append('Unabhängiger Debitor')
                else:
                    if mitgliedschaft.reduzierte_mitgliedschaft:
                        row_data.append('Reduzierte Mitgliedschaft')
                    else:
                        row_data.append('')
                
                data.append(row_data)
                
                if pseudo_zeile:
                    row_data = []
                    if mitgliedschaft.kundentyp == 'Unternehmen':
                        row_data.append(mitgliedschaft.firma or '')
                        row_data.append(mitgliedschaft.zusatz_firma or '')
                    else:
                        row_data.append("")
                        row_data.append("")
                    row_data.append(mitgliedschaft.anrede_c or '')
                    row_data.append(mitgliedschaft.briefanrede or '')
                    row_data.append(mitgliedschaft.vorname_1 or '')
                    row_data.append(mitgliedschaft.nachname_1 or '')
                    if mitgliedschaft.hat_solidarmitglied:
                        row_data.append(mitgliedschaft.vorname_2 or '')
                        row_data.append(mitgliedschaft.nachname_2 or '')
                    else:
                        row_data.append("")
                        row_data.append("")
                
                    row_data.append(mitgliedschaft.zusatz_adresse or '')
                    strasse = ''
                    strasse += mitgliedschaft.strasse or ''
                    strasse += " " + str(mitgliedschaft.nummer or '')
                    strasse += mitgliedschaft.nummer_zu or ''
                    row_data.append(strasse)
                    if mitgliedschaft.postfach:
                        row_data.append("Postfach {0}".format(mitgliedschaft.postfach_nummer or ''))
                        row_data.append("")
                        row_data.append("")
                    else:
                        row_data.append("")
                        row_data.append("")
                        row_data.append("")
                    row_data.append(mitgliedschaft.plz or '')
                    row_data.append(mitgliedschaft.ort or '')
                    
                    row_data.append('--')
                    row_data.append('--')
                    row_data.append('--')
                    row_data.append('--')
                    row_data.append('--')
                    row_data.append('--')
                    row_data.append('--')
                    row_data.append(mitgliedschaft.mitglied_nr or '')
                    row_data.append(jahresversand.jahr or '')
                    row_data.append(mitgliedschaft.mitgliedtyp_c or '')
                    row_data.append(mitgliedschaft.sektion_id or '')
                    row_data.append('')
                    row_data.append('')
                    row_data.append(mitgliedschaft.e_mail_1 or '')
                    row_data.append(mitgliedschaft.e_mail_2 or '')
                    row_data.append('')
                    row_data.append(mitgliedschaft.vorname_1 or '')
                    row_data.append(mitgliedschaft.nachname_1 or '')
                    if mitgliedschaft.hat_solidarmitglied:
                        row_data.append(mitgliedschaft.vorname_2 or '')
                        row_data.append(mitgliedschaft.nachname_2 or '')
                    else:
                        row_data.append("")
                        row_data.append("")
                    
                    # bezahlt_fuer_firma
                    row_data.append('')
                    # bezahlt_fuer_name
                    row_data.append('')
                    
                    if mitgliedschaft.rg_kundentyp == 'Unternehmen':
                        # bezahlt_von_firma
                        bezahlt_von_firma = mitgliedschaft.rg_firma or ''
                        bezahlt_von_firma += ' ' if mitgliedschaft.rg_firma else ''
                        bezahlt_von_firma += mitgliedschaft.rg_zusatz_firma or ''
                        row_data.append(bezahlt_von_firma)
                        # bezahlt_von_name
                        bezahlt_von_name = mitgliedschaft.rg_anrede or ''
                        bezahlt_von_name += ' ' if mitgliedschaft.rg_anrede else ''
                        bezahlt_von_name += mitgliedschaft.rg_vorname or ''
                        bezahlt_von_name += ' ' if mitgliedschaft.rg_vorname else ''
                        bezahlt_von_name += mitgliedschaft.rg_nachname or ''
                        row_data.append(bezahlt_von_name)
                    else:
                        # bezahlt_von_name
                        row_data.append('')
                        bezahlt_von_name = mitgliedschaft.rg_anrede or ''
                        bezahlt_von_name += ' ' if mitgliedschaft.rg_anrede else ''
                        bezahlt_von_name += mitgliedschaft.rg_vorname or ''
                        bezahlt_von_name += ' ' if mitgliedschaft.rg_vorname else ''
                        bezahlt_von_name += mitgliedschaft.rg_nachname or ''
                        row_data.append(bezahlt_von_name)
                    
                    if mitgliedschaft.ist_geschenkmitgliedschaft:
                        row_data.append('Geschenkmitgliedschaft')
                    else:
                        if mitgliedschaft.reduzierte_mitgliedschaft:
                            row_data.append('Reduzierte Mitgliedschaft / Unabhängiger Debitor')
                        else:
                            row_data.append('Unabhängiger Debitor')
                    
                    data.append(row_data)
        
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

