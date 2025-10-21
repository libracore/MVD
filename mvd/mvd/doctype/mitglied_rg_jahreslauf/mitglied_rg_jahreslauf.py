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
from PyPDF2 import PdfFileWriter
from frappe.utils.pdf import get_file_data_from_writer
from mvd.mvd.doctype.druckvorlage.druckvorlage import replace_mv_keywords

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
            WHERE `mrj` = '{0}'
        """.format(self.name), as_dict=True)

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
    
    def get_mail_accounts(self):
        accounts = frappe.get_all("Email Account", filters={ "enable_outgoing": 1 },
            fields=["email_id"],
            distinct=True)
        mail_accounts = "\n".join(acc.get("email_id") for acc in accounts)
        return mail_accounts
    
    def start_rg(self):
        self.status = "In Warteschlange"
        self.save()
    
    def stop_rg(self):
        self.status = "Abgebrochen"
        self.save()
    
    def create_pdf(self):
        self.status = "Erstelle PDFs"
        self.save()
    
    def stop_pdf(self):
        self.status = "Abgebrochen"
        self.save()
    
    def send_test_mails(self, sender_account=None, mail_account=None, qty=0, test_mail_mitglied=None):
        if not mail_account:
            frappe.throw("Die Auswahl des Mailaccounts ist fehlgeschlagen")
        
        self.status = "Versende Test E-Mails"
        self.test_email_account = mail_account
        self.email_account = sender_account
        self.use_sektion_mail_account = 0
        self.test_mail_qty = qty or 0
        self.test_mail_mitglied = test_mail_mitglied
        self.save()
    
    def send_mails(self, mail_from_sektion=0, mail_account=None):
        if mail_from_sektion == 0 and not mail_account:
            frappe.throw("Die Auswahl des Mailaccounts ist fehlgeschlagen")
        
        self.status = "Versende E-Mails"
        self.use_sektion_mail_account = mail_from_sektion or 0
        self.email_account = mail_account or None
        self.test_mail_qty = 0
        self.test_mail_mitglied = None
        self.save()
    
    def stop_mail(self):
        self.status = "Abgebrochen"
        self.save()

# ---------------------------------------------------
# Background Worker Method
# ---------------------------------------------------
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
        else:
            ready_for_pdf = frappe.db.sql("""SELECT `name` FROM `tabMitglied RG Jahreslauf` WHERE `status` = 'Erstelle PDFs'""", as_dict=True)
            if len(ready_for_pdf) > 0:
                if not is_job_already_running('Erstellung PDF {0}'.format(ready_for_pdf[0].name)):
                    args = {
                        'mrj': ready_for_pdf[0].name
                    }
                    enqueue("mvd.mvd.doctype.mitglied_rg_jahreslauf.mitglied_rg_jahreslauf.create_pdfs", queue='long', job_name='Erstellung PDF {0}'.format(ready_for_pdf[0].name), timeout=23500, **args)
            else:
                ready_for_test_mail = frappe.db.sql("""SELECT `name` FROM `tabMitglied RG Jahreslauf` WHERE `status` = 'Versende Test E-Mails'""", as_dict=True)
                if len(ready_for_test_mail) > 0:
                    if not is_job_already_running('Versende Test E-Mails {0}'.format(ready_for_test_mail[0].name)):
                        args = {
                            'mrj': ready_for_test_mail[0].name,
                            'test': True
                        }
                        enqueue("mvd.mvd.doctype.mitglied_rg_jahreslauf.mitglied_rg_jahreslauf.send_mails", queue='long', job_name='Versende Test E-Mails {0}'.format(ready_for_test_mail[0].name), timeout=23500, **args)
                else:
                    ready_for_mail = frappe.db.sql("""SELECT `name` FROM `tabMitglied RG Jahreslauf` WHERE `status` = 'Versende E-Mails'""", as_dict=True)
                    if len(ready_for_mail) > 0:
                        if not is_job_already_running('Versende E-Mails {0}'.format(ready_for_mail[0].name)):
                            args = {
                                'mrj': ready_for_mail[0].name,
                                'test': False
                            }
                            enqueue("mvd.mvd.doctype.mitglied_rg_jahreslauf.mitglied_rg_jahreslauf.send_mails", queue='long', job_name='Versende E-Mails {0}'.format(ready_for_mail[0].name), timeout=23500, **args)

# ---------------------------------------------------
# Helper Methods
# ---------------------------------------------------
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

# ---------------------------------------------------
# Create Methods
# ---------------------------------------------------
def create_invoices(mrj):
    def add_duchlaufszeit():
        # Comment Start- & End-Zeit inkl. Duchrlauszeit
        time_logging_end = datetime.now()
        durchlaufszeit = time_logging_end - time_logging_start
        frappe.get_doc("Mitglied RG Jahreslauf", mrj).add_comment('Comment', text='<b>Rechnungserstellung</b><br>Gestartet am: {0}<br>Beendet am: {1}<br>Durchlaufszeit: {2}'.format(time_logging_start, time_logging_end, durchlaufszeit))
        return
    
    # Festlegen der Start-/Stop-Zeiten
    from datetime import datetime, time
    current_day = datetime.today().weekday()
    aktuelle_uhrzeit = datetime.now().time()
    time_logging_start = datetime.now()
    start_stop = get_start_stop(mrj)
    if current_day >= 5:
        # Wochenende
        start_time = time(start_stop['wknd_start_hour'], start_stop['wknd_start_minute'])
        stop_time = time(start_stop['wknd_stop_hour'], start_stop['wknd_stop_minute'])
    else:
        # Wochentag
        start_time = time(start_stop['start_hour'], start_stop['start_minute'])
        stop_time = time(start_stop['stop_hour'], start_stop['stop_minute'])
    
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
                                `druckvorlage`,
                                `druckvorlage_hv`,
                                `druckvorlage_email`,
                                `druckvorlage_digitalrechnung`,
                                `sinv_date`,
                                `due_date_days`
                             FROM `tabMRJ Sektions Selektion` WHERE `status` = 'Rechnungsdaten in Arbeit'
                             AND `mrj` = '{0}'""".format(mrj), as_dict=True)
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
                                        `druckvorlage`,
                                        `druckvorlage_hv`,
                                        `druckvorlage_email`,
                                        `druckvorlage_digitalrechnung`,
                                        `sinv_date`,
                                        `due_date_days`
                                    FROM `tabMRJ Sektions Selektion` WHERE `status` = 'Bereit zur Ausführung'
                                    AND `mrj` = '{0}'""".format(mrj), as_dict=True)
        if len(ready_to_run) > 0:
            sektions_selektion = ready_to_run[0]
    
    if not sektions_selektion:
        # alle sektions selektionen sind verarbeitet -> gesammter lauf ist verarbeitet
        frappe.db.set_value("Mitglied RG Jahreslauf", mrj, "status", "Rechnungen erstellt")
        frappe.db.commit()
        add_duchlaufszeit()
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
    sinv_date = sektions_selektion.sinv_date
    due_date_days = cint(sektions_selektion.due_date_days) or 30
    due_date = add_days(sinv_date, due_date_days)
    item_defaults = {
        'Privat': [{"item_code": sektion.mitgliedschafts_artikel,"qty": 1, "cost_center": company.cost_center, "rate": get_item_price(sektion.mitgliedschafts_artikel).get("price")}],
        'Geschäft': [{"item_code": sektion.mitgliedschafts_artikel_geschaeft,"qty": 1, "cost_center": company.cost_center, "rate": get_item_price(sektion.mitgliedschafts_artikel_geschaeft).get("price")}]
    }
    for mitglied in mitglieder:
        aktuelle_uhrzeit = datetime.now().time()
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitglied)
        create_invoice(mitgliedschaft, sektion, company, sinv_date, due_date, item_defaults, sektions_selektion.bezugsjahr, sektions_selektion.druckvorlage, sektions_selektion.druckvorlage_hv, sektions_selektion.druckvorlage_email, sektions_selektion.druckvorlage_digitalrechnung, mrj)
        # aktuelle_uhrzeit = datetime.now().time()
        if aktuelle_uhrzeit > stop_time:
            # autom. stoppzeit erreicht, prozess unterbrechen
            breaked_loop = True
            break
    
    if not breaked_loop:
        # loop durch komplette verarbeitung beendet
        frappe.db.set_value("MRJ Sektions Selektion", sektions_selektion.name, "status", "Rechnungen erstellt")
        frappe.db.commit()
        # Comment Start- & End-Zeit inkl. Duchrlauszeit
        add_duchlaufszeit()
        # prozess neustart um nächste sektions selektion zu verarbeiten
        create_invoices(mrj)
    else:
        # loop beendet weil autom. stoppzeit erreicht -> pausiert
        frappe.db.set_value("Mitglied RG Jahreslauf", mrj, "status", "Rechnungserstellung pausiert")
        frappe.db.commit()
        # Comment Start- & End-Zeit inkl. Duchrlauszeit
        add_duchlaufszeit()
        return

def create_invoice(mitgliedschaft, sektion, company, sinv_date, due_date, item_defaults, jahr, druckvorlage_rg, druckvorlage_hv, druckvorlage_email, druckvorlage_digitalrechnung, mrj):
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
            "set_posting_time": 1,
            "posting_date": sinv_date,
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
            "druckvorlage_email": druckvorlage_email if druckvorlage_email else '',
            "druckvorlage_digitalrechnung": druckvorlage_digitalrechnung if druckvorlage_digitalrechnung else '',
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

        if mitgliedschaft.mitgliedtyp_c == 'Privat':
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

def create_pdfs(mrj):
    def add_duchlaufszeit():
        # Comment Start- & End-Zeit inkl. Duchrlauszeit
        time_logging_end = datetime.now()
        durchlaufszeit = time_logging_end - time_logging_start
        frappe.get_doc("Mitglied RG Jahreslauf", mrj).add_comment('Comment', text='<b>PDF Erstellung</b><br>Gestartet am: {0}<br>Beendet am: {1}<br>Durchlaufszeit: {2}'.format(time_logging_start, time_logging_end, durchlaufszeit))
        return

    # Festlegen der Start-/Stop-Zeiten
    from datetime import datetime, time
    current_day = datetime.today().weekday()
    aktuelle_uhrzeit = datetime.now().time()
    time_logging_start = datetime.now()
    start_stop = get_start_stop(mrj)
    if current_day >= 5:
        # Wochenende
        start_time = time(start_stop['wknd_start_hour'], start_stop['wknd_start_minute'])
        stop_time = time(start_stop['wknd_stop_hour'], start_stop['wknd_stop_minute'])
    else:
        # Wochentag
        start_time = time(start_stop['start_hour'], start_stop['start_minute'])
        stop_time = time(start_stop['stop_hour'], start_stop['stop_minute'])
    
    # Prüfung ob der Job gestartet werden darf
    if (aktuelle_uhrzeit < start_time) or (aktuelle_uhrzeit > stop_time):
        return
    
    frappe.db.sql("""SET SQL_BIG_SELECTS=1""")
    sinvs = frappe.db.sql("""
        SELECT
            `sinv`.`name` AS `sinv_name`,
            `sinv`.`druckvorlage` AS `sinv_druckvorlage`,
            `fak`.`name` AS `fak_name`,
            `fak`.`druckvorlage` AS `fak_druckvorlage`
        FROM `tabSales Invoice` AS `sinv`
        LEFT JOIN `tabFakultative Rechnung` AS `fak` ON `fak`.`sales_invoice` = `sinv`.`name`
        WHERE `sinv`.`mrj` = '{mrj}'
        AND `sinv`.`docstatus` = 1
        AND `sinv`.`status` != 'Paid'
        AND `sinv`.`mrj_pdf_erstellt` != 1
    """.format(mrj=mrj), as_dict=True)
    frappe.db.sql("""SET SQL_BIG_SELECTS=0""")

    breaked_loop = False
    for sinv in sinvs:
        aktuelle_uhrzeit = datetime.now().time()
        try:
            # erstellung Rechnungs PDF
            sinv_output = PdfFileWriter()
            sinv_output = frappe.get_print("Sales Invoice", sinv.sinv_name, 'Automatisierte Mitgliedschaftsrechnung', as_pdf = True, output = sinv_output, ignore_zugferd=True)
            sinv_file_name = "MRJ-{sinv}_{datetime}".format(sinv=sinv.sinv_name, datetime=now().replace(" ", "_"))
            sinv_file_name = sinv_file_name.split(".")[0]
            sinv_file_name = sinv_file_name.replace(":", "-")
            sinv_file_name = sinv_file_name + ".pdf"
            sinv_filedata = get_file_data_from_writer(sinv_output)
            sinv_file = frappe.get_doc({
                "doctype": "File",
                "file_name": sinv_file_name,
                "folder": "Home/Attachments",
                "is_private": 1,
                "content": sinv_filedata,
                "attached_to_doctype": 'Sales Invoice',
                "attached_to_name": sinv.sinv_name
            })
            sinv_file.save(ignore_permissions=True)
            frappe.db.set_value("Sales Invoice", sinv.sinv_name, "mrj_pdf_erstellt", 1)

            # erstellung Fak-Rechnungs PDF
            if sinv.fak_name:
                fak_output = PdfFileWriter()
                fak_output = frappe.get_print("Fakultative Rechnung", sinv.fak_name, 'Fakultative Rechnung', as_pdf = True, output = fak_output, ignore_zugferd=True)
                fak_file_name = "MRJ-{sinv}_{datetime}".format(sinv=sinv.fak_name, datetime=now().replace(" ", "_"))
                fak_file_name = fak_file_name.split(".")[0]
                fak_file_name = fak_file_name.replace(":", "-")
                fak_file_name = fak_file_name + ".pdf"
                fak_filedata = get_file_data_from_writer(fak_output)
                fak_file = frappe.get_doc({
                    "doctype": "File",
                    "file_name": fak_file_name,
                    "folder": "Home/Attachments",
                    "is_private": 1,
                    "content": fak_filedata,
                    "attached_to_doctype": 'Fakultative Rechnung',
                    "attached_to_name": sinv.fak_name
                })
                fak_file.save(ignore_permissions=True)
            frappe.db.commit()
        except frappe.exceptions.DuplicateEntryError:
            continue
        except Exception as err:
            frappe.log_error(str(err), "Failed MRJ: Create PDFs")
            frappe.db.set_value("Mitglied RG Jahreslauf", mrj, "status", "Fehlgeschlagen")
            frappe.db.commit()
            breaked_loop = True
            break

        if aktuelle_uhrzeit > stop_time:
            # autom. stoppzeit erreicht, prozess unterbrechen
            breaked_loop = True
            break
    
    if not breaked_loop:
        # loop durch komplette verarbeitung beendet
        frappe.db.set_value("Mitglied RG Jahreslauf", mrj, "status", "PDFs erstellt")
        frappe.db.commit()
    
    add_duchlaufszeit()

    return

def send_mails(mrj, test=False):
    def add_duchlaufszeit():
        # Comment Start- & End-Zeit inkl. Duchrlauszeit
        time_logging_end = datetime.now()
        durchlaufszeit = time_logging_end - time_logging_start
        frappe.get_doc("Mitglied RG Jahreslauf", mrj).add_comment('Comment', text='<b>E-Mail Versand</b><br>Gestartet am: {0}<br>Beendet am: {1}<br>Durchlaufszeit: {2}'.format(time_logging_start, time_logging_end, durchlaufszeit))
        return
    
    def get_sender_and_reply_to(sektion):
        if frappe.db.get_value("Mitglied RG Jahreslauf", mrj, "use_sektion_mail_account") == 1:
            sektion_mail = frappe.db.get_value("Sektion", sektion, "serien_email_absender_adresse")
            return sektion_mail, sektion_mail
        
        dummy_mail = frappe.db.get_value("Mitglied RG Jahreslauf", mrj, "email_account")
        reply_to = "{0}@{1}".format(sektion.lower(), dummy_mail.split("@")[1])
        return dummy_mail, reply_to

    def get_recipient(mitglied):
        abw_debitor = 0
        abw_rg_adr = frappe.db.get_value("Mitgliedschaft", mitglied, "abweichende_rechnungsadresse") or 0
        if abw_rg_adr:
            abw_debitor = frappe.db.get_value("Mitgliedschaft", mitglied, "unabhaengiger_debitor") or 0
        if abw_debitor == 1:
            return frappe.db.get_value("Mitgliedschaft", mitglied, "rg_e_mail") or None
        
        return frappe.db.get_value("Mitgliedschaft", mitglied, "e_mail_1") or None
    
    # Festlegen der Start-/Stop-Zeiten
    from datetime import datetime, time
    current_day = datetime.today().weekday()
    aktuelle_uhrzeit = datetime.now().time()
    time_logging_start = datetime.now()
    start_stop = get_start_stop(mrj)
    if current_day >= 5:
        # Wochenende
        start_time = time(start_stop['wknd_start_hour'], start_stop['wknd_start_minute'])
        stop_time = time(start_stop['wknd_stop_hour'], start_stop['wknd_stop_minute'])
    else:
        # Wochentag
        start_time = time(start_stop['start_hour'], start_stop['start_minute'])
        stop_time = time(start_stop['stop_hour'], start_stop['stop_minute'])
    
    # Prüfung ob der Job gestartet werden darf
    if (aktuelle_uhrzeit < start_time) or (aktuelle_uhrzeit > stop_time):
        return

    if test:
        frappe.db.set_value("Mitglied RG Jahreslauf", mrj, "status", "Versende Test E-Mails")
        recipient = frappe.db.get_value("Mitglied RG Jahreslauf", mrj, "test_email_account")
        limit = frappe.db.get_value("Mitglied RG Jahreslauf", mrj, "test_mail_qty") or 0
        limit_filter = ""
        if limit > 0:
            limit_filter = "LIMIT {0}".format(limit)
        test_mail_mitglied = frappe.db.get_value("Mitglied RG Jahreslauf", mrj, "test_mail_mitglied")
        if test_mail_mitglied:
            test_mail_mitglied = "AND `sinv`.`mv_mitgliedschaft` = {0}".format(test_mail_mitglied)
        else:
            test_mail_mitglied = ""
    else:
        frappe.db.set_value("Mitglied RG Jahreslauf", mrj, "status", "Versende E-Mails")
        limit_filter = ""
        test_mail_mitglied = ""
    frappe.db.commit()

    frappe.db.sql("""SET SQL_BIG_SELECTS=1""")
    sinvs = frappe.db.sql("""
        SELECT
            `sinv`.`name` AS `sinv_name`,
            `sinv`.`sektion_id` AS `sektion`,
            `sinv`.`druckvorlage_email`,
            `sinv`.`druckvorlage_digitalrechnung`,
            `sinv`.`mv_mitgliedschaft` AS `mitglied`,
            `fak`.`name` AS `fak_name`
        FROM `tabSales Invoice` AS `sinv`
        LEFT JOIN `tabFakultative Rechnung` AS `fak` ON `fak`.`sales_invoice` = `sinv`.`name`
        WHERE `sinv`.`mrj` = '{mrj}'
        AND `sinv`.`docstatus` = 1
        AND `sinv`.`status` != 'Paid'
        AND `sinv`.`mrj_email_versendet` != 1
        AND `sinv`.`mrj_pdf_erstellt` = 1
        {test_mail_mitglied}
        ORDER BY `sinv`.`sektion_id` ASC
        {limit_filter}
    """.format(mrj=mrj, test_mail_mitglied=test_mail_mitglied, limit_filter=limit_filter), as_dict=True)
    frappe.db.sql("""SET SQL_BIG_SELECTS=0""")

    sektion = None
    sektion_footer = None
    sender = None
    reply_to = None
    breaked_loop = False
    for sinv in sinvs:
        if sinv.sektion != sektion:
            sektion = sinv.sektion
            sender, reply_to = get_sender_and_reply_to(sektion)
            sektion_footer = frappe.get_value("Sektion", sektion, "footer")
    
        attachments = []
        sinv_attachment = frappe.get_all("File", fields=["name", "file_name"],
            filters = {"attached_to_name": sinv.sinv_name, "attached_to_doctype": "Sales Invoice"})
        for si_att in sinv_attachment:
            if "MRJ-RJ-" in si_att.get("file_name"):
                attachments.append({'fid': si_att.get("name")})
        
        fak_attachment = frappe.get_all("File", fields=["name", "file_name"],
            filters = {"attached_to_name": sinv.fak_name, "attached_to_doctype": "Fakultative Rechnung"})
        for fak_att in fak_attachment:
            if "MRJ-FRJ-" in fak_att.get("file_name"):
                attachments.append({'fid': fak_att.get("name")})
        
        recipient = get_recipient(sinv.mitglied) if not test else recipient
        email_vorlage = sinv.druckvorlage_email
        if cint(frappe.db.get_value("Mitgliedschaft", sinv.mitglied, "digitalrechnung")) == 1:
            email_vorlage = sinv.druckvorlage_digitalrechnung
        subject_txt = frappe.db.get_value("Druckvorlage", email_vorlage, "e_mail_betreff")
        message_txt = "{0}<br><br>{1}".format(frappe.db.get_value("Druckvorlage", email_vorlage, "e_mail_text"), sektion_footer)
        subject = replace_mv_keywords(subject_txt, sinv.mitglied)
        message = replace_mv_keywords(message_txt, sinv.mitglied)
        if len(attachments) > 0 and recipient:
            frappe.sendmail(sender="{0} <{1}>".format(frappe.get_value("Sektion", sektion, "serien_email_absender_name"), sender),
                            recipients=[recipient],
                            message=message,
                            subject=subject,
                            reply_to=reply_to,
                            attachments=attachments)
            if not test:
                frappe.db.set_value("Sales Invoice", sinv.sinv_name, "mrj_email_versendet", 1)
                frappe.db.commit()
        
        if aktuelle_uhrzeit > stop_time:
            # autom. stoppzeit erreicht, prozess unterbrechen
            breaked_loop = True
            break
    
    if not breaked_loop:
        # loop durch komplette verarbeitung beendet
        if test:
            frappe.db.set_value("Mitglied RG Jahreslauf", mrj, "status", "Test E-Mails versendet")
        else:
            frappe.db.set_value("Mitglied RG Jahreslauf", mrj, "status", "E-Mails versendet")
        frappe.db.commit()
    
    add_duchlaufszeit()

    return