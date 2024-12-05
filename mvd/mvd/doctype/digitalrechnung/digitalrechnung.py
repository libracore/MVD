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
        self.status = 'Verarbeitet'
        if not self.hash:
            self.generate_hash()
        else:
            if cint(self.changed_by_sektion) != 1:
                old_opt = frappe.db.get_value("Mitgliedschaft", self.mitglied_id, "digitalrechnung")
                if self.opt_in:
                    if cint(old_opt) != 1:
                        frappe.db.set_value("Mitgliedschaft", self.mitglied_id, "digitalrechnung", 1)
                        create_mitglied_change_log(self.mitglied_id, "hat die digitale Rechnung <b>aktiviert</b>")
                else:
                    if cint(old_opt) == 1:
                        frappe.db.set_value("Mitgliedschaft", self.mitglied_id, "digitalrechnung", 0)
                        create_mitglied_change_log(self.mitglied_id, "hat die digitale Rechnung <b>deaktiviert</b>")

                if cint(self.email_changed) == 1:
                    abweichende_rechnungsadresse = cint(frappe.db.get_value("Mitgliedschaft", self.mitglied_id, "abweichende_rechnungsadresse"))
                    unabhaengiger_debitor = cint(frappe.db.get_value("Mitgliedschaft", self.mitglied_id, "unabhaengiger_debitor"))
                    if abweichende_rechnungsadresse == 1 and unabhaengiger_debitor == 1:
                        rg_e_mail = frappe.db.get_value("Mitgliedschaft", self.mitglied_id, "rg_e_mail")
                        if rg_e_mail != self.email:
                            frappe.db.set_value("Mitgliedschaft", self.mitglied_id, "rg_e_mail", self.email)
                            create_mitglied_change_log(self.mitglied_id, "hat die E-Mail-Adresse von {0} auf {1} geändert".format(rg_e_mail, self.email))
                    else:
                        e_mail_1 = frappe.db.get_value("Mitgliedschaft", self.mitglied_id, "e_mail_1")
                        if e_mail_1 != self.email:
                            frappe.db.set_value("Mitgliedschaft", self.mitglied_id, "e_mail_1", self.email)
                            create_mitglied_change_log(self.mitglied_id, "hat die E-Mail-Adresse von {0} auf {1} geändert".format(e_mail_1, self.email))
            else:
                self.changed_by_sektion = 0
    
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

def digitalrechnung_mapper(mitglied):
    def check_if_latest(mitglied):
        latest_mitglied = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `mitglied_nr` = '{0}' ORDER BY `creation` DESC""".format(mitglied.mitglied_nr), as_dict=True)
        if latest_mitglied[0].name == mitglied.name:
            return True
        else:
            return False
    
    def check_existing(hash=None, mitglied_nr=None):
        if hash:
            existing_digitalrechnung = frappe.db.sql("""SELECT `name` FROM `tabDigitalrechnung` WHERE `hash` = '{0}'""".format(hash), as_dict=True)
        if mitglied_nr:
            existing_digitalrechnung = frappe.db.sql("""SELECT `name` FROM `tabDigitalrechnung` WHERE `mitglied_nr` = '{0}'""".format(mitglied_nr), as_dict=True)
        if len(existing_digitalrechnung) > 0:
            return existing_digitalrechnung[0].name
        else:
            return False
    
    def update_digitalrechnung(dr, mitglied):
        dr_doc = frappe.get_doc("Digitalrechnung", dr)
        if dr_doc.mitglied_id != mitglied.name:
            dr_doc.mitglied_id = mitglied.name
        if dr_doc.language != mitglied.language:
            dr_doc.language = mitglied.language

        if cint(mitglied.abweichende_rechnungsadresse) == 1 and cint(mitglied.unabhaengiger_debitor) == 1:
            if dr_doc.email != mitglied.rg_e_mail:
                dr_doc.email = mitglied.rg_e_mail
        else:
            if dr_doc.email != mitglied.e_mail_1:
                dr_doc.email = mitglied.e_mail_1
        
        if dr_doc.sektion_id != mitglied.sektion_id:
            dr_doc.sektion_id = mitglied.sektion_id
        
        if cint(mitglied.digitalrechnung) == 1:
            dr_doc.set_opt_in()
        else:
            dr_doc.set_opt_out()
        
        dr_doc.changed_by_sektion = 1
        
        dr_doc.save(ignore_permissions=True)
    
    def create_digitalrechnung(mitglied):
        dr_doc = frappe.get_doc({
            "doctype": "Digitalrechnung",
            "mitglied_id": mitglied.name,
            "mitglied_nr": mitglied.mitglied_nr,
            "language": mitglied.language,
            "email": mitglied.rg_e_mail if cint(mitglied.abweichende_rechnungsadresse) == 1 and cint(mitglied.unabhaengiger_debitor) == 1 else mitglied.e_mail_1,
            "sektion_id": mitglied.sektion_id
        }).insert(ignore_permissions=True)

        if cint(mitglied.digitalrechnung) == 1:
            dr_doc.set_opt_in()
            dr_doc.save(ignore_permissions=True)
    
    if check_if_latest(mitglied):
        if mitglied.digitalrechnung_hash:
            digitalrechnung = check_existing(hash=mitglied.digitalrechnung_hash)
            if digitalrechnung:
                update_digitalrechnung(digitalrechnung, mitglied)
            else:
                create_digitalrechnung(mitglied)
        else:
            digitalrechnung = check_existing(mitglied_nr=mitglied.mitglied_nr)
            if digitalrechnung:
                update_digitalrechnung(digitalrechnung, mitglied)
            else:
                create_digitalrechnung(mitglied)

def create_mitglied_change_log(mitglied, txt):
    comment = frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Workflow",
        "comment_email": "Das Mitglied",
        "reference_doctype": "Mitgliedschaft",
        "reference_name": mitglied,
        "content": txt
    }).insert(ignore_permissions=True)

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

def reset():
    digitalrechnungen = frappe.db.sql("""SELECT * FROM `tabDigitalrechnung`""", as_dict=True)
    loop = 1
    total = len(digitalrechnungen)
    submit_count = 0
    for digitalrechnung in digitalrechnungen:
        if digitalrechnung.mitglied_id:
            digitalrechnung.email_changed = 0
            digitalrechnung.opt_in = None
            digitalrechnung.opt_out = None
            mitgliedschaft = frappe.db.sql("""
                SELECT
                    `sektion_id`,
                    `e_mail_1` AS `mitgl_email`,
                    `abweichende_rechnungsadresse` AS `abw_rg_adr`,
                    `unabhaengiger_debitor` AS `unabh_deb`,
                    `rg_e_mail` AS `rg_email`,
                    `language`
                FROM `tabMitgliedschaft`
                WHERE `name` = '{0}'
            """.format(digitalrechnung.mitglied_id), as_dict=True)
            if len(mitgliedschaft) > 0:
                m = mitgliedschaft[0]
                digitalrechnung.email = m.mitgl_email
                digitalrechnung.language = m.language
                if cint(m.abw_rg_adr) == 1 and cint(m.unabh_deb) == 1:
                    digitalrechnung.email = None
                    if m.rg_email:
                        digitalrechnung.email = m.rg_email
            digitalrechnung.save()
            submit_count += 1
            if submit_count == 100:
                frappe.db.commit()
                submit_count = 0
            print("{0} von {1}".format(loop, total))
            loop += 1
    frappe.db.commit()

def go_life_reset():
    def check_if_latest(mitglied):
        latest_mitglied = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `mitglied_nr` = '{0}' ORDER BY `creation` DESC""".format(mitglied.mitglied_nr), as_dict=True)
        if latest_mitglied[0].name == mitglied.mitglied_id:
            return True
        else:
            return False
    
    print("Create Digitalrechnungen")
    mitgliedschaften = frappe.db.sql("""
        SELECT
            `name` AS `mitglied_id`,
            `mitglied_nr`,
            `sektion_id`,
            `e_mail_1` AS `mitgl_email`,
            `abweichende_rechnungsadresse` AS `abw_rg_adr`,
            `unabhaengiger_debitor` AS `unabh_deb`,
            `rg_e_mail` AS `rg_email`,
            `digitalrechnung_hash`,
            `language`
        FROM `tabMitgliedschaft`
        WHERE `status_c` NOT IN ('Inaktiv', 'Anmeldung', 'Online-Anmeldung', 'Gestorben', 'Wegzug', 'Ausschluss', 'Interessent*in')
        AND `digitalrechnung_hash` IS NULL
    """, as_dict=True)

    total = len(mitgliedschaften)
    loop = 1
    submit_count = 1

    for mitgliedschaft in mitgliedschaften:
        print("Create: {0} von {1}".format(loop, total))
        if check_if_latest(mitgliedschaft):
            if not mitgliedschaft.digitalrechnung_hash:
                new_digitalrechnung = frappe.get_doc({
                    'doctype': "Digitalrechnung",
                    'mitglied_nr': mitgliedschaft.mitglied_nr,
                    'mitglied_id': mitgliedschaft.mitglied_id,
                    'sektion_id': mitgliedschaft.sektion_id,
                    'email': mitgliedschaft.mitgl_email,
                    'language': mitgliedschaft.language
                })

                if cint(mitgliedschaft.abw_rg_adr) == 1 and cint(mitgliedschaft.unabh_deb) == 1:
                    new_digitalrechnung.email = None
                    if mitgliedschaft.rg_email:
                        new_digitalrechnung.email = mitgliedschaft.rg_email
                
                new_digitalrechnung.insert()
        else:
            print("Skip, not latest")
        
        loop += 1
        submit_count += 1
        if submit_count == 100:
            frappe.db.commit()
            submit_count = 1
    frappe.db.commit()

    print("Check Digitalrechnungen")
    digitalrechnungen = frappe.db.sql("""SELECT `name`, `mitglied_nr`, `mitglied_id` FROM `tabDigitalrechnung`""", as_dict=True)
    loop = 1
    total = len(digitalrechnungen)
    for digitalrechnung in digitalrechnungen:
        print("Check {0} von {1}".format(loop, total))
        latest_mitglied = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `mitglied_nr` = '{0}' ORDER BY `creation` DESC""".format(digitalrechnung.mitglied_nr), as_dict=True)
        if latest_mitglied[0].name != digitalrechnung.mitglied_id:
            frappe.db.set_value("Digitalrechnung", digitalrechnung.name, 'mitglied_id', latest_mitglied[0].name)
            print("Updated {0}".format(loop))
            frappe.db.commit()
        loop += 1

