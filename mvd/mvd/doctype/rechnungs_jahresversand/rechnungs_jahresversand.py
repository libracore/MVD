# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.csvutils import to_csv as make_csv
from frappe.utils.data import now, getdate
from mvd.mvd.utils.manuelle_rechnungs_items import get_item_price
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import create_mitgliedschaftsrechnung
from frappe.utils.background_jobs import enqueue

class RechnungsJahresversand(Document):
    def before_save(self):
        if not self.jahr:
            self.jahr = int(getdate(now()).strftime("%Y")) + 1

@frappe.whitelist()
def get_draft_csv(jahresversand=None):
    jahresversand = frappe.get_doc("Rechnungs Jahresversand", jahresversand)
    sektion = frappe.get_doc("Sektion", jahresversand.sektion_id)
    data = []
    header = [
        'firma',
        'zusatz_firma',
        'anrede',
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
        'bezahlt_fuer'
    ]
    data.append(header)
    
    mitgliedschaften = frappe.db.sql("""SELECT
                                            `name`
                                        FROM `tabMitgliedschaft`
                                        WHERE `sektion_id` = '{sektion_id}'
                                        AND `status_c` = 'Regulär'
                                        AND `name` NOT IN (
                                            SELECT
                                                `mv_mitgliedschaft`
                                            FROM `tabSales Invoice`
                                            WHERE `mitgliedschafts_jahr` = '{mitgliedschafts_jahr}'
                                            AND `ist_mitgliedschaftsrechnung` = 1
                                            AND `docstatus` = 1)""".format(sektion_id=jahresversand.sektion_id, mitgliedschafts_jahr=jahresversand.jahr), as_dict=True)
    
    for _mitgliedschaft in mitgliedschaften:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", _mitgliedschaft.name)
        row_data = []
        if mitgliedschaft.kundentyp == 'Unternehmen':
            row_data.append(mitgliedschaft.firma or '')
            row_data.append(mitgliedschaft.zusatz_firma or '')
        else:
            row_data.append("")
            row_data.append("")
        row_data.append(mitgliedschaft.anrede_c or '')
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
                row_data.append(mitgliedschaft.rg_postfach_nummer or '')
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
                row_data.append(mitgliedschaft.postfach_nummer or '')
                row_data.append("")
                row_data.append("")
            else:
                row_data.append("")
                row_data.append("")
                row_data.append("")
            row_data.append(mitgliedschaft.plz or '')
            row_data.append(mitgliedschaft.ort or '')
            
        # ~ sinv = frappe.get_doc("Sales Invoice", row.sales_invoice)
        row_data.append(get_invcoice_amount(mitgliedschaft, sektion))
        row_data.append('Entwurfsdaten')
        row_data.append('')
        row_data.append(get_hv_rate(mitgliedschaft, sektion))
        row_data.append('Entwurfsdaten')
        row_data.append('')
        row_data.append('Entwurfsdaten')
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
        row_data.append('')
        data.append(row_data)
    
    csv_file = make_csv(data)
    file_name = "DRAFT_{titel}_{datetime}.csv".format(titel='Jahresversand-{sektion_id}-{jahr}'.format(sektion_id=jahresversand.sektion_id, jahr=jahresversand.jahr), datetime=now().replace(" ", "_"))
    
    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "folder": "Home/Attachments",
        "is_private": 1,
        "content": csv_file,
        "attached_to_doctype": 'Rechnungs Jahresversand',
        "attached_to_name": jahresversand.name
    })
    
    _file.insert()
    
    return 'done'

def get_invcoice_amount(mitgliedschaft, sektion):
    if int(mitgliedschaft.reduzierte_mitgliedschaft) != 1:
        if mitgliedschaft.mitgliedtyp_c == 'Privat':
            return get_item_price(sektion.mitgliedschafts_artikel)
        elif mitgliedschaft.mitgliedtyp_c == 'Geschäft':
            return get_item_price(sektion.mitgliedschafts_artikel_geschaeft)
        else:
            return 'FEHLER'
    else:
        return mitgliedschaft.reduzierter_betrag

def get_hv_rate(mitgliedschaft, sektion):
    if mitgliedschaft.mitgliedtyp_c == 'Privat':
        return get_item_price(sektion.hv_artikel)
    else:
        return ''

def create_invoices(jahresversand):
    jahresversand = frappe.get_doc("Rechnungs Jahresversand", jahresversand)
    sektion = frappe.get_doc("Sektion", jahresversand.sektion_id)
    mitgliedschaften = frappe.db.sql("""SELECT
                                            `name`
                                        FROM `tabMitgliedschaft`
                                        WHERE `sektion_id` = '{sektion_id}'
                                        AND `status_c` = 'Regulär'
                                        AND `name` NOT IN (
                                            SELECT
                                                `mv_mitgliedschaft`
                                            FROM `tabSales Invoice`
                                            WHERE `mitgliedschafts_jahr` = '{mitgliedschafts_jahr}'
                                            AND `ist_mitgliedschaftsrechnung` = 1
                                            AND `docstatus` = 1)""".format(sektion_id=jahresversand.sektion_id, mitgliedschafts_jahr=jahresversand.jahr), as_dict=True)
    
    try:
        for mitgliedschaft in mitgliedschaften:
            sinv = create_mitgliedschaftsrechnung(mitgliedschaft.name, jahr=jahresversand.jahr, submit=True, ignore_stichtage=True, rechnungs_jahresversand=jahresversand.name)
        get_csv(jahresversand.name)
        jahresversand.status = 'Abgeschlossen'
        jahresversand.save()
    except Exception as err:
        jahresversand.status = 'Fehlgeschlagen'
        jahresversand.save()
        jahresversand.add_comment('Comment', text='{0}'.format(str(err)))

@frappe.whitelist()
def storno(jahresversand):
    new_name = jahresversand + "-" + str(frappe.generate_hash(now(), 10))
    frappe.rename_doc("Rechnungs Jahresversand", jahresversand, new_name)
    jahresversand = frappe.get_doc("Rechnungs Jahresversand", new_name)
    
    args = {
        'jahresversand': jahresversand
    }
    enqueue("mvd.mvd.doctype.rechnungs_jahresversand.rechnungs_jahresversand._storno", queue='long', job_name='Storniere Rechnungs Jahresversand {0}'.format(jahresversand.name), timeout=5000, **args)
    return new_name

def _storno(jahresversand):
    try:
        rechnungen = frappe.db.sql("""SELECT
                                        `name`
                                    FROM `tabSales Invoice`
                                    WHERE `docstatus` = 1
                                    AND `rechnungs_jahresversand` = '{rechnungs_jahresversand}'""".format(rechnungs_jahresversand=jahresversand.name), as_dict=True)
        
        for rechnung in rechnungen:
            sinv = frappe.get_doc("Sales Invoice", rechnung.name)
            hv_rechnungen = frappe.db.sql("""SELECT
                                                `name`
                                            FROM `tabFakultative Rechnung`
                                            WHERE `sales_invoice` = '{sinv}'
                                            AND `docstatus` = 1""".format(sinv=sinv.name), as_dict=True)
            if len(hv_rechnungen) > 0:
                for hv in hv_rechnungen:
                    hv_doc = frappe.get_doc("Fakultative Rechnung", hv.name)
                    hv_doc.cancel()
                    hv_doc.add_comment('Comment', text='Storniert aufgrund Rechnungs Jahresversand {0}'.format(jahresversand.name))
            sinv.cancel()
            sinv.add_comment('Comment', text='Storniert aufgrund Rechnungs Jahresversand {0}'.format(jahresversand.name))
        
        jahresversand.status = 'Storniert'
        jahresversand.save(ignore_permissions=True)
        jahresversand.add_comment('Comment', text='Stornierung durchgeführt')
        # ~ return new_name
    except Exception as err:
        jahresversand.add_comment('Comment', text='Stornierung Fehlgeschlagen!<br>{0}'.format(str(err)))
        # ~ return jahresversand.name
        
def get_csv(jahresversand):
    jahresversand = frappe.get_doc("MV Jahresversand", jahresversand)
    data = []
    header = [
        'firma',
        'zusatz_firma',
        'anrede',
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
        'bezahlt_fuer'
    ]
    data.append(header)
    
    rechnungen = frappe.db.sql("""SELECT
                                        `name`,
                                        `mv_mitgliedschaft`
                                    FROM `tabSales Invoice`
                                    WHERE `docstatus` = 1
                                    AND `rechnungs_jahresversand` = '{rechnungs_jahresversand}'""".format(rechnungs_jahresversand=jahresversand), as_dict=True)
    for rechnung in rechnungen:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", rechnung.mv_mitgliedschaft)
        row_data = []
        if mitgliedschaft.kundentyp == 'Unternehmen':
            row_data.append(mitgliedschaft.firma or '')
            row_data.append(mitgliedschaft.zusatz_firma or '')
        else:
            row_data.append("")
            row_data.append("")
        row_data.append(mitgliedschaft.anrede_c or '')
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
                row_data.append(mitgliedschaft.rg_postfach_nummer or '')
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
                row_data.append(mitgliedschaft.postfach_nummer or '')
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
        
        row_data.append(sinv.grand_total or '')
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
        row_data.append('')
        data.append(row_data)
    
    csv_file = make_csv(data)
    file_name = "{titel}_{datetime}.csv".format(titel='Jahresversand-{sektion_id}-{jahr}'.format(sektion_id=jahresversand.sektion_id, jahr=jahresversand.jahr), datetime=now().replace(" ", "_"))
    
    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "folder": "Home/Attachments",
        "is_private": 1,
        "content": csv_file,
        "attached_to_doctype": 'MV Jahresversand',
        "attached_to_name": jahresversand.name
    })
    
    _file.save()
    
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
