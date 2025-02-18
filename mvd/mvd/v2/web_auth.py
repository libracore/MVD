# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

'''
LOGIN
------------------------------------------------------------------------------------------------------------
curl --location --request POST 'https://libracore.mieterverband.ch/api/method/mvd.mvd.v2.web_auth.login' \
--header 'Content-Type: application/json' \
--data-raw '{
    "user": "MV11111111",
    "pwd": "$HASHMETHODE$PWDHASH"
}'

Optionaler Parameter "clear" --> PWD im Klartext, default = PWD als Hash

RESET
------------------------------------------------------------------------------------------------------------
Anfrage eines Reset Hash per Mail
----------------------------------
curl --location --request POST 'https://libracore.mieterverband.ch/api/method/mvd.mvd.v2.web_auth.reset' \
--header 'Content-Type: application/json' \
--data-raw '{
    "user": "MV11111111"
}'

Reset PWD mit Reset-Hash
--------------------------
curl --location --request POST 'https://libracore.mieterverband.ch/api/method/mvd.mvd.v2.web_auth.reset' \
--header 'Content-Type: application/json' \
--data-raw '{
    "user": "MV11111111",
    "reset_hash": "HIERFOLGTDERRESETHASH",
    "pwd": "$HASHMETHODE$PWDHASH"
}'
'''

'''
ENDPOINTS
'''

@frappe.whitelist(allow_guest=True)
def login(**api_request):
    # Check/Get Mitgliedernummer
    if '@' in api_request['user']:
        mitglied = get_mitglied_nummer(api_request['user'])
    elif 'MV0' in api_request['user']:
        mitglied = "{0}@login.ch".format(api_request['user'])
    elif 'MV' not in api_request['user']:
        mitglied = "MV{0}@login.ch".format(api_request['user'])
    else:
        mitglied = None
    
    if mitglied and api_request['pwd']:
        clear = False
        if "clear" in api_request:
            clear = True
        return check_credentials(mitglied, api_request['pwd'], clear)
    
    return multi_mail()

@frappe.whitelist(allow_guest=True)
def reset(**api_request):
    # Check/Get Mitgliedernummer
    if '@' in api_request['user']:
        mitglied = get_mitglied_nummer(api_request['user'])
    elif 'MV0' in api_request['user']:
        mitglied = "{0}@login.ch".format(api_request['user'])
    elif 'MV' not in api_request['user']:
        mitglied = "MV{0}@login.ch".format(api_request['user'])
    else:
        mitglied = None
    
    if mitglied:
        if 'reset_hash' in api_request and 'pwd' in api_request:
            return update_pwd(mitglied, api_request['reset_hash'], api_request['pwd'])
        else:
            return generate_reset_hash(mitglied)
    
    return multi_mail()

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

def update_pwd(user, reset_hash, pwd):
    user_doc = frappe.get_doc("User", user)
    if user_doc.reset_password_key == reset_hash:
        frappe.db.sql("""
                        UPDATE
                        `__Auth`
                        SET `password` = '{pwd}'
                        WHERE `doctype` = 'User'
                        AND `name` = '{user}'
                        AND `fieldname` = 'password'
                        AND `encrypted` = 0""".format(user=user, pwd=pwd))
        user_doc.reset_password_key = ''
        user_doc.save(ignore_permissions=True)
        return success_data(user)
    else:
         return failed_login()

def generate_reset_hash(user):
    from frappe.utils import random_string
    key = random_string(32)
    user_doc = frappe.get_doc("User", user)
    user_doc.reset_password_key = key
    user_doc.save(ignore_permissions=True)
    # TBD
    # hier erfolgt dann noch der Mailversand
    return success_info()

'''
RETURNS
'''

def success_data(mitglied_nr):
    mitglied_nr = mitglied_nr.replace("@login.ch", "")
    from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr
    mitglied_id = get_mitglied_id_from_nr(mitglied_nr=mitglied_nr)
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
    code = 200
    return {
        "code": code
    }

def multi_mail():
    code = 409
    message = 'E-Mail mehrfach vorhanden'
    return {
        "code": code,
        "message": "{message}".format(message=message)
    }

def failed_login():
    code = 401
    message = 'Passwort falsch'
    return {
        "code": code,
        "message": "{message}".format(message=message)
    }

def server_error():
    code = 500
    message = 'Internal Server Error'
    return {
        "code": code,
        "message": "{message}".format(message=message)
    }
