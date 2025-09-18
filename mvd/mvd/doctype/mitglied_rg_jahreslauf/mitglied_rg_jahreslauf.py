# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils.background_jobs import enqueue
from frappe.utils import cint
import copy
from frappe.utils.data import now, add_days, today
from mvd.mvd.utils.manuelle_rechnungs_items import get_item_price
from mvd.mvd.utils.qrr_reference import get_qrr_reference

class MitgliedRGJahreslauf(Document):
    def autoname(self):
        self.name = "MRJ-{0}".format(self.bezugsjahr)
        if frappe.db.exists("Mitglied RG Jahreslauf", self.name):
            self.name = make_autoname(
                "MRJ-{0}-.#".format(self.bezugsjahr)
            )
    
    def get_overview(self):
        sektions_selektionen = frappe.db.sql("""
            SELECT `sektion_id`, `docstatus`
            FROM `tabMRJ Sektions Selektion`
        """, as_dict=True)

        uebersicht = {}

        for sektions_selektion in sektions_selektionen:
            if sektions_selektion.sektion_id not in uebersicht:
                uebersicht[sektions_selektion.sektion_id] = []
            uebersicht[sektions_selektion.sektion_id].append(sektions_selektion.docstatus)

        return_list = []
        for key, value in uebersicht.items():
            return_list.append({"sektion": key, "docs": value})
        
        return return_list
    
    def check_start_rg(self):
        drafts = frappe.db.sql("""
            SELECT COUNT(`name`) AS `qty`
            FROM `tabMRJ Sektions Selektion`
            WHERE `mrj` = '{0}'
            AND `docstatus` = 0
        """.format(self.name), as_dict=True)[0].qty
        return drafts
    
    def start_rg(self):
        self.status = "In Warteschlange"
        self.save()
    
    def stop_rg(self):
        self.status = "Abgebrochen"
        self.save()

def mrj_worker():
    pausiert = frappe.db.sql("""SELECT `name` FROM `tabMitglied RG Jahreslauf` WHERE `status` = 'Rechnungserstellung pausiert'""", as_dict=True)
    if len(pausiert) > 0:
        if not is_job_already_running('Erstellung Rechnungen {0}'.format(pausiert[0].name)):
            args = {
                'mrj': pausiert[0].name
            }
            enqueue("mvd.mvd.doctype.mitglied_rg_jahreslauf.mitglied_rg_jahreslauf.create_invoices", queue='long', job_name='Erstellung Rechnungen {0}'.format(pausiert[0].name), timeout=23500, **args)
    else:
        ready_to_run = frappe.db.sql("""SELECT `name` FROM `tabMitglied RG Jahreslauf` WHERE `status` = 'In Warteschlange'""", as_dict=True)
        if len(ready_to_run) > 0:
            if not is_job_already_running('Erstellung Rechnungen {0}'.format(ready_to_run[0].name)):
                args = {
                    'mrj': ready_to_run[0].name
                }
                enqueue("mvd.mvd.doctype.mitglied_rg_jahreslauf.mitglied_rg_jahreslauf.create_invoices", queue='long', job_name='Erstellung Rechnungen {0}'.format(ready_to_run[0].name), timeout=23500, **args)

def create_invoices(mrj):
    def get_start_stop(mrj):
        return {
            'start_hour': cint(frappe.db.get_value("Mitglied RG Jahreslauf", mrj, "start_hour")),
            'start_minute': cint(frappe.db.get_value("Mitglied RG Jahreslauf", mrj, "start_minute")),
            'wknd_start_hour': cint(frappe.db.get_value("Mitglied RG Jahreslauf", mrj, "wknd_start_hour")),
            'wknd_start_minute': cint(frappe.db.get_value("Mitglied RG Jahreslauf", mrj, "wknd_start_minute")),
            'stop_hour': cint(frappe.db.get_value("Mitglied RG Jahreslauf", mrj, "stop_hour")),
            'stop_minute': cint(frappe.db.get_value("Mitglied RG Jahreslauf", mrj, "stop_minute")),
            'wknd_stop_hour': cint(frappe.db.get_value("Mitglied RG Jahreslauf", mrj, "wknd_stop_hour")),
            'wknd_stop_minute': cint(frappe.db.get_value("Mitglied RG Jahreslauf", mrj, "wknd_stop_minute"))
        }
    
    # Festlegen der Start-/Stop-Zeiten
    from datetime import datetime, time
    current_day = datetime.today().weekday()
    aktuelle_uhrzeit = datetime.now().time()
    start_stop = get_start_stop(mrj)
    if current_day >= 5:
        # Wochenende
        start_time = time(start_stop['wknd_start_hour'], start_stop['wknd_start_minute'])
        stop_time = time(start_stop['wknd_stop_hour'], start_stop['wknd_stop_minute'])
    else:
        # Wochentag
        start_time = time(start_stop['start_hour'], start_stop['start_minute'])
        stop_time = time(start_stop['stop_hour'], start_stop['stop_minute'])
    
    frappe.log_error(str(start_stop), "xxx")
    # Prüfung ob der Job gestartet werden darf
    if (aktuelle_uhrzeit < start_time) or (aktuelle_uhrzeit > stop_time):
        return

    frappe.db.set_value("Mitglied RG Jahreslauf", mrj, "status", "Erstelle Rechnungen")
    frappe.db.commit()

    sektions_selektion = None

    pausiert = frappe.db.sql("""
                             SELECT
                                `name`,
                                `sektion_id`,
                                `bezugsjahr`,
                                `mitgliedtyp_spezifisch`,
                                `mitgliedtyp`,
                                `sprach_spezifisch`,
                                `language`,
                                `region_spezifisch`,
                                `region`,
                                `druckvorlage`
                             FROM `tabMRJ Sektions Selektion` WHERE `status` = 'Rechnungsdaten in Arbeit'""", as_dict=True)
    if len(pausiert) > 0:
        sektions_selektion = pausiert[0]
    else:
        ready_to_run = frappe.db.sql("""
                                    SELECT
                                        `name`,
                                        `sektion_id`,
                                        `bezugsjahr`,
                                        `mitgliedtyp_spezifisch`,
                                        `mitgliedtyp`,
                                        `sprach_spezifisch`,
                                        `language`,
                                        `region_spezifisch`,
                                        `region`,
                                        `druckvorlage`
                                    FROM `tabMRJ Sektions Selektion` WHERE `status` = 'Bereit zur Ausführung'""", as_dict=True)
        if len(ready_to_run) > 0:
            sektions_selektion = ready_to_run[0]
    
    if not sektions_selektion:
        # alle sektions selektionen sind verarbeitet -> gesammter lauf ist verarbeitet
        frappe.db.set_value("Mitglied RG Jahreslauf", mrj, "status", "Rechnungen erstellt")
        frappe.db.commit()
        return
    
    mitgliedtyp_filter = ''
    if cint(sektions_selektion.mitgliedtyp_spezifisch):
        mitgliedtyp_filter = "AND `mitgliedtyp_c` = '{0}'".format(sektions_selektion.mitgliedtyp)
    
    language_filter = ''
    if cint(sektions_selektion.sprach_spezifisch):
        language_filter = "AND `language` = '{0}'".format(sektions_selektion.language)
    
    region_filter = ''
    if cint(sektions_selektion.region_spezifisch):
        region_filter = "AND `region` = '{0}'".format(sektions_selektion.region)
    
    mitglieder = frappe.db.sql("""
        SELECT `name`
        FROM `tabMitgliedschaft`
        WHERE `bezahltes_mitgliedschaftsjahr` < '{jahr}'
        AND `sektion_id` = '{sektion}'
        AND `status_c` IN ('Regulär', 'Zuzug', 'Online-Mutation')
        AND (
            `kuendigung` IS NULL
            OR
            `kuendigung` > '{jahr}-01-01'
        )
        {mitgliedtyp_filter}
        {language_filter}
        {region_filter}
        AND `name` NOT IN (
            SELECT `mv_mitgliedschaft`
            FROM `tabSales Invoice`
            WHERE `docstatus` = 1
            AND `sektion_id` = '{sektion}'
            AND `mitgliedschafts_jahr` = '{jahr}'
            AND `ist_mitgliedschaftsrechnung` = 1
        )
    """.format(sektion=sektions_selektion.sektion_id, jahr=sektions_selektion.bezugsjahr, mitgliedtyp_filter=mitgliedtyp_filter, \
            language_filter=language_filter, region_filter=region_filter), as_dict=True)
    
    if len(mitglieder) < 1:
        # keine mitglieder zur sektions selektion gefunden -> sektion selektion ist verarbeitet
        frappe.db.set_value("MRJ Sektions Selektion", sektions_selektion.name, "status", "Abgeschlossen")
        frappe.db.commit()
        # prozess neustart um nächste sektions selektion zu verarbeiten
        create_invoices(mrj)
    else:
        frappe.db.set_value("MRJ Sektions Selektion", sektions_selektion.name, "status", "Rechnungsdaten in Arbeit")
        frappe.db.commit()
    

    # setzen der Markierung des autom. stopps
    breaked_loop = False

    sektion = frappe.get_doc("Sektion", sektions_selektion.sektion_id)
    company = frappe.get_doc("Company", sektion.company)
    due_date = add_days(today(), 30)
    item_defaults = {
        'Privat': [{"item_code": sektion.mitgliedschafts_artikel,"qty": 1, "cost_center": company.cost_center, "rate": get_item_price(sektion.mitgliedschafts_artikel).get("price")}],
        'Geschäft': [{"item_code": sektion.mitgliedschafts_artikel_geschaeft,"qty": 1, "cost_center": company.cost_center, "rate": get_item_price(sektion.mitgliedschafts_artikel_geschaeft).get("price")}]
    }
    for mitglied in mitglieder:
        aktuelle_uhrzeit = datetime.now().time()
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitglied)
        create_invoice(mitgliedschaft, sektion, company, due_date, item_defaults, sektions_selektion.bezugsjahr, sektions_selektion.druckvorlage, sektions_selektion.druckvorlage_hv, mrj)
        # aktuelle_uhrzeit = datetime.now().time()
        if aktuelle_uhrzeit > stop_time:
            # autom. stoppzeit erreicht, prozess unterbrechen
            breaked_loop = True
            break
    
    if not breaked_loop:
        # loop durch komplette verarbeitung beendet
        frappe.db.set_value("MRJ Sektions Selektion", sektions_selektion.name, "status", "Abgeschlossen")
        frappe.db.commit()
        # prozess neustart um nächste sektions selektion zu verarbeiten
        create_invoices(mrj)
    else:
        # loop beendet weil autom. stoppzeit erreicht -> pausiert
        frappe.db.set_value("Mitglied RG Jahreslauf", mrj, "status", "Rechnungserstellung pausiert")
        frappe.db.commit()
        return

def create_invoice(mitgliedschaft, sektion, company, due_date, item_defaults, jahr, druckvorlage_rg, druckvorlage_hv, mrj):
    # ------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------
    '''
        Geschenkmitgliedschaften sowie Gratis Mitgliedschaften werden NICHT berücksichtigt
    '''
    # ------------------------------------------------------------------------------------
    skip = False
    if int(mitgliedschaft.ist_geschenkmitgliedschaft) == 1:
        skip = True
    if int(mitgliedschaft.reduzierte_mitgliedschaft) == 1 and not mitgliedschaft.reduzierter_betrag > 0:
        skip = True
    # ------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------
    
    if not skip:
        if not mitgliedschaft.rg_kunde:
            customer = mitgliedschaft.kunde_mitglied
            contact = mitgliedschaft.kontakt_mitglied
            if not mitgliedschaft.rg_adresse:
                address = mitgliedschaft.adresse_mitglied
            else:
                address = mitgliedschaft.rg_adresse
        else:
            customer = mitgliedschaft.rg_kunde
            address = mitgliedschaft.rg_adresse
            contact = mitgliedschaft.rg_kontakt
        
        item = copy.deepcopy(item_defaults.get(mitgliedschaft.mitgliedtyp_c))
        if cint(mitgliedschaft.reduzierte_mitgliedschaft) == 1 and mitgliedschaft.reduzierter_betrag > 0:
            item[0]["rate"] = mitgliedschaft.reduzierter_betrag
        
        sinv = frappe.get_doc({
            "doctype": "Sales Invoice",
            "ist_mitgliedschaftsrechnung": 1,
            "mv_mitgliedschaft": mitgliedschaft.name,
            "company": sektion.company,
            "cost_center": company.cost_center,
            "customer": customer,
            "customer_address": address,
            "contact_person": contact,
            'mitgliedschafts_jahr': jahr,
            'due_date': due_date,
            'debit_to': company.default_receivable_account,
            'sektions_code': str(sektion.sektion_id) or '00',
            'sektion_id': sektion.name,
            "items": item,
            "druckvorlage": druckvorlage_rg if druckvorlage_rg else '',
            "exclude_from_payment_reminder_until": '',
            "mrj": mrj,
            "allocate_advances_automatically": 1,
            "fast_mode": 1,
            "esr_reference": '',
            "outstanding_amount": item[0].get("rate"),
            "naming_series": "RJ-.{sektions_code}.#####",
            # "renaming_series": "RJ-{0}{1}{2}".format(str(sektion.sektion_id) or '00', jahresversand_doc.counter, str(current_series_index).rjust(5, "0"))
        }).insert()
        sinv.esr_reference = get_qrr_reference(sales_invoice=sinv.name)
        sinv.submit()

        fr = frappe.get_doc({
            "doctype": "Fakultative Rechnung",
            "mv_mitgliedschaft": mitgliedschaft.name,
            'due_date': due_date,
            'sektion_id': sektion.name,
            'sektions_code': str(sektion.sektion_id) or '00',
            'sales_invoice': sinv.name,
            'typ': 'HV',
            'betrag': sektion.betrag_hv,
            'posting_date': today(),
            'company': sektion.company,
            'druckvorlage': druckvorlage_hv if druckvorlage_hv else '',
            'bezugsjahr': jahr,
            'spenden_versand': '',
            "naming_series": "FRJ-.{sektions_code}.#####",
            # "renaming_series": "FRJ-{0}{1}{2}".format(str(sektion.sektion_id) or '00', jahresversand_doc.counter, str(current_fr_series_index).rjust(5, "0"))
        }).insert()
        fr.qrr_referenz = get_qrr_reference(fr=fr.name)
        fr.submit()

        frappe.db.commit()

def is_job_already_running(jobname):
    running = get_info(jobname)
    return running

def get_info(jobname):
    from rq import Queue, Worker
    from frappe.utils.background_jobs import get_redis_conn
    conn = get_redis_conn()
    queues = Queue.all(conn)
    workers = Worker.all(conn)
    jobs = []

    def add_job(j, name):
        if j.kwargs.get('site')==frappe.local.site:
            jobs.append({
                'job_name': str(j.kwargs.get('job_name')),
                'queue': name
            })

    for w in workers:
        j = w.get_current_job()
        if j:
            add_job(j, w.name)

    for q in queues:
        if q.name != 'failed':
            for j in q.get_jobs(): add_job(j, q.name)
    
    found_job = False
    for job in jobs:
        if job['job_name'] == jobname:
            found_job = True

    return found_job