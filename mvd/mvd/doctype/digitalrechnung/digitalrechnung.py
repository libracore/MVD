# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint
from frappe.utils.data import today
import hashlib

class Digitalrechnung(Document):
    def validate(self):
        if not self.hash:
            self.generate_hash()
    
    def after_insert(self):
        frappe.db.set_value("Mitgliedschaft", self.mitglied_id, "digitalrechnung_hash", self.hash)
    
    def generate_hash(self):
        txt = "{0}{1}".format(self.mitglied_id, self.mitglied_nr)
        
        # Create a SHA-256 hash
        hash_object = hashlib.sha256(txt.encode())
        full_hash = hash_object.hexdigest()
        
        # Truncate to the last 10 characters
        truncated_hash = full_hash[:10]
        
        self.hash = truncated_hash
    
    def set_opt_in(self):
        self.opt_in = today()
        self.opt_out = None
    
    def set_opt_out(self):
        self.opt_out = today()
        self.opt_in = None
        self.no_auto_opt_in = 1
    
    def set_email(self, email):
        self.email = email
        self.set_opt_in()

def initial_setup():
    mitgliedschaften = frappe.db.sql("""
        SELECT
            `name` AS `mitglied_id`,
            `mitglied_nr`,
            `sektion_id`,
            `e_mail_1` AS `mitgl_email`,
            `abweichende_rechnungsadresse` AS `abw_rg_adr`,
            `unabhaengiger_debitor` AS `unabh_deb`,
            `rg_e_mail` AS `rg_email`,
            `digitalrechnung_hash`
        FROM `tabMitgliedschaft`
        WHERE `status_c` NOT IN ('Inaktiv', 'Anmeldung', 'Online-Anmeldung', 'Gestorben', 'Wegzug', 'Ausschluss', 'Interessent*in')
    """, as_dict=True)

    total = len(mitgliedschaften)
    loop = 1
    submit_count = 1

    for mitgliedschaft in mitgliedschaften:
        print("{0} von {1}".format(loop, total))
        if not mitgliedschaft.digitalrechnung_hash:
            new_digitalrechnung = frappe.get_doc({
                'doctype': "Digitalrechnung",
                'mitglied_nr': mitgliedschaft.mitglied_nr,
                'mitglied_id': mitgliedschaft.mitglied_id,
                'sektion_id': mitgliedschaft.sektion_id,
                'email': mitgliedschaft.mitgl_email
            })

            if cint(mitgliedschaft.abw_rg_adr) == 1 and cint(mitgliedschaft.unabh_deb) == 1:
                new_digitalrechnung.email = None
                if mitgliedschaft.rg_email:
                    new_digitalrechnung.email = mitgliedschaft.rg_email
            
            new_digitalrechnung.insert()
        
        loop += 1
        submit_count += 1
        if submit_count == 100:
            frappe.db.commit()
            submit_count = 1
    frappe.db.commit()


