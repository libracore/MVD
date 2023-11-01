# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class WebshopOrder(Document):
    pass

def create_order_from_api(kwargs=None):
    if (kwargs):
        try:
            import json
            json_formatted_str = json.dumps(kwargs, indent=2)
            webshop_order = frappe.get_doc({
                "doctype": "Webshop Order",
                "request": json_formatted_str
            }).insert(ignore_permissions=True)
            return raise_200()
        except Exception as err:
            return raise_xxx(500, '', err, daten=kwargs)

# Success Return
def raise_200(answer='Success'):
    frappe.local.response.http_status_code = 200
    frappe.local.response.message = answer
    return ['200 Success', answer]

# Error Return
def raise_xxx(code, title, message, daten=None):
    frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(code, title, message, frappe.utils.get_traceback(), daten or ''), 'SP API Error!')
    frappe.local.response.http_status_code = code
    frappe.local.response.message = message
    return ['{code} {title}'.format(code=code, title=title), {
        "error": {
            "code": code,
            "message": "{message}".format(message=message)
        }
    }]
