# Copyright (c) 2013, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data

def get_columns():
    return[
        {"label": _("Mitglied"), "fieldname": "mitglied_nr", "fieldtype": "Data", "width": 130},
        {"label": _("ID"), "fieldname": "mitglied_id", "fieldtype": "Link", "options": "Mitgliedschaft", "width":100},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data"},
        {"label": _("Sektion"), "fieldname": "sektion", "fieldtype": "Data"},
        {"label": _("Wegzug zu"), "fieldname": "wegzug_zu", "fieldtype": "Data"},
        {"label": _("Wegzug"), "fieldname": "wegzug", "fieldtype": "Date"},
        {"label": _("Zuzug von"), "fieldname": "zuzug_von", "fieldtype": "Data"},
        {"label": _("Zuzug"), "fieldname": "zuzug", "fieldtype": "Date"},
        {"label": _("Zuletzt Bearbeitet"), "fieldname": "modified", "fieldtype": "Datetime"}

    ]

def get_data():
    data = frappe.db.sql("""SELECT
                                `tbl_a`.`mitglied_nr`,
                                `tbl_a`.`name` AS `mitglied_id`,
                                `tbl_a`.`status_c` AS `status`,
                                `tbl_a`.`sektion_id` AS `sektion`,
                                `tbl_a`.`wegzug_zu` AS `wegzug_zu`,
                                `tbl_a`.`wegzug` AS `wegzug`,
                                `tbl_a`.`zuzug_von` AS `zuzug_von`,
                                `tbl_a`.`zuzug` AS `zuzug`,
                                `tbl_a`.`modified` AS `modified`
                            FROM `tabMitgliedschaft` AS `tbl_a`
                            INNER JOIN (
                                SELECT
                                    `mitglied_nr`
                                FROM `tabMitgliedschaft`
                                WHERE `status_c` NOT IN ('Interessent*in', 'Inaktiv')
                                GROUP BY `mitglied_nr`
                                HAVING COUNT(`name`) > 1
                            ) AS `tbl_b` ON `tbl_b`.`mitglied_nr` = `tbl_a`.`mitglied_nr`
                            WHERE `tbl_a`.`status_c` NOT IN ('Interessent*in', 'Inaktiv')
                            ORDER BY `tbl_a`.`mitglied_nr` ASC""", as_dict=True)
    return data
