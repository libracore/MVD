# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class MitgliedMainNaming(Document):
    def set_new_id(self, existing_nr):
        if not self.mitglied_id:
            last_id = frappe.db.sql("""
                                    SELECT `mitglied_id` AS `last_id`
                                    FROM `tabMitglied Main Naming`
                                    ORDER BY `mitglied_id` DESC
                                    LIMIT 1
                                    """, as_dict=True)[0].last_id or 499999
            new_id = last_id + 1
            self.mitglied_id = new_id

            if existing_nr:
                self.mitglied_nr = existing_nr
                self.mitglied_nr_raw = int(existing_nr.replace("MV", ""))

    def set_new_number(self):
        if not self.mitglied_nr_raw:
            last_nr = frappe.db.sql("""
                                    SELECT `mitglied_nr_raw` AS `last_nr`
                                    FROM `tabMitglied Main Naming`
                                    ORDER BY `mitglied_nr_raw` DESC
                                    LIMIT 1
                                    """, as_dict=True)[0].last_nr or 3900000
            new_nr = last_nr + 1
            self.mitglied_nr_raw = new_nr

            mitglied_nr = "MV{0}".format(str(new_nr).zfill(8))
            self.mitglied_nr = mitglied_nr

def create_new_id(new_nr=False, existing_nr=False):
    # create record
    new_mitglied_main_naming = frappe.get_doc({
        'doctype': "Mitglied Main Naming"
    })
    new_mitglied_main_naming.insert(ignore_permissions=True)

    if new_nr and existing_nr:
        return {
            'error': True,
            'msg': "unauthorized combination (new_nr and existing_nr)",
            'code': 400,
            'title': 'Bad Request'
        }

    # create new ID
    new_mitglied_main_naming.set_new_id(existing_nr)

    # create new nr
    if new_nr:
        new_mitglied_main_naming.set_new_number()
    
    new_mitglied_main_naming.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        'id': new_mitglied_main_naming.mitglied_id,
        'nr': new_mitglied_main_naming.mitglied_nr
    }

def create_new_number(id=None):
    # check if id is present
    if not id:
        return {
            'error': True,
            'msg': "ID is mandatory",
            'code': 400,
            'title': 'Bad Request'
        }
    
    # check if id exists
    if not frappe.db.exists("Mitglied Main Naming", {'mitglied_id': id}):
        return {
            'error': True,
            'msg': "ID not existing",
            'code': 404,
            'title': 'Not Found'
        }
    else:
        # get Mitglied Main Naming
        mitglied_main_naming = frappe.db.sql("""
                                            SELECT `name`
                                            FROM `tabMitglied Main Naming`
                                            WHERE `mitglied_id` = {0}
                                            LIMIT 1
                                            """.format(id), as_dict=True)[0].name or None
        if not mitglied_main_naming:
            return {
                'error': True,
                'msg': "ID not existing",
                'code': 404,
                'title': 'Not Found'
            }
        
        # create new number
        mmn = frappe.get_doc("Mitglied Main Naming", mitglied_main_naming)
        mmn.set_new_number()
        mmn.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            'id': mmn.mitglied_id,
            'nr': mmn.mitglied_nr
        }


