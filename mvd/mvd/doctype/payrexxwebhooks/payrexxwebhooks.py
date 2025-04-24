# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from frappe.utils import cint
from urllib.parse import urlparse
from urllib.parse import parse_qs

class PayrexxWebhooks(Document):
    def before_insert(self):
        self.set_transaction_fields()

    def set_transaction_fields(self):
        try:
            if not self.json:
                return

            data = json.loads(self.json)
            transaction = data.get("transaction", {})
            transaction_id = transaction.get("id")

            # Define a mapping of attribute names to their paths in the JSON
            field_map = {
                "status": lambda t: t.get("status"),
                "amount": lambda t: t.get("amount"),
                "amount": lambda t: round(float(t["amount"]) / 100.0, 2) if t.get("amount") not in [None, ""] else None, # Amount comes in Rp. as Int -> convert to CHF
                "title": lambda t: t.get("contact", {}).get("title"),
                "first_name": lambda t: t.get("contact", {}).get("firstname"),
                "last_name": lambda t: t.get("contact", {}).get("lastname"),
                "company": lambda t: t.get("contact", {}).get("company"),
                "street": lambda t: t.get("contact", {}).get("street"),
                "plz": lambda t: t.get("contact", {}).get("zip"),
                "place": lambda t: t.get("contact", {}).get("place"),
                "country": lambda t: t.get("contact", {}).get("country"),
                "phone": lambda t: t.get("contact", {}).get("phone"),
                "email": lambda t: t.get("contact", {}).get("email"),
                "transaction_datetime": lambda t: t.get("time"),
            }

            missing_fields = [] # to log error
            for field, getter in field_map.items():
                value = getter(transaction)
                setattr(self, field, value)
                if value is None:
                    missing_fields.append(field)

            if missing_fields: #log error
                log_message = (
                    "Missing or invalid fields in PayrexxWebhook\n"
                    "Transaction ID: {0}\n"
                    "Missing Fields: {1}".format(transaction_id, ', '.join(missing_fields))
                )
                frappe.log_error("PayrexxWebhook Missing Fields", log_message)

        except Exception as e:
            frappe.log_error("PayrexxWebhook JSON parse error", str(e))

    def after_insert(self):
        # do some magic....
        return

def process_webhook(kwargs):
    def is_allowed(payrexx_ip):
        try:
            url = frappe.request.url
            parsed_url = urlparse(url)
            token = parse_qs(parsed_url.query)['token'][0]
        except:
            token = None
            pass
        
        if token == frappe.db.get_value("MVD Settings", "MVD Settings", "webhooks_token"):
            if payrexx_ip:
                allowed = frappe.db.sql("""SELECT `name` FROM `tabPayrexx IP` WHERE `ip` = '{0}'""".format(payrexx_ip), as_dict=True)
                if len(allowed) > 0:
                    return True
            else:
                return True

        frappe.local.response.http_status_code = 401
        frappe.local.response.message = 'Not Allowed'
        return False
    
    payrexx_ip = False
    if cint(frappe.db.get_value("MVD Settings", "MVD Settings", "check_payrexx_ip")) == 1:
        r = frappe.request
        payrexx_ip = r.headers.get('X-Real-Ip', "0.0.0.0")
    # instance_name = kwargs.get("transaction").get("instance").get("name")
    # uuid = kwargs.get("transaction").get("instance").get("uuid")

    if is_allowed(payrexx_ip):
        transaction = kwargs.get("transaction", {})
        transaction_id = transaction.get("id")

        formatted_json = json.dumps(kwargs, indent=2)
        new_pw = frappe.get_doc({
            'doctype': 'PayrexxWebhooks',
            'json': formatted_json,
            'transaction_id': transaction_id,
        }).insert(ignore_permissions=True)
