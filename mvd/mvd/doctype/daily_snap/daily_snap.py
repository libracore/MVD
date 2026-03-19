# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json

class DailySnap(Document):
    def validate(self):
        if not self.data:
            data_query = frappe.db.sql("""
                SELECT
                    COUNT(`name`) AS `qty`,
                    `sektion_id` AS `sektion`,
                    `status_c` AS `status`,
                    `kundentyp` AS `typ`
                FROM `tabMitgliedschaft`
                GROUP BY `sektion_id`, `status_c`, `kundentyp`
                ORDER BY `sektion_id` ASC
            """, as_dict=True)
            
            ordered_data = {}
            
            for dq in data_query:
                sektion = dq.get("sektion")
                status = dq.get("status")
                typ = dq.get("typ")
                qty = dq.get("qty")

                if sektion not in ordered_data:
                    ordered_data[sektion] = {}
                
                if status not in ordered_data[sektion]:
                    ordered_data[sektion][status] = {}
                
                ordered_data[sektion][status][typ] = qty
            
            self.data = json.dumps(ordered_data, indent=2)