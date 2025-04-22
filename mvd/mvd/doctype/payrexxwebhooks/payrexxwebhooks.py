# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json

class PayrexxWebhooks(Document):
    def after_insert(self):
        # do some magic....
        return

def process_webhook(kwargs):
    def is_allowed():
        from urllib.parse import urlparse
        from urllib.parse import parse_qs
        try:
            url = frappe.request.url
            parsed_url = urlparse(url)
            token = parse_qs(parsed_url.query)['token'][0]
        except:
            token = None
            pass
        
        if token == frappe.db.get_value("MVD Settings", "MVD Settings", "webhooks_token"):
            return True

        frappe.local.response.http_status_code = 401
        frappe.local.response.message = 'Not Allowed'
        return False
    
    # r = frappe.request
    # sender_ip = r.headers.get('X-Real-Ip', None)
    # instance_name = kwargs.get("transaction").get("instance").get("name")
    # uuid = kwargs.get("transaction").get("instance").get("uuid")

    if is_allowed():
        formatted_json = json.dumps(kwargs, indent=2)
        new_pw = frappe.get_doc({
            'doctype': 'PayrexxWebhooks',
            'json': formatted_json
        }).insert(ignore_permissions=True)
