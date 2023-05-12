# Copyright (c) 2013, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.data import get_datetime

def execute(filters=None):
    columns, data = get_columns(), get_data(filters)
    return columns, data

def get_columns():
    return[
        {"label": _("User"), "fieldname": "user", "fieldtype": "Data", "width": 160},
        {"label": _("Sektion"), "fieldname": "sektion", "fieldtype": "Data", "width": 160},
        {"label": _("Mitgliedname"), "fieldname": "mitgliedname", "fieldtype": "Data", "width": 160},
        {"label": _("Thema"), "fieldname": "thema", "fieldtype": "Data", "width": 160},
        {"label": _("Beratung"), "fieldname": "beratung", "fieldtype": "Link", "options": "Beratung", "width": 160}
    ]

def get_data(filters):
    if filters.sektion:
        beratungen = frappe.db.sql("""
                                    SELECT
                                        `kontaktperson` AS `user`,
                                        `sektion_id` AS `sektion`,
                                        `mitgliedname` AS `mitgliedname`,
                                        `subject` AS `thema`,
                                        `name` AS `beratung`
                                    FROM `tabBeratung`
                                    WHERE `sektion_id` = '{sektion}'
                                    """.format(sektion=filters.sektion), as_dict=True)
        
        return beratungen
    else:
        return []
