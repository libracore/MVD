# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Termin(Document):
    def validate(self):
        if not self.mv_mitgliedschaft:
            frappe.throw("Termine müssen immer einer Mitgliedschaft zugewiesen sein")
        self.sektion_id = frappe.get_value("Mitgliedschaft", self.mv_mitgliedschaft, "sektion_id")
