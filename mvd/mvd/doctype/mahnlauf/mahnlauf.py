# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import add_to_date, nowdate
from datetime import datetime
from frappe.utils.background_jobs import enqueue
from frappe.core.doctype.communication.email import make
from frappe import sendmail, get_print
from mvd.mvd.doctype.druckvorlage.druckvorlage import replace_mv_keywords

class Mahnlauf(Document):
    def onload(self):
        self.entwurfs_mahnungen = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabMahnung` WHERE `mahnlauf` = '{mahnlauf}' AND `docstatus` = 0""".format(mahnlauf=self.name), as_dict=True)[0].qty or 0
        self.gebuchte_mahnungen = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabMahnung` WHERE `mahnlauf` = '{mahnlauf}' AND `docstatus` = 1""".format(mahnlauf=self.name), as_dict=True)[0].qty or 0
        self.stornierte_mahnungen = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabMahnung` WHERE `mahnlauf` = '{mahnlauf}' AND `docstatus` = 2""".format(mahnlauf=self.name), as_dict=True)[0].qty or 0
        self.anzahl_pdf, self.anzahl_mail, self.mahnungen_total = self.get_anzahl()
    
    def validate(self):
       # berechne relevantes Fälligkeitsdatum
        mahnstufen_frist = frappe.db.get_value('Sektion', self.sektion_id, 'mahnstufe_{0}'.format(self.mahnstufe)) * -1
        ueberfaellig_seit = add_to_date(nowdate(), days=mahnstufen_frist)
        self.ueberfaellig_seit = ueberfaellig_seit
        if not self.druckvorlage:
            self.druckvorlage = self.get_druckvorlage()
        if not self.e_mail_vorlage:
            self.e_mail_vorlage = self.get_e_mail_vorlage()
    
    def on_submit(self):
        if self.druckvorlage:
            self.get_invoices()
        else:
            frappe.throw("Bitte wählen Sie eine Druckvorlage aus.")
    
    def get_druckvorlage(self):
        druckvorlagen = frappe.db.sql("""SELECT
                                            `name`
                                        FROM `tabDruckvorlage`
                                        WHERE `sektion_id` = '{sektion_id}'
                                        AND `language` = 'de'
                                        AND `dokument` = 'Mahnung'
                                        AND `mahnstufe` = '{mahnstufe}'
                                        AND `default` = 1
                                        AND `mahntyp` = '{typ}'
                                        AND `e_mail_vorlage` != 1""".format(sektion_id=self.sektion_id, mahnstufe=self.mahnstufe, typ=self.typ), as_dict=True)
        if len(druckvorlagen) > 0:
            return druckvorlagen[0].name
        else:
            return None
        
    def get_e_mail_vorlage(self):
        if self.mahnungen_per_mail == 'Ja':
            druckvorlagen = frappe.db.sql("""SELECT
                                                `name`
                                            FROM `tabDruckvorlage`
                                            WHERE `sektion_id` = '{sektion_id}'
                                            AND `language` = 'de'
                                            AND `dokument` = 'Mahnung'
                                            AND `mahnstufe` = '{mahnstufe}'
                                            AND `default` = 1
                                            AND `mahntyp` = '{typ}'
                                            AND `e_mail_vorlage` = 1""".format(sektion_id=self.sektion_id, mahnstufe=self.mahnstufe, typ=self.typ), as_dict=True)
            if len(druckvorlagen) > 0:
                return druckvorlagen[0].name
            else:
                return None
        else:
            return None
    
    def get_anzahl(self):
        if self.typ == 'Produkte / Dienstleistungen':
            rg_typ_filter = """AND `sinv`.`ist_sonstige_rechnung` = 1"""
        elif self.typ == 'Mitgliedschaft (Jahresrechnung)':
            rg_typ_filter = """
                            AND `sinv`.`ist_mitgliedschaftsrechnung` = 1 
                            AND `mvm`.`status_c` NOT IN ('Anmeldung', 'Online-Anmeldung')
                            """
        elif self.typ == 'Anmeldungen':
            rg_typ_filter = """
                            AND `sinv`.`ist_mitgliedschaftsrechnung` = 1 
                            AND `mvm`.`status_c` IN ('Anmeldung', 'Online-Anmeldung')
                            """
        else:
            frappe.throw("Unbekannter Mahnlauf Typ")
        
        if self.is_new() or (self.entwurfs_mahnungen + self.gebuchte_mahnungen + self.stornierte_mahnungen) == 0:
            if int(self.zahlungserinnerungen) != 1:
                e_mails = frappe.db.sql("""SELECT
                                            SUM(CASE
                                                WHEN `mvm`.`unabhaengiger_debitor` = 1 AND `mvm`.`rg_e_mail` LIKE '%@%' THEN 1
                                                WHEN `mvm`.`unabhaengiger_debitor` != 1 AND `mvm`.`e_mail_1` LIKE '%@%' THEN 1
                                                WHEN `cus`.`unabhaengiger_debitor` = 1 AND `cus`.`rg_e_mail` LIKE '%@%' THEN 1
                                                WHEN `cus`.`unabhaengiger_debitor` != 1 AND `cus`.`e_mail` LIKE '%@%' THEN 1
                                                ELSE 0
                                            END) AS `e_mail`
                                        FROM `tabSales Invoice` AS `sinv`
                                        LEFT JOIN `tabMitgliedschaft` AS `mvm` ON `sinv`.`mv_mitgliedschaft` = `mvm`.`name`
                                        LEFT JOIN `tabKunden` AS `cus` ON `sinv`.`mv_kunde` = `cus`.`name`
                                        WHERE `sinv`.`sektion_id` = '{sektion_id}'
                                        AND `sinv`.`docstatus` = 1
                                        AND `sinv`.`status` != 'Paid'
                                        AND `sinv`.`due_date` <= '{ueberfaellig_seit}'
                                        {rg_typ_filter}
                                        AND `sinv`.`payment_reminder_level` = {mahnstufe}
                                        AND ((`sinv`.`exclude_from_payment_reminder_until` IS NULL) OR (`sinv`.`exclude_from_payment_reminder_until` < CURDATE()))""".format(sektion_id=self.sektion_id, \
                                        ueberfaellig_seit=self.ueberfaellig_seit, mahnstufe=int(self.mahnstufe) - 1, rg_typ_filter=rg_typ_filter), as_dict=True)[0].e_mail or 0
                alle = frappe.db.sql("""SELECT
                                            COUNT(`sinv`.`name`) AS `qty`
                                        FROM `tabSales Invoice` AS `sinv`
                                        LEFT JOIN `tabMitgliedschaft` AS `mvm` ON `sinv`.`mv_mitgliedschaft` = `mvm`.`name`
                                        WHERE `sinv`.`sektion_id` = '{sektion_id}'
                                        AND `sinv`.`docstatus` = 1
                                        AND `sinv`.`status` != 'Paid'
                                        AND `sinv`.`due_date` <= '{ueberfaellig_seit}'
                                        {rg_typ_filter}
                                        AND `sinv`.`payment_reminder_level` = {mahnstufe}
                                        AND ((`sinv`.`exclude_from_payment_reminder_until` IS NULL) OR (`sinv`.`exclude_from_payment_reminder_until` < CURDATE()))""".format(sektion_id=self.sektion_id, \
                                        ueberfaellig_seit=self.ueberfaellig_seit, mahnstufe=int(self.mahnstufe) - 1, rg_typ_filter=rg_typ_filter), as_dict=True)[0].qty or 0
                return alle - e_mails, e_mails, alle
            else:
                e_mails = frappe.db.sql("""SELECT
                                            SUM(CASE
                                                WHEN `mvm`.`unabhaengiger_debitor` = 1 AND `mvm`.`rg_e_mail` LIKE '%@%' THEN 1
                                                WHEN `mvm`.`unabhaengiger_debitor` != 1 AND `mvm`.`e_mail_1` LIKE '%@%' THEN 1
                                                WHEN `cus`.`unabhaengiger_debitor` = 1 AND `cus`.`rg_e_mail` LIKE '%@%' THEN 1
                                                WHEN `cus`.`unabhaengiger_debitor` != 1 AND `cus`.`e_mail` LIKE '%@%' THEN 1
                                                ELSE 0
                                            END) AS `e_mail`
                                        FROM `tabSales Invoice` AS `sinv`
                                        LEFT JOIN `tabMitgliedschaft` AS `mvm` ON `sinv`.`mv_mitgliedschaft` = `mvm`.`name`
                                        LEFT JOIN `tabKunden` AS `cus` ON `sinv`.`mv_kunde` = `cus`.`name`
                                        WHERE `sinv`.`sektion_id` = '{sektion_id}'
                                        AND `sinv`.`docstatus` = 1
                                        AND `sinv`.`status` != 'Paid'
                                        AND `sinv`.`due_date` <= '{ueberfaellig_seit}'
                                        {rg_typ_filter}
                                        AND `sinv`.`payment_reminder_level` = {mahnstufe}
                                        AND ((`sinv`.`exclude_from_payment_reminder_until` IS NULL) OR (`sinv`.`exclude_from_payment_reminder_until` < CURDATE()))""".format(sektion_id=self.sektion_id, \
                                        ueberfaellig_seit=self.ueberfaellig_seit, mahnstufe=int(self.mahnstufe) - 1, rg_typ_filter=rg_typ_filter), as_dict=True)[0].e_mail or 0
                return 0, e_mails, e_mails
        else:
            if int(self.zahlungserinnerungen) != 1:
                e_mails = frappe.db.sql("""SELECT
                                            SUM(CASE
                                                WHEN `mvm`.`unabhaengiger_debitor` = 1 AND `mvm`.`rg_e_mail` LIKE '%@%' THEN 1
                                                WHEN `mvm`.`unabhaengiger_debitor` != 1 AND `mvm`.`e_mail_1` LIKE '%@%' THEN 1
                                                WHEN `cus`.`unabhaengiger_debitor` = 1 AND `cus`.`rg_e_mail` LIKE '%@%' THEN 1
                                                WHEN `cus`.`unabhaengiger_debitor` != 1 AND `cus`.`e_mail` LIKE '%@%' THEN 1
                                                ELSE 0
                                            END) AS `e_mail`
                                        FROM `tabSales Invoice` AS `sinv`
                                        LEFT JOIN `tabMitgliedschaft` AS `mvm` ON `sinv`.`mv_mitgliedschaft` = `mvm`.`name`
                                        LEFT JOIN `tabKunden` AS `cus` ON `sinv`.`mv_kunde` = `cus`.`name`
                                        WHERE `sinv`.`name` IN (
                                            SELECT `sales_invoice` AS `name` FROM `tabMahnung Invoices` WHERE `docstatus` != 2 AND `parent` IN (
                                                SELECT `name` FROM `tabMahnung` WHERE `mahnlauf` = '{mahnlauf}'
                                            )
                                        )""".format(mahnlauf=self.name), as_dict=True)[0].e_mail or 0
                alle = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabSales Invoice`
                                        WHERE `name` IN (
                                            SELECT `sales_invoice` AS `name` FROM `tabMahnung Invoices` WHERE `docstatus` != 2 AND `parent` IN (
                                                SELECT `name` FROM `tabMahnung` WHERE `mahnlauf` = '{mahnlauf}'
                                            )
                                        )""".format(mahnlauf=self.name), as_dict=True)[0].qty or 0
                return alle - e_mails, e_mails, alle
            else:
                e_mails = frappe.db.sql("""SELECT
                                            SUM(CASE
                                                WHEN `mvm`.`unabhaengiger_debitor` = 1 AND `mvm`.`rg_e_mail` LIKE '%@%' THEN 1
                                                WHEN `mvm`.`unabhaengiger_debitor` != 1 AND `mvm`.`e_mail_1` LIKE '%@%' THEN 1
                                                WHEN `cus`.`unabhaengiger_debitor` = 1 AND `cus`.`rg_e_mail` LIKE '%@%' THEN 1
                                                WHEN `cus`.`unabhaengiger_debitor` != 1 AND `cus`.`e_mail` LIKE '%@%' THEN 1
                                                ELSE 0
                                            END) AS `e_mail`
                                        FROM `tabSales Invoice` AS `sinv`
                                        LEFT JOIN `tabMitgliedschaft` AS `mvm` ON `sinv`.`mv_mitgliedschaft` = `mvm`.`name`
                                        LEFT JOIN `tabKunden` AS `cus` ON `sinv`.`mv_kunde` = `cus`.`name`
                                        WHERE `sinv`.`name` IN (
                                            SELECT `sales_invoice` AS `name` FROM `tabMahnung Invoices` WHERE `docstatus` != 2 AND `parent` IN (
                                                SELECT `name` FROM `tabMahnung` WHERE `mahnlauf` = '{mahnlauf}'
                                            )
                                        )""".format(mahnlauf=self.name), as_dict=True)[0].e_mail or 0
                return 0, e_mails, e_mails
    
    def get_invoices(self):
        if self.typ == 'Produkte / Dienstleistungen':
            rg_typ_filter = """AND `sinv`.`ist_sonstige_rechnung` = 1"""
        elif self.typ == 'Mitgliedschaft (Jahresrechnung)':
            rg_typ_filter = """
                            AND `sinv`.`ist_mitgliedschaftsrechnung` = 1 
                            AND `mvm`.`status_c` NOT IN ('Anmeldung', 'Online-Anmeldung')
                            """
        elif self.typ == 'Anmeldungen':
            rg_typ_filter = """
                            AND `sinv`.`ist_mitgliedschaftsrechnung` = 1 
                            AND `mvm`.`status_c` IN ('Anmeldung', 'Online-Anmeldung')
                            """
        else:
            frappe.throw("Unbekannter Mahnlauf Typ")
        
        sinvs = frappe.db.sql("""SELECT
                                    `sinv`.`name`,
                                    `sinv`.`payment_reminder_level`,
                                    `sinv`.`grand_total`,
                                    `sinv`.`outstanding_amount`,
                                    `sinv`.`posting_date`,
                                    `sinv`.`due_date`,
                                    `sinv`.`ist_mitgliedschaftsrechnung`,
                                    `sinv`.`mitgliedschafts_jahr`,
                                    `sinv`.`currency`,
                                    `sinv`.`mv_mitgliedschaft`,
                                    `sinv`.`customer`,
                                    `sinv`.`company`,
                                    `sinv`.`mv_kunde`
                                FROM `tabSales Invoice` AS `sinv`
                                LEFT JOIN `tabMitgliedschaft` AS `mvm` ON `sinv`.`mv_mitgliedschaft` = `mvm`.`name`
                                WHERE `sinv`.`sektion_id` = '{sektion_id}'
                                AND `sinv`.`docstatus` = 1
                                AND `sinv`.`status` != 'Paid'
                                AND `sinv`.`due_date` <= '{ueberfaellig_seit}'
                                {rg_typ_filter}
                                AND `sinv`.`payment_reminder_level` = {mahnstufe}
                                AND ((`sinv`.`exclude_from_payment_reminder_until` IS NULL) OR (`sinv`.`exclude_from_payment_reminder_until` < CURDATE()))""".format(sektion_id=self.sektion_id, \
                                ueberfaellig_seit=self.ueberfaellig_seit, mahnstufe=int(self.mahnstufe) - 1, rg_typ_filter=rg_typ_filter), as_dict=True)
        
        if len(sinvs) > 0:
            for invoice in sinvs:
                now = datetime.now()
                invoices = []
                mitgliedschaften = []
                highest_level = 0
                total_before_charges = 0
                currency = None
                if not int(self.zahlungserinnerungen) == 1:
                    level = invoice.payment_reminder_level + 1
                else:
                    level = 0
                new_invoice = { 
                    'sales_invoice': invoice.name,
                    'amount': invoice.grand_total,
                    'outstanding_amount': invoice.outstanding_amount,
                    'posting_date': invoice.posting_date,
                    'due_date': invoice.due_date,
                    'reminder_level': level,
                    'ist_mitgliedschaftsrechnung': invoice.ist_mitgliedschaftsrechnung,
                    'mitgliedschafts_jahr': invoice.mitgliedschafts_jahr
                }
                if level > highest_level:
                    highest_level = level
                total_before_charges += invoice.outstanding_amount
                invoices.append(new_invoice)
                currency = invoice.currency
                # find reminder charge
                charge_matches = frappe.get_all("ERPNextSwiss Settings Payment Reminder Charge", 
                    filters={ 'reminder_level': highest_level },
                    fields=['reminder_charge'])
                reminder_charge = 0
                if charge_matches:
                    reminder_charge = charge_matches[0]['reminder_charge']
                if self.mahnungen_per_mail == 'Ja':
                    mahnungen_per_mail = frappe.db.sql("""SELECT
                                                SUM(CASE
                                                    WHEN `mvm`.`unabhaengiger_debitor` = 1 AND `mvm`.`rg_e_mail` LIKE '%@%' THEN 1
                                                    WHEN `mvm`.`unabhaengiger_debitor` != 1 AND `mvm`.`e_mail_1` LIKE '%@%' THEN 1
                                                    WHEN `cus`.`unabhaengiger_debitor` = 1 AND `cus`.`rg_e_mail` LIKE '%@%' THEN 1
                                                    WHEN `cus`.`unabhaengiger_debitor` != 1 AND `cus`.`e_mail` LIKE '%@%' THEN 1
                                                    ELSE 0
                                                END) AS `e_mail`
                                            FROM `tabSales Invoice` AS `sinv`
                                            LEFT JOIN `tabMitgliedschaft` AS `mvm` ON `sinv`.`mv_mitgliedschaft` = `mvm`.`name`
                                            LEFT JOIN `tabKunden` AS `cus` ON `sinv`.`mv_kunde` = `cus`.`name`
                                            WHERE `sinv`.`name` = '{0}'""".format(invoice.name), as_dict=True)[0].e_mail or 0
                else:
                    mahnungen_per_mail = 0
                
                create_reminder_record_check = True
                
                if int(self.zahlungserinnerungen) == 1 and mahnungen_per_mail == 0:
                    create_reminder_record_check = False
                
                if create_reminder_record_check:
                    new_reminder = frappe.get_doc({
                        "doctype": "Mahnung",
                        "sektion_id": self.sektion_id,
                        "customer": invoice.customer,
                        "mahnlauf": self.name,
                        "per_mail": mahnungen_per_mail,
                        "zahlungserinnerung": self.zahlungserinnerungen,
                        "mv_mitgliedschaft": invoice.mv_mitgliedschaft,
                        "mv_kunde": invoice.mv_kunde,
                        "date": "{year:04d}-{month:02d}-{day:02d}".format(
                            year=now.year, month=now.month, day=now.day),
                        "title": "{customer} {year:04d}-{month:02d}-{day:02d}".format(
                            customer=invoice.customer, year=now.year, month=now.month, day=now.day),
                        "sales_invoices": invoices,
                        'highest_level': highest_level,
                        'total_before_charge': total_before_charges,
                        'reminder_charge': reminder_charge,
                        'total_with_charge': (total_before_charges + reminder_charge),
                        'company': invoice.company,
                        'currency': currency,
                        'druckvorlage': self.druckvorlage,
                        'status_c': frappe.get_value("Mitgliedschaft", invoice.mv_mitgliedschaft, "status_c") if invoice.mv_mitgliedschaft else None
                    })
                    reminder_record = new_reminder.insert(ignore_permissions=True)
                    frappe.db.commit()

@frappe.whitelist()
def bulk_submit(mahnlauf):
    args = {
        'mahnlauf': mahnlauf
    }
    enqueue("mvd.mvd.doctype.mahnlauf.mahnlauf.bg_bulk_submit", queue='long', job_name='Mahnlauf {0} (Submit)'.format(mahnlauf), timeout=5000, **args)
    return

def bg_bulk_submit(mahnlauf):
    mahnungen = frappe.db.sql("""SELECT `name` FROM `tabMahnung` WHERE `mahnlauf` = '{mahnlauf}' AND `docstatus` = 0""".format(mahnlauf=mahnlauf), as_dict=True)
    for mahnung in mahnungen:
        mahnung = frappe.get_doc("Mahnung", mahnung.name)
        mahnung.update_reminder_levels()
        mahnung.submit()
    return

@frappe.whitelist()
def bulk_cancel(mahnlauf):
    args = {
        'mahnlauf': mahnlauf
    }
    enqueue("mvd.mvd.doctype.mahnlauf.mahnlauf.bg_bulk_cancel", queue='long', job_name='Mahnlauf {0} (Cancel)'.format(mahnlauf), timeout=5000, **args)
    return

@frappe.whitelist()
def bg_bulk_cancel(mahnlauf):
    mahnungen = frappe.db.sql("""SELECT `name` FROM `tabMahnung` WHERE `mahnlauf` = '{mahnlauf}' AND `docstatus` = 1""".format(mahnlauf=mahnlauf), as_dict=True)
    for mahnung in mahnungen:
        mahnung = frappe.get_doc("Mahnung", mahnung.name)
        mahnung.reset_reminder_levels()
        mahnung.cancel()
    return

@frappe.whitelist()
def bulk_delete(mahnlauf):
    args = {
        'mahnlauf': mahnlauf
    }
    enqueue("mvd.mvd.doctype.mahnlauf.mahnlauf.bg_bulk_delete", queue='long', job_name='Mahnlauf {0} (Delete)'.format(mahnlauf), timeout=5000, **args)
    return

def bg_bulk_delete(mahnlauf):
    mahnungen = frappe.db.sql("""SELECT `name` FROM `tabMahnung` WHERE `mahnlauf` = '{mahnlauf}' AND `docstatus` = 0""".format(mahnlauf=mahnlauf), as_dict=True)
    for mahnung in mahnungen:
        mahnung = frappe.get_doc("Mahnung", mahnung.name)
        mahnung.delete()
    return

@frappe.whitelist()
def mahnung_massenlauf(mahnlauf):
    args = {
        'mahnlauf': mahnlauf
    }
    enqueue("mvd.mvd.doctype.mahnlauf.mahnlauf.bg_mahnung_massenlauf", queue='long', job_name='Mahnlauf {0} (Vorber. Massenlauf)'.format(mahnlauf), timeout=5000, **args)
    return

def bg_mahnung_massenlauf(mahnlauf):
    mahnungen = frappe.get_list('Mahnung', filters={'massenlauf': 1, 'docstatus': 1, 'mahnlauf': mahnlauf, 'per_mail': ['!=',1] }, fields=['name'])
    if len(mahnungen) > 0:
        massenlauf = frappe.get_doc({
            "doctype": "Massenlauf",
            "sektion_id": frappe.get_value("Mahnlauf", mahnlauf, "sektion_id"),
            "status": "Offen",
            "typ": "Mahnung"
        })
        massenlauf.insert(ignore_permissions=True)
        
        for mahnung in mahnungen:
            m = frappe.get_doc("Mahnung", mahnung['name'])
            m.massenlauf = '0'
            m.massenlauf_referenz = massenlauf.name
            m.save(ignore_permissions=True)
        
        frappe.set_value("Mahnlauf", mahnlauf, "massenlauf", massenlauf.name)
        return
    else:
        frappe.throw("Es gibt keine Mahnungen die für einen Massenlauf vorgemerkt sind.")

@frappe.whitelist()
def is_mahnungs_job_running(jobname):
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

@frappe.whitelist()
def get_e_mail_field_list(e_mail_vorlage=None):
    if e_mail_vorlage:
        druckvorlage = frappe.get_doc("Druckvorlage", e_mail_vorlage)
        fields_list = [
            {'fieldname': 'betreff', 'label': 'Betreff', 'fieldtype': 'Data', 'reqd': 1, 'default': druckvorlage.e_mail_betreff},
            {'fieldname': 'message', 'label': 'Nachricht', 'fieldtype': 'Text Editor', 'reqd': 1, 'default': druckvorlage.e_mail_text}
        ]
    else:
        fields_list = [
            {'fieldname': 'betreff', 'label': 'Betreff', 'fieldtype': 'Data', 'reqd': 1},
            {'fieldname': 'message', 'label': 'Nachricht', 'fieldtype': 'Text Editor', 'reqd': 1}
        ]
    return fields_list

@frappe.whitelist()
def send_reminder_mails(mahnlauf=None, betreff=None, message=None, email_vorlage=None):
    mahnungen = frappe.db.sql("""SELECT `name` FROM `tabMahnung` WHERE `mahnlauf` = '{mahnlauf}' AND `docstatus` = 1 AND `per_mail` = 1""".format(mahnlauf=mahnlauf), as_dict=True)
    mahnungen_tbl = []
    for mahnung in mahnungen:
        if not int(frappe.get_value('MVD Settings', 'MVD Settings', 'email_queue')) == 1:
            mahnung = frappe.get_doc("Mahnung", mahnung.name)
            if email_vorlage:
                if mahnung.mv_mitgliedschaft:
                    mitgliedschaft = mahnung.mv_mitgliedschaft
                else:
                    mitgliedschaft = mahnung.mv_kunde
                email_vorlage = frappe.get_doc("Druckvorlage", email_vorlage)
                betreff = replace_mv_keywords(email_vorlage.e_mail_betreff, mitgliedschaft, mahnung=mahnung.name, idx=0, sinv=mahnung.sales_invoices[0].sales_invoice)
                message = replace_mv_keywords(email_vorlage.e_mail_text, mitgliedschaft, mahnung=mahnung.name, idx=0, sinv=mahnung.sales_invoices[0].sales_invoice)
            attachments = [frappe.attach_print("Mahnung", mahnung.name, file_name=mahnung.name, print_format='Mahnung')]
            comm = make(
                recipients=get_recipients(mahnung),
                sender=frappe.get_value("Sektion", mahnung.sektion_id, "mahnung_absender_adresse"),
                subject=betreff,
                content=message,
                doctype='Mahnung',
                name=mahnung.name,
                attachments=attachments,
                send_email=False,
                sender_full_name=frappe.get_value("Sektion", mahnung.sektion_id, "mahnung_absender_name")
            )["name"]
            
            sendmail(
                recipients=get_recipients(mahnung),
                sender="{0} <{1}>".format(frappe.get_value("Sektion", mahnung.sektion_id, "mahnung_absender_name"), frappe.get_value("Sektion", mahnung.sektion_id, "mahnung_absender_adresse")),
                subject=betreff,
                message=message,
                as_markdown=False,
                delayed=True,
                reference_doctype='Mahnung',
                reference_name=mahnung.name,
                unsubscribe_method=None,
                unsubscribe_params=None,
                unsubscribe_message=None,
                attachments=attachments,
                content=None,
                doctype='Mahnung',
                name=mahnung.name,
                reply_to=frappe.get_value("Sektion", mahnung.sektion_id, "mahnung_absender_adresse"),
                cc=[],
                bcc=[],
                message_id=frappe.get_value("Communication", comm, "message_id"),
                in_reply_to=None,
                send_after=None,
                expose_recipients=None,
                send_priority=1,
                communication=comm,
                retry=1,
                now=None,
                read_receipt=None,
                is_notification=False,
                inline_images=None,
                template='mahnung',
                args={
                    "message": message,
                    "footer": frappe.get_value("Sektion", mahnung.sektion_id, "footer")
                },
                header=None,
                print_letterhead=False
            )
        else:
            mahnungen_tbl.append({
                'mahnung': mahnung.name,
                'status': 'Not send'
            })
        
    if int(frappe.get_value('MVD Settings', 'MVD Settings', 'email_queue')) == 1:
        new_queue = frappe.get_doc({
            'doctype': 'MVD Email Queue',
            'status': 'Not send',
            'mahnlauf': mahnlauf,
            'betreff': betreff,
            'email_vorlage': email_vorlage,
            'message': message,
            'mahnungen': mahnungen_tbl
        }).insert()
        
    frappe.set_value("Mahnlauf", mahnlauf, "e_mails_versendet", 1)
    return

def get_recipients(mahnung):
    if mahnung.mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mahnung.mv_mitgliedschaft)
        if mitgliedschaft.abweichende_rechnungsadresse and mitgliedschaft.unabhaengiger_debitor and mitgliedschaft.rg_e_mail:
            return [mitgliedschaft.rg_e_mail]
        else:
            return [mitgliedschaft.e_mail_1]
    else:
        kunde = frappe.get_doc("Kunden", mahnung.mv_kunde)
        if kunde.abweichende_rechnungsadresse and kunde.unabhaengiger_debitor and kunde.rg_e_mail:
            return [kunde.rg_e_mail]
        else:
            return [kunde.e_mail]
