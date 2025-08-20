# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd
from tqdm import tqdm

'''
    execute with: bench --site [site] execute mvd.mvd.data_import.web_auth_script.import_or_update_web_auth --kwargs "{'site_name': '[sitename]', 'file_name': '[filename]', 'limit': 100, 'bench': 'frappe'}"
'''

def import_or_update_web_auth(site_name, file_name, limit=False, bench='frappe'):
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench))
    
    # loop through rows
    count = 1
    submit_count = 1
    max_loop = limit
    index = df.index
    if not limit:
        max_loop = len(index)
    
    error_list = []
    not_existing = []
    created = 0
    updated = 0
        
    # for index, row in df.iterrows():
    for index, row in tqdm(df.iterrows(), desc="Creating/Updating Web-Login and Password-Hashes", unit=" PWD Datasets", total=max_loop):
        if count <= max_loop:
            mitglied_nr = "MV0{0}".format(str(int(get_value(row, 'user_id'))))
            from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr
            mitglied_id = get_mitglied_id_from_nr(mitglied_nr=mitglied_nr, ignore_inaktiv=True)

            if frappe.db.exists("Mitgliedschaft", mitglied_id):
                user_id = "{0}@login.ch".format(mitglied_nr)
                if not frappe.db.exists("User", user_id):
                    try:
                        # create User
                        web_login_user = frappe.get_doc({
                            "doctype": "User",
                            "email": user_id,
                            "first_name": user_id.replace("@login.ch", ""),
                            "last_name": "WebLogin",
                            "send_welcome_email": 0
                        })
                        web_login_user.insert(ignore_permissions=True)

                        # Set Passwort-Hash
                        frappe.db.sql("""
                                      INSERT INTO `__Auth` (`doctype`, `name`, `fieldname`, `password`, `encrypted`)
                                      VALUES ('User', '{0}', 'password', '{1}', 0)
                                      """.format(user_id, get_value(row, 'password_hashed')))
                        frappe.db.set_value("Mitgliedschaft", mitglied_id, 'web_login_user_created', 1)
                        created += 1
                    except Exception as err:
                        error_list.append([mitglied_nr, str(err)])
                else:
                    # Update Passwort-Hash
                    frappe.db.sql("""
                                UPDATE `__Auth`
                                SET `password`= '{0}'
                                WHERE `doctype` = 'User'
                                AND `name` = '{1}'
                                AND `fieldname` = 'password'
                                AND `encrypted` = 0
                                """.format(get_value(row, 'password_hashed'), user_id))
                    updated += 1
            else:
                not_existing.append(mitglied_nr)
            
            count += 1
            submit_count += 1
            if submit_count == 100:
                frappe.db.commit()
                submit_count = 1
        else:
            break
    
    frappe.db.commit()

    print("WrapUp:")
    print("------------------------")
    print("Created: {0}".format(created))
    print("Updated: {0}".format(updated))
    print("------------------------")
    print("Inexistente Mitgliedschaften:")
    print(not_existing)
    print("------------------------")
    print("Fehler:")
    print(error_list)

def get_value(row, value):
    value = row[value]
    if not pd.isnull(value):
        try:
            if isinstance(value, str):
                return value.strip()
            else:
                return value
        except:
            return value
    else:
        return ''