# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from frappe.utils import nowdate, getdate

class YearlySnap(Document):
    def validate(self):
        if not self.year:
            self.year = getdate().year

@frappe.whitelist()
def erstelle_mitglieder_statistik(date=None):
    if not date:
        date = nowdate()

    date_obj = getdate(date)
    year = int(date_obj.year)

    existing_snap = frappe.db.get_value("Yearly Snap", {"year": year}, "name")

    if existing_snap:
        doc = frappe.get_doc("Yearly Snap", existing_snap)
    else:
        doc = frappe.new_doc("Yearly Snap")
        doc.year = year
        doc.insert()

    stichtag_treue = f"{year - 1}-09-15"

    data_query = frappe.db.sql("""
        SELECT
            `sektion_id` AS `sektion`,
            `kundentyp` AS `typ`,
            LEAST(
                CASE 
                    WHEN `eintrittsdatum` > DATE_SUB(%(stichtag)s, INTERVAL 0 YEAR) THEN 1
                    WHEN `eintrittsdatum` > DATE_SUB(%(stichtag)s, INTERVAL 1 YEAR) THEN 2
                    WHEN `eintrittsdatum` > DATE_SUB(%(stichtag)s, INTERVAL 2 YEAR) THEN 3
                    WHEN `eintrittsdatum` > DATE_SUB(%(stichtag)s, INTERVAL 3 YEAR) THEN 4
                    ELSE 5
                END, 
            5) AS `jahre_dabei`,
            COUNT(`name`) AS `qty`
        FROM `tabMitgliedschaft`
        WHERE `status_c` = 'Regulär'
        GROUP BY `sektion_id`, `kundentyp`, `jahre_dabei`
        ORDER BY `sektion_id` ASC
    """, {"stichtag": stichtag_treue}, as_dict=True)

    ordered_data = {}
    
    for dq in data_query:
        sektion = dq.get("sektion")
        typ = dq.get("typ")
        jahre = dq.get("jahre_dabei")
        qty = dq.get("qty")
        
        if sektion not in ordered_data:
            ordered_data[sektion] = {}
            
        if typ not in ordered_data[sektion]:
            ordered_data[sektion][typ] = {}
        
        ordered_data[sektion][typ][jahre] = qty
        
    doc.mitglieder_statistik = json.dumps(ordered_data, indent=2)

    doc.save()
    frappe.db.commit()
    return doc.name

@frappe.whitelist()
def erstelle_nichtzahler_statistik(year):
    existing_snap = frappe.db.get_value("Yearly Snap", {"year": year}, "name")

    if existing_snap:
        doc = frappe.get_doc("Yearly Snap", existing_snap)
    else:
        doc = frappe.new_doc("Yearly Snap")
        doc.year = year
        doc.insert()

    data_query = frappe.db.sql("""
        SELECT 
            parent_doc.sektion_id AS sektion,
            COUNT(child_doc.name) AS qty
        FROM 
            `tabMassenlauf Inaktivierung` AS parent_doc
        JOIN 
            `tabMassenlauf Inaktivierung Mitgliedschaften` AS child_doc 
            ON child_doc.parent = parent_doc.name
        WHERE 
            parent_doc.status = 'Abgeschlossen' 
            AND parent_doc.relevantes_mitgliedschaftsjahr = %(year)s
        GROUP BY 
            parent_doc.sektion_id
            """, {"year": year}, as_dict=True)

    ordered_data = {}

    for dq in data_query:
        sektion = dq.get("sektion")
        qty = dq.get("qty")
        
        if sektion not in ordered_data:
            ordered_data[sektion] = qty
            
    doc.nicht_zahler = json.dumps(ordered_data, indent=2)
    
    doc.save()
    frappe.db.commit()
    return doc.name