# Copyright (c) 2013, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns, data = get_columns(), get_data(filters)
    return columns, data

def get_columns():
    return[
        {"label": _("Beratungskategorie"), "fieldname": "beratungskategorie", "fieldtype": "Link", "options": "Beratungskategorie"},
        {"label": _("Ist Unterkategorie"), "fieldname": "unterkategorie", "fieldtype": "Check"},
        {"label": _("Anzahl Geschlossen"), "fieldname": "closed", "fieldtype": "Int"}
    ]

def get_data(filters):
    data = []
    closed_as_main = frappe.db.sql("""
                                        SELECT
                                            COUNT(`name`) AS `qty`,
                                            `beratungskategorie`
                                        FROM `tabBeratung`
                                        WHERE `status` = 'Closed'
                                        AND `geschlossen_am` >= '{from_filter}'
                                        AND `geschlossen_am` <= '{to_filter}'
                                        GROUP BY `beratungskategorie`""".format(from_filter=filters.from_date, to_filter=filters.to), as_dict=True)
    
    for cam in closed_as_main:
        data.append({
            'beratungskategorie': cam.beratungskategorie,
            'closed': cam.qty
        })
    
    return data
