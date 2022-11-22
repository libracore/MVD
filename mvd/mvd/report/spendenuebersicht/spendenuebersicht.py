# Copyright (c) 2013, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return[
        {"label": _("Mitglied"), "fieldname": "mitglied_id", "fieldtype": "Link", "options": "Mitgliedschaft"},
        {"label": _("Mitglied Nr"), "fieldname": "mitglied_nr", "fieldtype": "Data"},
        {"label": _("Sektion"), "fieldname": "sektion_id", "fieldtype": "Data"},
        {"label": _("Anrede"), "fieldname": "anrede", "fieldtype": "Data"},
        {"label": _("Vorname"), "fieldname": "vorname", "fieldtype": "Data"},
        {"label": _("Nachname"), "fieldname": "nachname", "fieldtype": "Data"},
        {"label": _("Adressblock"), "fieldname": "adressblock", "fieldtype": "Code"},
        {"label": _("Spendenversand"), "fieldname": "spendenversand", "fieldtype": "Link", "options": "Spendenversand"},
        {"label": _("Fakultative Rechnung"), "fieldname": "fakultative_rechnung", "fieldtype": "Link", "options": "Fakultative Rechnung"},
        {"label": _("Rechnung"), "fieldname": "sales_invoice", "fieldtype": "Link", "options": "Sales Invoice"},
        {"label": _("Betrag"), "fieldname": "amount", "fieldtype": "Currency"}
    ]

def get_data(filters):
    data = []
    
    if filters.grundlage == 'Spendenversand' and not filters.spendenversand:
        return data
    
    if filters.grundlage == 'Sektionsspezifisch' and not filters.sektion_id:
        return data
    
    if filters.grundlage == 'Spendenversand':
        data = frappe.db.sql("""SELECT
                                    `fak`.`mv_mitgliedschaft` AS `mitglied_id`,
                                    `mvm`.`mitglied_nr` AS `mitglied_nr`,
                                    `fak`.`sektion_id` AS `sektion_id`,
                                    `fak`.`name` AS `fakultative_rechnung`,
                                    `fak`.`bezahlt_via` AS `sales_invoice`,
                                    `sinv`.`grand_total` AS `amount`,
                                    `fak`.`spenden_versand` AS `spendenversand`,
                                    `mvm`.`anrede_c` AS `anrede`,
                                    `mvm`.`vorname_1` AS `vorname`,
                                    `mvm`.`nachname_1` AS `nachname`,
                                    `mvm`.`rg_adressblock` AS `adressblock`
                                FROM `tabFakultative Rechnung` AS `fak`
                                LEFT JOIN `tabMitgliedschaft` AS `mvm` ON `fak`.`mv_mitgliedschaft` = `mvm`.`name`
                                LEFT JOIN `tabSales Invoice` AS `sinv` ON `fak`.`bezahlt_via` = `sinv`.`name`
                                WHERE `fak`.`status` = 'Paid'
                                AND `fak`.`spenden_versand` = '{spendenversand}'""".format(spendenversand=filters.spendenversand), as_dict=True)
        return data
    
    if filters.grundlage == 'Sektionsspezifisch':
        data = frappe.db.sql("""SELECT
                                    `fak`.`mv_mitgliedschaft` AS `mitglied_id`,
                                    `mvm`.`mitglied_nr` AS `mitglied_nr`,
                                    `fak`.`sektion_id` AS `sektion_id`,
                                    `fak`.`name` AS `fakultative_rechnung`,
                                    `fak`.`bezahlt_via` AS `sales_invoice`,
                                    `sinv`.`grand_total` AS `amount`,
                                    `fak`.`spenden_versand` AS `spendenversand`,
                                    `mvm`.`anrede_c` AS `anrede`,
                                    `mvm`.`vorname_1` AS `vorname`,
                                    `mvm`.`nachname_1` AS `nachname`,
                                    `mvm`.`rg_adressblock` AS `adressblock`
                                FROM `tabFakultative Rechnung` AS `fak`
                                LEFT JOIN `tabMitgliedschaft` AS `mvm` ON `fak`.`mv_mitgliedschaft` = `mvm`.`name`
                                LEFT JOIN `tabSales Invoice` AS `sinv` ON `fak`.`bezahlt_via` = `sinv`.`name`
                                WHERE `fak`.`status` = 'Paid'
				AND `fak`.`typ` IN ('Spende','Spende (Spendenversand)')
                                AND `fak`.`sektion_id` = '{sektion_id}'""".format(sektion_id=filters.sektion_id), as_dict=True)
        return data
    
    if filters.grundlage == 'Alles':
        frappe.only_for(["System Manager"])
        data = frappe.db.sql("""SELECT
                                    `fak`.`mv_mitgliedschaft` AS `mitglied_id`,
                                    `mvm`.`mitglied_nr` AS `mitglied_nr`,
                                    `fak`.`sektion_id` AS `sektion_id`,
                                    `fak`.`name` AS `fakultative_rechnung`,
                                    `fak`.`bezahlt_via` AS `sales_invoice`,
                                    `sinv`.`grand_total` AS `amount`,
                                    `fak`.`spenden_versand` AS `spendenversand`,
                                    `mvm`.`anrede_c` AS `anrede`,
                                    `mvm`.`vorname_1` AS `vorname`,
                                    `mvm`.`nachname_1` AS `nachname`,
                                    `mvm`.`rg_adressblock` AS `adressblock`
                                FROM `tabFakultative Rechnung` AS `fak`
                                LEFT JOIN `tabMitgliedschaft` AS `mvm` ON `fak`.`mv_mitgliedschaft` = `mvm`.`name`
                                LEFT JOIN `tabSales Invoice` AS `sinv` ON `fak`.`bezahlt_via` = `sinv`.`name`
                                WHERE `fak`.`status` = 'Paid'
				AND `fak`.`typ` IN ('Spende','Spende (Spendenversand)')""", as_dict=True)
        return data
        
