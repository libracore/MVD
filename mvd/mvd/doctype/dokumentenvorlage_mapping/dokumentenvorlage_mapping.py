# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class DokumentenvorlageMapping(Document):
    def validate(self):
        for mapping in self.mapping_tbl:
            if mapping.replace_with == 'Feld':
                mapping.function = None
                if not mapping.field: frappe.throw('Bitte erfassen sie "Feld" in Zeile {idx}'.format(idx=mapping.idx))
            if mapping.replace_with == 'Funktion':
                mapping.field = None
                
                if mapping.function == 'Mail-In DMC':
                    mapping.platzhalter = 'dmc_platzhalter'
                
                if not mapping.function: frappe.throw('Bitte erfassen sie "Funktion" in Zeile {idx}'.format(idx=mapping.idx))
        return
