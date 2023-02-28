# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Sektion(Document):
    def validate(self):
        if self.legacy_mode != '0':
            if not self.legacy_email:
                frappe.throw("Bitte hinterlegen Sie eine Sektionsspezifische E-Mail Adresse für den E-Mail Beratung Legacy Mode")
