# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.doctype.retouren_mw.retouren_mw import create_post_retouren

# Post Retouren
def _post_retouren(data):
    if 'mitgliedId' in data:
        if data["mitgliedId"] > 0:
            create_sp_log(data["mitgliedId"], True, data)
            if not frappe.db.exists("Mitgliedschaft", data["mitgliedId"]):
                return raise_xxx(400, 'Bad Request', 'Unknown mitgliedId', data)
            else:
                missing_keys = check_main_keys(data, 'retouren')
                if not missing_keys:
                    # hier würde ich nun die Meldungen verarbeiten
                    job = create_post_retouren(data)
                    if job == 1:
                        return raise_200()
                    else:
                        return raise_xxx(500, 'Internal Server Error', '{error}'.format(error=job), data)
                else:
                    return raise_xxx(400, 'Bad Request', '{key} missing'.format(key=missing_keys), data)
        else:
            return raise_xxx(400, 'Bad Request', 'mitgliedId == 0', data)
    else:
        return raise_xxx(400, 'Bad Request', 'mitgliedId missing', data)

# Post Rückmeldungen
def _post_responses(data):
    if 'mitgliedId' in data:
        if data["mitgliedId"] > 0:
            create_sp_log(data["mitgliedId"], False, data)
            if not frappe.db.exists("Mitgliedschaft", data["mitgliedId"]):
                return raise_xxx(400, 'Bad Request', 'Unknown mitgliedId', data)
            else:
                missing_keys = check_main_keys(data, 'responses')
                if not missing_keys:
                    # hier würde ich nun die Meldungen verarbeiten
                    return raise_200()
                else:
                    return raise_xxx(400, 'Bad Request', '{key} missing'.format(key=missing_keys), data)
        else:
            return raise_xxx(400, 'Bad Request', 'mitgliedId == 0', data)
    else:
        return raise_xxx(400, 'Bad Request', 'mitgliedId missing', data)

# SP Log
def create_sp_log(mitgliedschaft, retoure, data):
    if retoure:
        retoure = 1
        response = 0
    else:
        retoure = 0
        response = 1
    
    sp_log = frappe.get_doc({
        "doctype":"Service Plattform Log",
        "mv_mitgliedschaft": mitgliedschaft,
        "json": str(data),
        "retoure": retoure,
        "response": response
    }).insert(ignore_permissions=True)
    
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
def raise_xxx(code, title, message, data=None):
    frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(code, title, message, frappe.utils.get_traceback(), data or ''), 'SP (Post) API Error!')
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

