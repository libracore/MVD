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
        """
        Versuche dem Payrexx Eintrag eine Mitgliedschaft zuzuordnen über 
            - den Mitglied Hash
            - die Email
        Über die PLZ wird immer eine Sektion zugeordnet
        """
        email = self.email 
        mitglied_hash = self.mitglied_hash
        plz = self.plz

        mitglied_info = mitgliedschaft_zuweisen(email=email, mitglied_hash=mitglied_hash, zip_code=plz)

        # Sektion wird primär über die payrexx_instance_uuid zugeordnet
        if self.payrexx_instance_uuid:
            results = frappe.get_all(
                "Sektion",
                filters={"payrexx_instance_uuid": self.payrexx_instance_uuid},
                fields=["title"]
            )
            if len(results) == 1:
                self.sektion_id = results[0]["title"]

        if mitglied_info:
            if isinstance(mitglied_info, tuple):
                self.mitglied_id = mitglied_info[0]
                if not self.sektion_id:
                    self.sektion_id = mitglied_info[1]
            elif isinstance(mitglied_info, str) and not self.sektion_id:
                self.sektion_id = mitglied_info
        # Fallback       
        if not self.sektion_id:
            self.sektion_id = "MVD"

        self.save(ignore_permissions=True)
 

    def set_transaction_fields(self):
        if not self.json:
            return

        try:
            payload = json.loads(self.json)
            transaction = payload.get("transaction", {})
        except Exception as e:
            frappe.log_error("Invalid Payrexx JSON: {0}".format(str(e)), "PayrexxWebhooks")
            return

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
            "payrexx_instance_name": lambda t: t.get("instance", {}).get("name"),
            "payrexx_instance_uuid": lambda t: t.get("instance", {}).get("uuid"),
            "original_transaction_uuid": lambda t:t.get("originalTransactionUuid"),
            "reference_id": lambda t: t.get("invoice", {}).get("referenceId"),
        }

        for field, getter in field_map.items():
            value = getter(transaction)
            setattr(self, field, value)

        # Custom logic to extract mitglied_hash because it's in a list
        mitglied_hash = None
        for field in transaction.get("invoice", {}).get("custom_fields", []):
            if "mitglied_hash" in field:
                mitglied_hash = field.get("mitglied_hash")
                break
        self.mitglied_hash = mitglied_hash


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
