# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint
from mvd.mvd.service_plattform.api import send_kampagne_to_sp
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import mitgliedschaft_zuweisen
import json

class Kampagne(Document):
    def before_insert(self):
        if not self.id:
            self.id = frappe.generate_hash(txt="", length=10)
        
        # Normalize newsletter_names to comma-separated string
        names = []

        if isinstance(self.newsletter_names, list):
            names = self.newsletter_names
        elif isinstance(self.newsletter_names, str):
            try:
                # Try to parse JSON string to list
                parsed = json.loads(self.newsletter_names)
                if isinstance(parsed, list):
                    names = parsed
                else:
                    names = self.newsletter_names.split(",")
            except Exception:
                # fallback: assume comma-separated
                names = self.newsletter_names.split(",")

        cleaned_list = [n.strip().replace(" ", "") for n in names if isinstance(n, str)]
        self.newsletter_names = ",".join(cleaned_list)

    def after_insert(self):
        # Mitglied zuordnen
        email = self.email 
        mitglied_hash = self.mitglied_hash
        plz = self.zip_code
        mitglied_info = mitgliedschaft_zuweisen(email=email, mitglied_hash=mitglied_hash, plz=plz)

        if mitglied_info:
            if isinstance(mitglied_info, tuple):
                mitglied_id, sektion_id = mitglied_info
                frappe.db.set_value(self.doctype, self.name, "mitglied", mitglied_id)
                frappe.db.set_value(self.doctype, self.name, "sektion_id", sektion_id)
            elif isinstance(mitglied_info, str):
                frappe.db.set_value(self.doctype, self.name, "sektion_id", mitglied_info)

        # Send to emarsis
        sp_data = {
            "Email": self.email or None,
            "NewsletterNames": self.newsletter_names.split(",") if self.newsletter_names else [],
            "CampaignTriggerCode": str(self.campaign_trigger_code) if self.campaign_trigger_code else None,
            "SubscribedOverPledge": False if cint(self.subscribed_over_pledge) != 1 else True,
            "Zip_code": self.zip_code or 0,
            "Last_name": self.last_name or None,
            "First_name": self.first_name or None,
            "Anrede": self.anrede or None,
            "LangCode": self.lang_code or "de",
            "Nl_abo": False if cint(self.nl_abo) != 1 else True,
            "Quelle": self.quelle or None
        }

        if cint(frappe.db.get_value("MVD Settings", "MVD Settings", "suspend_kampagne_to_sp")) != 1:
            send_kampagne_to_sp(sp_data, id=self.name)
