# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint

class Addresschange(Document):
    def on_submit(self):
        if cint(self.history_only) != 1:
            self.execute_addresschange()
    
    def execute_addresschange(self):
        mitgl = frappe.get_doc("Mitgliedschaft", self.mv_mitgliedschaft)
        if cint(mitgl.abweichende_objektadresse) == 1:
            mitgl.objekt_zusatz_adresse = self.zusatz_adresse
            mitgl.objekt_strasse = self.strasse
            mitgl.objekt_hausnummer = self.nummer
            mitgl.objekt_nummer_zu = self.nummer_zu
            mitgl.objekt_plz = self.plz
            mitgl.objekt_ort = self.ort
        else:
            mitgl.zusatz_adresse = self.zusatz_adresse
            mitgl.strasse = self.strasse
            mitgl.nummer = self.nummer
            mitgl.nummer_zu = self.nummer_zu
            mitgl.plz = self.plz
            mitgl.ort = self.ort
        
        if self.owner != 'Administartor':
            if "MV_MA-unvalidiert" in frappe.get_roles(self.owner):
                mitgl.validierung_notwendig = 1
        
        mitgl.flags.from_addresschange = True
        mitgl.save(ignore_permissions=True)
