# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import now
import random
import hashlib

class MitgliedMainNaming(Document):
    def set_new_id(self, existing_nr, mitglied_hash=None):
        if not self.mitglied_id:
            randome_hash = "{0} {1}".format(str(hash(now())), str(random.random()))
            create_new_id = frappe.db.sql("""INSERT INTO `MitgliedMainId` (`id`,`name`) VALUES(0,'{0}');""".format(randome_hash))
            new_id = frappe.db.sql("""SELECT `id` FROM `MitgliedMainId` WHERE `name` = '{0}';""".format(randome_hash))[0][0]
            self.mitglied_id = new_id

            if existing_nr:
                self.mitglied_nr = existing_nr
                self.mitglied_nr_raw = int(existing_nr.replace("MV", ""))
            
            if mitglied_hash:
                self.mitglied_hash = mitglied_hash
            
            if not self.mitglied_hash:
                salt = frappe.get_doc("MVD Settings", "MVD Settings").hash_salt or ''
                txt = "{0}{1}".format(self.mitglied_id, salt)
                
                # Create a SHA-256 hash
                hash_object = hashlib.sha256(txt.encode())
                full_hash = hash_object.hexdigest()
                
                # Truncate to the last 10 characters
                truncated_hash = full_hash[:10]
                
                self.mitglied_hash = truncated_hash

    def set_new_number(self):
        if not self.mitglied_nr_raw:
            randome_hash = "{0} {1}".format(str(hash(now())), str(random.random()))
            create_new_nr = frappe.db.sql("""INSERT INTO `MitgliedMainNumber` (`id`,`name`) VALUES(0,'{0}');""".format(randome_hash))
            new_nr = frappe.db.sql("""SELECT `id` FROM `MitgliedMainNumber` WHERE `name` = '{0}';""".format(randome_hash))[0][0]
            self.mitglied_nr_raw = new_nr

            mitglied_nr = "MV{0}".format(str(new_nr).zfill(8))
            self.mitglied_nr = mitglied_nr

def create_new_id(new_nr=False, existing_nr=False, mitglied_hash=None):
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
        new_mitglied_main_naming.set_new_id(existing_nr, mitglied_hash)
    else:
        try:
            if "MV" in existing_nr:
                # create new ID with existing_nr
                new_mitglied_main_naming.set_new_id(existing_nr, mitglied_hash)
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
        'nr': new_mitglied_main_naming.mitglied_nr,
        'mitglied_hash': new_mitglied_main_naming.mitglied_hash
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
            'nr': mmn.mitglied_nr,
            'mitglied_hash': mmn.mitglied_hash
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


def initial_hash_calc():
    # mvd.mvd.doctype.mitglied_main_naming.mitglied_main_naming.initial_hash_calc
    
    salt = frappe.get_doc("MVD Settings", "MVD Settings").hash_salt or ''
    # alle ausser interessenten
    # nur den neuesten Datensatz pro Mitglied-Nr
    print("Mitglieder")
    mmns = frappe.db.sql("""SELECT *
                            FROM (
                                SELECT *,
                                    ROW_NUMBER() OVER (PARTITION BY `mitglied_nr` ORDER BY `creation` DESC) AS `rn`
                                FROM `tabMitglied Main Naming`
                                WHERE `mitglied_nr_raw` != 0
                            ) AS `sub`
                            WHERE `rn` = 1
                            ORDER BY `creation` DESC;
                         """, as_dict=True)
    total = len(mmns)
    loop = 1
    for mmn in mmns:
        if not mmn.mitglied_hash:
            txt = "{0}{1}".format(mmn.mitglied_id, salt)
            # Create a SHA-256 hash
            hash_object = hashlib.sha256(txt.encode())
            full_hash = hash_object.hexdigest()
            
            # Truncate to the last 10 characters
            truncated_hash = full_hash[:10]
            
            frappe.db.sql("""UPDATE `tabMitglied Main Naming` SET `mitglied_hash` = '{0}' WHERE `name` = '{1}'""".format(truncated_hash, mmn.name))
            frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `mitglied_hash` = '{0}' WHERE `mitglied_nr` = '{1}'""".format(truncated_hash, mmn.mitglied_nr))
            frappe.db.commit()
        print("M: {0} von {1}".format(loop, total))
        loop += 1
    
    # nur interessenten
    print("Interessenten")
    mmns = frappe.db.sql("""SELECT *
                            FROM `tabMitglied Main Naming`
                            WHERE `mitglied_nr_raw` = 0
                            ORDER BY `creation` DESC;
                         """, as_dict=True)
    total = len(mmns)
    loop = 1
    for mmn in mmns:
        if not mmn.mitglied_hash:
            txt = "{0}{1}".format(mmn.mitglied_id, salt)
            # Create a SHA-256 hash
            hash_object = hashlib.sha256(txt.encode())
            full_hash = hash_object.hexdigest()
            
            # Truncate to the last 10 characters
            truncated_hash = full_hash[:10]
            
            frappe.db.sql("""UPDATE `tabMitglied Main Naming` SET `mitglied_hash` = '{0}' WHERE `name` = '{1}'""".format(truncated_hash, mmn.name))
            frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `mitglied_hash` = '{0}' WHERE `name` = '{1}'""".format(truncated_hash, mmn.mitglied_id))
            frappe.db.commit()
        print("I: {0} von {1}".format(loop, total))
        loop += 1