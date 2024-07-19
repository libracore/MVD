# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import today

class MitgliedMainNaming(Document):
    def set_new_id(self, existing_nr):
        # MVZH Sepcial Case (#1089; Doppelte Zuzüge)
        affected = False
        if existing_nr:
            same_day_requests = frappe.db.sql("""
                                    SELECT `mitglied_id`
                                    FROM `tabMitglied Main Naming`
                                    WHERE `mitglied_nr` = '{0}'
                                    AND `creation` BETWEEN '{1} 00:00:00' AND '{1} 23:59:59'
                                    ORDER BY `creation` DESC
                                    LIMIT 2
                                    """.format(existing_nr, today()), as_dict=True)
            if len(same_day_requests) > 0:
                same_day_request_data = frappe.db.sql("""SELECT `status_c`, `sektion_id` FROM `tabMitgliedschaft` WHERE `name` = '{0}'""".format(same_day_requests[0].mitglied_id), as_dict=True)
                if same_day_request_data[0].status_c == 'Zuzug':
                    affected = same_day_requests[0].mitglied_id
                if not affected and len(same_day_requests) > 1:
                    same_day_request_data = frappe.db.sql("""SELECT `status_c`, `sektion_id` FROM `tabMitgliedschaft` WHERE `name` = '{0}'""".format(same_day_requests[1].mitglied_id), as_dict=True)
                    if same_day_request_data[1].sektion_id == 'MVZH':
                        affected = same_day_requests[1].mitglied_id
        # END: MVZH Sepcial Case (#1089; Doppelte Zuzüge)

        if not self.mitglied_id:
            if not affected:
                last_id = frappe.db.sql("""
                                        SELECT `mitglied_id` AS `last_id`
                                        FROM `tabMitglied Main Naming`
                                        ORDER BY `mitglied_id` DESC
                                        LIMIT 1
                                        """, as_dict=True)[0].last_id or 999999
                if last_id < 999999:
                    last_id = 999999
                
                new_id = last_id + 1
                self.mitglied_id = new_id

                if existing_nr:
                    self.mitglied_nr = existing_nr
                    self.mitglied_nr_raw = int(existing_nr.replace("MV", ""))
            else:
                self.mitglied_id = affected
                self.mitglied_nr = existing_nr
                self.mitglied_nr_raw = int(existing_nr.replace("MV", ""))

    def set_new_number(self):
        if not self.mitglied_nr_raw:
            last_nr = frappe.db.sql("""
                                    SELECT `mitglied_nr_raw` AS `last_nr`
                                    FROM `tabMitglied Main Naming`
                                    ORDER BY `mitglied_nr_raw` DESC
                                    LIMIT 1
                                    """, as_dict=True)[0].last_nr or 4999999
            if last_nr < 4999999:
                last_nr = 4999999
            
            new_nr = last_nr + 1
            self.mitglied_nr_raw = new_nr

            mitglied_nr = "MV{0}".format(str(new_nr).zfill(8))
            self.mitglied_nr = mitglied_nr

def create_new_id(new_nr=False, existing_nr=False):
    if new_nr and existing_nr:
        return {
            'error': True,
            'msg': "unauthorized combination (new_nr and existing_nr)",
            'code': 400,
            'title': 'Bad Request'
        }
    
    # create record
    new_mitglied_main_naming = frappe.get_doc({
        'doctype': "Mitglied Main Naming"
    })
    new_mitglied_main_naming.insert(ignore_permissions=True)
    
    if not existing_nr:
        # create new ID
        new_mitglied_main_naming.set_new_id(existing_nr)
    else:
        try:
            if "MV" in existing_nr:
                # create new ID with existing_nr
                new_mitglied_main_naming.set_new_id(existing_nr)
            else:
                return {
                    'error': True,
                    'msg': "Bad Value (existing_nr)",
                    'code': 400,
                    'title': 'Bad Request'
                }
        except:
            return {
                    'error': True,
                    'msg': "Bad Value (existing_nr)",
                    'code': 400,
                    'title': 'Bad Request'
                }

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

'''
    Diese Methode wird nur (zu Migrationszwecken) verwendet,
    um alle ID/Nr Datensätze zu löschen und mit der aktuellen Mitgliederliste abzugleichen.
    call to action:
    bench --site [site_name] execute mvd.mvd.doctype.mitglied_main_naming.mitglied_main_naming.reset_mitglied_main_naming
'''
def reset_mitglied_main_naming(delete=True):
    if delete:
        print("lösche Tab Mitglied Main Naming...")
        safe_update_out = frappe.db.sql("""SET SQL_SAFE_UPDATES = 0""", as_list=True)
        delete_mitglied_main_naming = frappe.db.sql("""
                                                    DELETE FROM `tabMitglied Main Naming`
                                                    """, as_list=True)
        safe_update_in = frappe.db.sql("""SET SQL_SAFE_UPDATES = 1""", as_list=True)
        frappe.db.commit()

    print("Lade Mitgliedschaften...")
    mitgliedschaften = frappe.db.sql("""
                                     SELECT
                                        `name` AS `id`,
                                        `mitglied_nr` AS `nr`
                                     FROM `tabMitgliedschaft`
                                     ORDER BY `creation` ASC
                                     """, as_dict=True)
    total = len(mitgliedschaften)
    loop = 1
    counter = 1
    errors = []
    for mitgliedschaft in mitgliedschaften:
        print("{0} von {1}".format(loop, total))
        check_successfull = True
        if delete:
            existing_main_naming = frappe.db.sql("""
                                                SELECT `name` FROM `tabMitglied Main Naming`
                                                WHERE `mitglied_id` = '{0}'
                                                """.format(mitgliedschaft.id), as_dict=True)
            if len(existing_main_naming) > 0:
                print("Möglicher Fehler bei Mitglied {0}".format(mitgliedschaft.id))
                errors.append(mitgliedschaft.id)
                loop += 1
                check_successfull = False
            
        if check_successfull:
            if not delete:
                if frappe.db.exists("Mitglied Main Naming", {'mitglied_id': mitgliedschaft.id}):
                    print("Skip Mitglied {0}".format(mitgliedschaft.id))
                    loop += 1
                    check_successfull = False
            if check_successfull:
                mitglied_nr_raw = 0
                mitglied_nr = None
                if mitgliedschaft.nr and mitgliedschaft.nr != "MV":
                    mitglied_nr = mitgliedschaft.nr
                    mitglied_nr_raw = int(mitgliedschaft.nr.replace("MV0", ""))
                
                new_mitglied_main_naming = frappe.get_doc({
                    'doctype': "Mitglied Main Naming",
                    'mitglied_id': mitgliedschaft.id,
                    'mitglied_nr_raw': mitglied_nr_raw,
                    'mitglied_nr': mitglied_nr
                })
                new_mitglied_main_naming.insert(ignore_permissions=True)
                loop += 1
                counter += 1
                if counter == 100:
                    frappe.db.commit()
                    counter = 1
    if len(errors) > 0:
        frappe.log_error("{0}".format(errors), "reset_mitglied_main_naming")
        print("Achtung Error Log beachten!")
    print("Done")
