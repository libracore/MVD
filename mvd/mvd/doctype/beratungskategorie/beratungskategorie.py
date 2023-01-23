# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Beratungskategorie(Document):
    def set_new_name(self):
        self.titel = self.get_name()
    
    def after_rename(self, olddn, newdn, merge=False):
        if ' - ' in newdn:
            code = newdn.split(" - ")[0]
            kategorie = newdn.replace(code + " - ", "")
            frappe.db.set(self, "code", code)
            frappe.db.set(self, "kategorie", kategorie)
        else:
            frappe.db.set(self, "code", None)
            frappe.db.set(self, "kategorie", newdn)

    def get_name(self):
        if self.code:
            titel = self.code + " - " + self.kategorie
        else:
            titel = self.kategorie
        return titel
