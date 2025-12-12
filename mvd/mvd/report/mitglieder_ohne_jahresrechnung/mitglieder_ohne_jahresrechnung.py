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
        {"label": _("Bezahltes Mitgliedschaftsjahr"), "fieldname": "paid_mitgliedschaftsjahr", "fieldtype": "Int"}
    ]

def get_data(filters):
    data = frappe.db.sql("""
        SELECT
            `name` AS `mitglied_id`,
            `mitglied_nr`,
            `mitgliedtyp_c`,
            CONCAT_WS(' ', `vorname_1`, `nachname_1`) AS `mitglied_name`,
            `status_c` AS `mitglied_status`,
            `bezahltes_mitgliedschaftsjahr` AS `paid_mitgliedschaftsjahr`
        FROM `tabMitgliedschaft`
        WHERE `bezahltes_mitgliedschaftsjahr` < '{0}'
        AND `sektion_id` = '{1}'
        AND `status_c` IN ('Regulär', 'Zuzug', 'Online-Mutation')
        AND (
            `kuendigung` IS NULL
            OR
            `kuendigung` > '{0}-01-01'
        )
        AND `name` NOT IN (
            SELECT `mv_mitgliedschaft`
            FROM `tabSales Invoice`
            WHERE `docstatus` = 1
            AND `sektion_id` = '{1}'
            AND `mitgliedschafts_jahr` = '{0}'
            AND `ist_mitgliedschaftsrechnung` = 1
        )
    """.format(filters.jahr, filters.sektion_id), as_dict=True)
    return data
