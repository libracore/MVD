# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint

@frappe.whitelist()
def login(**api_request):
    # Check/Get Mitgliedernummer
    mitglied = None
    if 'user' in api_request:
        if '@' in api_request['user']:
            mitglied = get_mitglied_nummer(api_request['user'])
        elif 'MV0' in api_request['user']:
            mitglied = "{0}@login.ch".format(api_request['user'])
        elif 'MV' not in api_request['user']:
            mitglied = "MV{0}@login.ch".format(api_request['user'])
    
    if 'pwd' in api_request:
        if mitglied and api_request['pwd']:
            clear = False
            if "clear" in api_request:
                clear = True
            return check_credentials(mitglied, api_request['pwd'], clear)
    
    if 'reset_hash' in api_request and api_request['reset_hash']:
        return check_hash_based_credentials(api_request['reset_hash'])
    
    return multi_mail()

@frappe.whitelist()
def reset(**api_request):
    email = None
    mitglied = None
    # Check/Get Mitgliedernummer
    if 'user' in api_request:
        if '@' in api_request['user']:
            mitglied = get_mitglied_nummer(api_request['user'])
            email = api_request['user']
        elif 'MV0' in api_request['user']:
            mitglied = "{0}@login.ch".format(api_request['user'])
        elif 'MV' not in api_request['user']:
            mitglied = "MV{0}@login.ch".format(api_request['user'])
    
        if mitglied:
            if 'reset_hash' in api_request and 'pwd' in api_request:
                clear = False
                if "clear" in api_request:
                    clear = True
                return update_pwd(mitglied, api_request['reset_hash'], api_request['pwd'], clear)
            else:
                hash_only = False
                if 'get_hash' in api_request and api_request['get_hash']:
                    hash_only = True
                return generate_reset_hash(mitglied, email, hash_only)
        else:
            return unknown_user()
    elif 'reset_hash' in api_request and 'pwd' in api_request:
            clear = False
            if "clear" in api_request:
                clear = True
            return update_pwd(mitglied, api_request['reset_hash'], api_request['pwd'], clear)
    
    return server_error()

'''
HELPERS
'''

def get_mitglied_nummer(user):
    mitgliedschaften = frappe.db.sql("""
                                    SELECT
                                        `mitglied_nr`
                                    FROM `tabMitgliedschaft`
                                    WHERE `e_mail_1` = '{0}'
                                    AND `status_c` != 'Inaktiv'
                                    ORDER BY
                                    CASE
                                        WHEN `status_c` = 'Regulär' THEN 1
                                        WHEN `status_c` = 'Online-Beitritt' THEN 2
                                        WHEN `status_c` = 'Zuzug' THEN 3
                                        WHEN `status_c` = 'Online-Mutation' THEN 4
                                        WHEN `status_c` = 'Online-Kündigung' THEN 5
                                        ELSE 6
                                    END,
                                    `status_c`
                                    """.format(user), as_dict=True)
    if len(mitgliedschaften) != 1:
        return False
    
    return "{0}@login.ch".format(mitgliedschaften[0].mitglied_nr)

def check_credentials(user, pwd, clear=False):
    if clear:
        # Prüfung des pwd im Klartext
        from frappe.utils.password import check_password
        try:
            mitglied_nr = check_password(user, pwd)
            if mitglied_nr:
                return success_data(mitglied_nr)
            else:
                return failed_login()
        except:
            return failed_login()
    else:
        # Reiner Hash Vergleich
        auth = frappe.db.sql("""
                             SELECT `name`, `password`
                             FROM `__Auth`
                             WHERE `doctype` = 'User'
                             AND `name` = '{user}'
                             AND `fieldname` = 'password'
                             AND `encrypted` = 0""".format(user=user), as_dict=True)
        if not auth or auth[0].password != pwd:
            return failed_login()
        else:
            return success_data(auth[0].name)

def check_hash_based_credentials(reset_hash):
    potential_user = frappe.db.sql("""
                                    SELECT `name`
                                   FROM `tabUser`
                                   WHERE `reset_password_key` = "{0}"
    """.format(reset_hash), as_dict=True)
    if len(potential_user) == 1:
        if '@login.ch' in potential_user[0].name:
            try:
                return success_data(potential_user[0].name)
            except:
                return failed_login()
    else:
        return failed_login()

def update_pwd(user, reset_hash, pwd, clear):
    print("{0}".format(pwd))
    user_doc = None
    if user:
        try:
            user_doc = frappe.get_doc("User", user)
        except:
            return unknown_user()
    else:
        potential_user = frappe.db.sql("""
                                    SELECT `name`
                                   FROM `tabUser`
                                   WHERE `reset_password_key` = "{0}"
        """.format(reset_hash), as_dict=True)
        if len(potential_user) == 1:
            if '@login.ch' in potential_user[0].name:
                user_doc = frappe.get_doc("User", potential_user[0].name)
    
    if not user_doc: return unknown_user()

    if user_doc.reset_password_key == reset_hash:
        if clear:
            if is_password_strength(user_doc, pwd):
                from frappe.utils.password import update_password
                update_password(user_doc.name, pwd)
                user_doc.reset_password_key = ''
                user_doc.save(ignore_permissions=True)
                frappe.db.commit()
                return success_data(user_doc.name)
            else:
                return weak_pwd()
        else:
            frappe.db.sql("""
                            UPDATE
                            `__Auth`
                            SET `password` = '{pwd}'
                            WHERE `doctype` = 'User'
                            AND `name` = '{user}'
                            AND `fieldname` = 'password'
                            AND `encrypted` = 0""".format(user=user_doc.name, pwd=pwd))
            user_doc.reset_password_key = ''
            user_doc.save(ignore_permissions=True)
            frappe.db.commit()
            return success_data(user_doc.name)
    else:
         return invalid_reset_hash()

def is_password_strength(user_doc, pwd):
    from frappe.core.doctype.user.user import test_password_strength
    user_data = (user_doc.first_name, user_doc.middle_name, user_doc.last_name, user_doc.email, user_doc.birth_date)
    result = test_password_strength(pwd, '', None, user_data)
    feedback = result.get("feedback", None)

    if feedback and not feedback.get('password_policy_validation_passed', False):
        return False

    return True

def generate_reset_hash(user, email, hash_only=False):
    from frappe.utils import random_string
    key = random_string(32)
    try:
        user_doc = frappe.get_doc("User", user)
    except:
        return unknown_user()
    
    user_doc.reset_password_key = key
    user_doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    if not hash_only:
        from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr
        mitglied_id = get_mitglied_id_from_nr(mitglied_nr=user.replace("@login.ch", ""))
        anrede = frappe.db.get_value("Mitgliedschaft", mitglied_id, "briefanrede") or "Guten Tag"
        if cint(frappe.db.get_value("MVD Settings", "MVD Settings", "pwd_reset_an_testadresse")) == 1:
            email = frappe.db.get_value("MVD Settings", "MVD Settings", "pwd_reset_testadresse")
        else:
            if not email:
                email = frappe.db.get_value("Mitgliedschaft", mitglied_id, "e_mail_1")
        if not email:
            return server_error()

        sender = frappe.db.get_value("MVD Settings", "MVD Settings", 'pwd_reset_sender')
        sender_name = frappe.db.get_value("MVD Settings", "MVD Settings", 'pwd_reset_sender_name')
        if sender_name:
            sender = "{0} <{1}>".format(sender_name, sender)
        subject = frappe.db.get_value("MVD Settings", "MVD Settings", 'pwd_reset_subject')
        template = frappe.db.get_value("MVD Settings", "MVD Settings", 'pwd_reset_template') or 'website_pwd_reset'
        reset_url = frappe.db.get_value("MVD Settings", "MVD Settings", 'reset_url')
        args = {
            'link': "{0}/?reset_hash={1}".format(reset_url, key),
            'mitglied_nr': user.replace("@login.ch", "").replace("mv", "MV"),
            'anrede': anrede
        }
        if not sender or not subject or not template or not reset_url:
            return server_error()
        
        try:
            frappe.sendmail(recipients=[email], sender=sender, subject=subject,
                template=template, args=args, retry=3)
            frappe.db.commit()
        except:
            return server_error()
        
        return success_info()
    else:
        hash_only_success_info(key)

'''
RETURNS
'''

def success_data(mitglied_nr):
    mitglied_nr = mitglied_nr.replace("@login.ch", "")
    from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr
    mitglied_id = get_mitglied_id_from_nr(mitglied_nr=mitglied_nr)

    if not mitglied_id:
        return inactive_member()

    if frappe.db.exists("Mitgliedschaft", mitglied_id):
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitglied_id)
        code = 200
        return {
            "code": code,
            "message": {
                'mitglied_nr': mitgliedschaft.mitglied_nr,
                'mitglied_id': mitglied_id,
                'sektion_id': mitgliedschaft.sektion_id
            }
        }
    else:
        return server_error()

def success_info():
    frappe.response['http_status_code'] = 200

def hash_only_success_info(reset_hash):
    frappe.response['http_status_code'] = 201
    frappe.response['message'] = {
        "reset_hash": reset_hash
    }

def multi_mail():
    frappe.response['http_status_code'] = 409
    frappe.response['message'] = "E-Mail mehrfach vorhanden"

def failed_login():
    frappe.response['http_status_code'] = 401
    frappe.response['message'] = "Passwort falsch"

def server_error():
    frappe.response['http_status_code'] = 500
    frappe.response['message'] = "Internal Server Error"

def weak_pwd():
    frappe.response['http_status_code'] = 422
    frappe.response['message'] = "Password requirements"

def invalid_reset_hash():
    frappe.response['http_status_code'] = 498
    frappe.response['message'] = "Invalid reset hash"

def unknown_user():
    frappe.response['http_status_code'] = 404
    frappe.response['message'] = "User not found"

def inactive_member():
    frappe.response['http_status_code'] = 406
    frappe.response['message'] = "No active member found"
