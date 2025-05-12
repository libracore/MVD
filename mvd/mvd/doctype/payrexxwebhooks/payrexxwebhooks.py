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
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import mitgliedschaft_zuweisen

class PayrexxWebhooks(Document):
    def before_insert(self):
        self.set_transaction_fields()

    def after_insert(self):
        email = self.email 
        mitglied_hash = self.mitglied_hash
        plz = self.plz
        mitglied_info = mitgliedschaft_zuweisen(email=email, mitglied_hash=mitglied_hash, plz=plz)

        if mitglied_info:
            if isinstance(mitglied_info, tuple):
                mitglied_id, sektion_id = mitglied_info
                frappe.db.set_value(self.doctype, self.name, "mitglied", mitglied_id)
                frappe.db.set_value(self.doctype, self.name, "sektion", sektion_id)
            elif isinstance(mitglied_info, str):
                frappe.db.set_value(self.doctype, self.name, "sektion", mitglied_info)
                
        return
    

    def set_transaction_fields(self):
        try:
            if not self.json:
                return

            data = json.loads(self.json)
            transaction = data.get("transaction", {})
            transaction_uuid = transaction.get("uuid")

            # Define a mapping of attribute names to their paths in the JSON
            field_map = {
                "status": lambda t: t.get("status"),
                "amount": lambda t: round(float(t["amount"]) / 100.0, 2) if t.get("amount") not in [None, ""] else None, # Amount comes in Rp. as Int -> convert to CHF
                "currency": lambda t: t.get("invoice", {}).get("currency"),
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

            # Custom logic to extract mitglied_hash because it's in a list
            mitglied_hash = None
            custom_fields = transaction.get("invoice", {}).get("custom_fields", [])
            for field in custom_fields:
                if "mitglied_hash" in field:
                    mitglied_hash = field.get("mitglied_hash")
                    break

            self.mitglied_hash = mitglied_hash

            # Error logging
            if mitglied_hash is None:
                missing_fields.append("mitglied_hash")

            if missing_fields: #log error
                log_message = (
                    "Missing or invalid fields in PayrexxWebhook\n"
                    "Transaction uuid: {0}\n"
                    "Missing Fields: {1}".format(transaction_uuid, ', '.join(missing_fields))
                )
                frappe.log_error("PayrexxWebhook Missing Fields", log_message)

        except Exception as e:
            frappe.log_error("PayrexxWebhook JSON parse error", str(e))

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
        transaction_uuid = transaction.get("uuid")
        formatted_json = json.dumps(kwargs, indent=2)


        existing = frappe.get_all("PayrexxWebhooks", filters={"uuid": transaction_uuid}, fields=["name"])
        if existing:
            # Update existing document
            doc = frappe.get_doc("PayrexxWebhooks", existing[0].name)
            doc.json = formatted_json
            doc.set_transaction_fields()
            doc.save(ignore_permissions=True)
        else:
            # Insert new document
            new_pw = frappe.get_doc({
                'doctype': 'PayrexxWebhooks',
                'json': formatted_json,
                'uuid': transaction_uuid,
            }).insert(ignore_permissions=True)
