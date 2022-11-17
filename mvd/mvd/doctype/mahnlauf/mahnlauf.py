# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import add_to_date, nowdate
from datetime import datetime

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
        # ~ self.anzahl_pdf, self.anzahl_mail = self.get_anzahl()
    
    def on_submit(self):
        if self.typ == 'Produkte / Dienstleistungen':
            self.get_invoices_sonstiges()
    
    def get_anzahl(self):
        if self.typ == 'Produkte / Dienstleistungen':
            if self.is_new() or (self.entwurfs_mahnungen + self.gebuchte_mahnungen + self.stornierte_mahnungen) == 0:
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
                                        AND `sinv`.`ist_sonstige_rechnung` = 1
                                        AND `sinv`.`payment_reminder_level` = {mahnstufe}
                                        AND ((`sinv`.`exclude_from_payment_reminder_until` IS NULL) OR (`sinv`.`exclude_from_payment_reminder_until` < CURDATE()))""".format(sektion_id=self.sektion_id, \
                                        ueberfaellig_seit=self.ueberfaellig_seit, mahnstufe=int(self.mahnstufe) - 1), as_dict=True)[0].e_mail or 0
                alle = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabSales Invoice`
                                        WHERE `sektion_id` = '{sektion_id}'
                                        AND `docstatus` = 1
                                        AND `status` != 'Paid'
                                        AND `due_date` <= '{ueberfaellig_seit}'
                                        AND `ist_sonstige_rechnung` = 1
                                        AND `payment_reminder_level` = {mahnstufe}
                                        AND ((`exclude_from_payment_reminder_until` IS NULL) OR (`exclude_from_payment_reminder_until` < CURDATE()))""".format(sektion_id=self.sektion_id, \
                                        ueberfaellig_seit=self.ueberfaellig_seit, mahnstufe=int(self.mahnstufe) - 1), as_dict=True)[0].qty or 0
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
                alle = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabSales Invoice`
                                        WHERE `name` IN (
                                            SELECT `sales_invoice` AS `name` FROM `tabMahnung Invoices` WHERE `docstatus` != 2 AND `parent` IN (
                                                SELECT `name` FROM `tabMahnung` WHERE `mahnlauf` = '{mahnlauf}'
                                            )
                                        )""".format(mahnlauf=self.name), as_dict=True)[0].qty or 0
                return alle - e_mails, e_mails, alle
    
    def get_invoices_sonstiges(self):
        sinvs = frappe.db.sql("""SELECT
                                    `name`,
                                    `payment_reminder_level`,
                                    `grand_total`,
                                    `outstanding_amount`,
                                    `posting_date`,
                                    `due_date`,
                                    `ist_mitgliedschaftsrechnung`,
                                    `mitgliedschafts_jahr`,
                                    `currency`,
                                    `mv_mitgliedschaft`,
                                    `customer`,
                                    `company`,
                                    `mv_kunde`
                                FROM `tabSales Invoice`
                                WHERE `sektion_id` = '{sektion_id}'
                                AND `docstatus` = 1
                                AND `status` != 'Paid'
                                AND `due_date` <= '{ueberfaellig_seit}'
                                AND `ist_sonstige_rechnung` = 1
                                AND `payment_reminder_level` = {mahnstufe}
                                AND ((`exclude_from_payment_reminder_until` IS NULL) OR (`exclude_from_payment_reminder_until` < CURDATE()))""".format(sektion_id=self.sektion_id, \
                                ueberfaellig_seit=self.ueberfaellig_seit, mahnstufe=int(self.mahnstufe) - 1), as_dict=True)
        
        if len(sinvs) > 0:
            for invoice in sinvs:
                now = datetime.now()
                invoices = []
                mitgliedschaften = []
                highest_level = 0
                total_before_charges = 0
                currency = None
                level = invoice.payment_reminder_level + 1
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
                # ~ mv_mitgliedschaft = None
                # ~ if invoice.mv_mitgliedschaft:
                    # ~ mitgliedschaften.append({
                        # ~ 'mv_mitgliedschaft': invoice.mv_mitgliedschaft
                    # ~ })
                    # ~ mv_mitgliedschaft = invoice.mv_mitgliedschaft
                # find reminder charge
                charge_matches = frappe.get_all("ERPNextSwiss Settings Payment Reminder Charge", 
                    filters={ 'reminder_level': highest_level },
                    fields=['reminder_charge'])
                reminder_charge = 0
                if charge_matches:
                    reminder_charge = charge_matches[0]['reminder_charge']
                druckvorlage = 'MVD 1. Mahnung-MVD' #get_default_druckvorlage(sektion_id, frappe.get_value("Mitgliedschaft", mitgliedschaften[0]['mv_mitgliedschaft'], "language"))
                if self.mahnungen_per_mail:
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
                new_reminder = frappe.get_doc({
                    "doctype": "Mahnung",
                    "sektion_id": self.sektion_id,
                    "customer": invoice.customer,
                    "mahnlauf": self.name,
                    "per_mail": mahnungen_per_mail,
                    "mv_mitgliedschaft": invoice.mv_mitgliedschaft,
                    "mv_kunde": invoice.mv_kunde,
                    # ~ "mitgliedschaften": mitgliedschaften,
                    # ~ "hidden_linking": mitgliedschaften,
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
                    'druckvorlage': druckvorlage,
                    'status_c': frappe.get_value("Mitgliedschaft", invoice.mv_mitgliedschaft, "status_c") if invoice.mv_mitgliedschaft else None
                })
                reminder_record = new_reminder.insert(ignore_permissions=True)
                frappe.db.commit()

@frappe.whitelist()
def bulk_submit(mahnlauf):
    mahnungen = frappe.db.sql("""SELECT `name` FROM `tabMahnung` WHERE `mahnlauf` = '{mahnlauf}' AND `docstatus` = 0""".format(mahnlauf=mahnlauf), as_dict=True)
    for mahnung in mahnungen:
        mahnung = frappe.get_doc("Mahnung", mahnung.name)
        mahnung.update_reminder_levels()
        mahnung.submit()
    return

@frappe.whitelist()
def bulk_cancel(mahnlauf):
    mahnungen = frappe.db.sql("""SELECT `name` FROM `tabMahnung` WHERE `mahnlauf` = '{mahnlauf}' AND `docstatus` = 1""".format(mahnlauf=mahnlauf), as_dict=True)
    for mahnung in mahnungen:
        mahnung = frappe.get_doc("Mahnung", mahnung.name)
        mahnung.reset_reminder_levels()
        mahnung.cancel()
    return

@frappe.whitelist()
def mahnung_massenlauf(mahnlauf):
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
        return massenlauf.name
    else:
        frappe.throw("Es gibt keine Mahnungen die für einen Massenlauf vorgemerkt sind.")
