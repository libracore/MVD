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
		if not self.jahr:
			self.jahr = getdate().year
			
		if not self.data:
			data_query = frappe.db.sql("""
                SELECT
                    `sektion_id` AS `sektion`,
                    `kundentyp` AS `typ`,
                    LEAST(TIMESTAMPDIFF(YEAR, `eintrittsdatum`, %(today)s), 5) AS `jahre_dabei`,
                    COUNT(`name`) AS `qty`
                FROM `tabMitgliedschaft`
                WHERE `status_c` = 'Regulär'
                GROUP BY `sektion_id`, `kundentyp`, `jahre_dabei`
                ORDER BY `sektion_id` ASC
            """, {"today": nowdate()}, as_dict=True)

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
				
			self.data = json.dumps(ordered_data, indent=2)