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
                    `status_c` AS `status`
                FROM `tabMitgliedschaft`
                GROUP BY `sektion_id`, `status_c`
                ORDER BY `sektion_id` ASC
            """, as_dict=True)
            
            ordered_data = {}
            for dq in data_query:
                if dq.get("sektion") in ordered_data:
                    ordered_data[dq.get("sektion")][dq.get("status")] = dq.get("qty")
                else:
                    ordered_data[dq.get("sektion")] = {}
                    ordered_data[dq.get("sektion")][dq.get("status")] = dq.get("qty")
            
            json_data = json.dumps(ordered_data, indent=2)
            self.data = json_data
