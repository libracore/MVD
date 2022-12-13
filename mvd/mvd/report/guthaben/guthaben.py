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
        {"label": _("Mitglied Name"), "fieldname": "mitglied_name", "fieldtype": "Data"},
        {"label": _("Mitglied Status"), "fieldname": "mitglied_status", "fieldtype": "Data"},
        {"label": _("Mitgliedtyp"), "fieldname": "mitgliedtyp_c", "fieldtype": "Data"},
        {"label": _("Guthaben"), "fieldname": "guthaben", "fieldtype": "Currency"}
    ]

def get_data(filters):
    company = frappe.db.get_value("Sektion", filters.sektion_id, "company")
    
    guthaben = frappe.db.sql("""
        SELECT DISTINCT
            `data`.`guthaben` AS `guthaben`,
            `data`.`party`,
            `data`.`name` AS `mitglied_id`,
            CONCAT(`data`.`vorname_1`, ' ', `data`.`nachname_1`) AS `mitglied_name`,
            `data`.`mitglied_nr` AS `mitglied_nr`,
            `data`.`status_c` AS `mitglied_status`,
            `data`.`mitgliedtyp_c` AS `mitgliedtyp_c`,
            `data`.`kunde_mitglied`,
            `data`.`rg_kunde`
        FROM (
            SELECT
                `data_tbl`.`guthaben`,
                `data_tbl`.`party`,
                `mitgl`.`name`,
                `mitgl`.`vorname_1`,
                `mitgl`.`nachname_1`,
                `mitgl`.`mitglied_nr`,
                `mitgl`.`status_c`,
                `mitgl`.`mitgliedtyp_c`,
                `mitgl`.`kunde_mitglied`,
                `mitgl`.`rg_kunde`
            FROM (
                SELECT
                    `company`,
                    ((SUM(`debit_in_account_currency`) - SUM(`credit_in_account_currency`)) * -1) AS `guthaben`,
                    `party`
                FROM `tabGL Entry`
                WHERE `party_type` = 'Customer'
                AND `company` = '{company}'
                GROUP BY `party`
            ) AS `data_tbl`
            LEFT JOIN `tabMitgliedschaft` AS `mitgl` ON `data_tbl`.`party` = `mitgl`.`kunde_mitglied`
            WHERE `data_tbl`.`guthaben` > 0
            UNION
            SELECT
                `data_tbl`.`guthaben`,
                `data_tbl`.`party`,
                `mitgl`.`name`,
                `mitgl`.`vorname_1`,
                `mitgl`.`nachname_1`,
                `mitgl`.`mitglied_nr`,
                `mitgl`.`status_c`,
                `mitgl`.`mitgliedtyp_c`,
                `mitgl`.`kunde_mitglied`,
                `mitgl`.`rg_kunde`
            FROM (
                SELECT
                    `company`,
                    ((SUM(`debit_in_account_currency`) - SUM(`credit_in_account_currency`)) * -1) AS `guthaben`,
                    `party`
                FROM `tabGL Entry`
                WHERE `party_type` = 'Customer'
                AND `company` = '{company}'
                GROUP BY `party`
            ) AS `data_tbl`
            LEFT JOIN `tabMitgliedschaft` AS `mitgl` ON `data_tbl`.`party` = `mitgl`.`rg_kunde`
            WHERE `data_tbl`.`guthaben` > 0
            AND IFNULL(`mitgl`.`rg_kunde`, '') != ''
        ) AS `data`
    """.format(company=company), as_dict=True)
    return guthaben
