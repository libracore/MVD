# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.doctype.retouren.retouren import create_post_retouren

# Post Retouren
def _post_retouren(data):
    if 'mitgliedId' in data:
        if data["mitgliedId"] > 0:
            create_sp_log(data["mitgliedId"], True, data)
            if not frappe.db.exists("Mitgliedschaft", data["mitgliedId"]):
                return raise_xxx(400, 'Bad Request', 'Unknown mitgliedId', data=data, error_log_title='400 > _post_retouren')
            else:
                missing_keys = check_main_keys(data, 'retouren')
                if not missing_keys:
                    job = create_post_retouren(data)
                    if job == 1:
                        return raise_200()
                    else:
                        return raise_xxx(500, 'Internal Server Error', '{error}'.format(error=job), data=data, error_log_title='500 > _post_retouren')
                else:
                    return raise_xxx(400, 'Bad Request', '{key} missing'.format(key=missing_keys), data=data, error_log_title='400 > _post_retouren')
        else:
            return raise_xxx(400, 'Bad Request', 'mitgliedId == 0', data=data, error_log_title='400 > _post_retouren')
    else:
        return raise_xxx(400, 'Bad Request', 'mitgliedId missing', data=data, error_log_title='400 > _post_retouren')

# Post Rückmeldungen
def _post_responses(data):
    if 'mitgliedId' in data:
        if data["mitgliedId"] > 0:
            create_sp_log(data["mitgliedId"], False, data)
            if not frappe.db.exists("Mitgliedschaft", data["mitgliedId"]):
                return raise_xxx(400, 'Bad Request', 'Unknown mitgliedId', data=data, error_log_title='400 > _post_responses')
            else:
                missing_keys = check_main_keys(data, 'responses')
                if not missing_keys:
                    # hier würde ich nun die Meldungen verarbeiten
                    return raise_200()
                else:
                    return raise_xxx(400, 'Bad Request', '{key} missing'.format(key=missing_keys), data=data, error_log_title='400 > _post_responses')
        else:
            return raise_xxx(400, 'Bad Request', 'mitgliedId == 0', data=data, error_log_title='400 > _post_responses')
    else:
        return raise_xxx(400, 'Bad Request', 'mitgliedId missing', data=data, error_log_title='400 > _post_responses')

# SP Log
def create_sp_log(mitgliedschaft, retoure, data):
    import json
    try: 
        if isinstance(data, str):
            json_formatted_str = json.dumps(data, indent=2)
        else:
            json_formatted_str = json.dumps(str(data), indent=2)
        
        if retoure:
            retoure = 1
            response = 0
        else:
            retoure = 0
            response = 1
        
        sp_log = frappe.get_doc({
            "doctype": "Service Plattform Log",
            "mv_mitgliedschaft": mitgliedschaft,
            "json": json_formatted_str,
            "retoure": retoure,
            "response": response,
            "status": "Done"
        }).insert(ignore_permissions=True)
    
    except Exception as err:
        frappe.log_error("""
                         Error: {0}\n\n
                         mitgliedschaft: {1}\n\n
                         json_formatted_str: {2}\n\n
                         retoure: {3}\n\n
                         response: {4}
        """.format(err, mitgliedschaft, json_formatted_str, retoure, response), "Post: create_sp_log")
    return

# key check
def check_main_keys(data, typ):
    if typ == 'retouren':
        mandatory_keys = [
            'mitgliedId',
            'legacyKategorieCode',
            'legacyNotiz',
            'grundCode',
            'grundBezeichnung',
            'retoureMuWSequenceNumber',
            'retoureDMC',
            'retoureSendungsbild',
            'datumErfasstPost'
        ]
    else:
        mandatory_keys = [
            'mitgliedId',
            'sektionCode',
            'legacyResponseId',
            'legacyKategorieCode',
            'legacyNotiz',
            'gueltigVon',
            'gueltigBis',
            'erhalten',
            'qStat',
            'qStatBezeichnung',
            'totalScore',
            'shortReport',
            'parsedShortReport',
            'isDirektAktualisierbar',
            'adresseAlt',
            'adresseNeu'
        ]
    
    for key in mandatory_keys:
        if key not in data:
            return key
    else:
        return False

# Status Returns
def raise_xxx(code, title, message, data=None, error_log_title='SP (Post) API Error!'):
    frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(code, title, message, frappe.utils.get_traceback(), data or ''), error_log_title)
    frappe.local.response.http_status_code = code
    frappe.local.response.message = message
    return ['{code} {title}'.format(code=code, title=title), {
        "error": {
            "code": code,
            "message": "{message}".format(message=message)
        }
    }]
    
def raise_200(answer='Success'):
    frappe.local.response.http_status_code = 200
    frappe.local.response.message = answer
    return ['200 Success', answer]

