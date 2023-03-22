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
        {"label": _("Von"), "fieldname": "von", "fieldtype": "Datetime"},
        {"label": _("Bis"), "fieldname": "bis", "fieldtype": "Datetime"},
        {"label": _("Ort"), "fieldname": "ort", "fieldtype": "Data"},
        {"label": _("Titel"), "fieldname": "titel", "fieldtype": "Data"},
        {"label": _("Thema"), "fieldname": "thema", "fieldtype": "Data"},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data"},
        {"label": _("Beratung"), "fieldname": "beratung", "fieldtype": "Link", "options": "Beratung"}
    ]

def get_data(filters):
    # ~ data = []
    if filters.von:
        von = """AND `bt`.`von` > '{von}'""".format(von=filters.von)
    else:
        von = ''
    
    termine = frappe.db.sql("""
                                SELECT
                                    `bt`.`von` AS `von`,
                                    `bt`.`bis` AS `bis`,
                                    `bt`.`ort` AS `ort`,
                                    `b`.`titel` AS `titel`,
                                    `b`.`status` AS `status`,
                                    `b`.`subject` AS `thema`,
                                    `b`.`name` AS `beratung`
                                FROM `tabBeratung Termin` AS `bt`
                                LEFT JOIN `tabBeratung` AS `b` on `bt`.`parent` = `b`.`name`
                                WHERE `b`.`_assign` LIKE '%{user}%'
                                {von} 
                                """.format(von=von, user=filters._assign), as_dict=True)
    
    return termine
