# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint
from mvd.mvd.service_plattform.api import send_kampagne_to_sp
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import mitgliedschaft_zuweisen

class Kampagne(Document):
    def after_insert(self):
        # Mitglied zuordnen
        email = self.email 
        mitglied_hash = self.mitglied_hash
        mitglied_info = mitgliedschaft_zuweisen(email=email, mitglied_hash=mitglied_hash)

        if mitglied_info:
            mitglied_id, sektion_id = mitglied_info
            frappe.db.set_value(self.doctype, self.name, "mitglied", mitglied_id)
            frappe.db.set_value(self.doctype, self.name, "sektion", sektion_id)

        # Send to emarsis
        sp_data = {
            "Email": self.email or None,
            "NewsletterName": self.newsletter_name or None,
            "CampaignTriggerCode": cint(self.campaign_trigger_code) if self.campaign_trigger_code else None,
            "SubscribedOverPledge": False if cint(self.subscribed_over_pledge) != 1 else True,
            "Zip_code": self.zip_code or 0,
            "Last_name": self.last_name or None,
            "First_name": self.first_name or None,
            "Anrede": self.anrede or None,
            "LangCode": self.lang_code or "de",
            "Nl_abo": False if cint(self.nl_abo) != 1 else True,
            "Quelle": self.quelle or None
        }
        send_kampagne_to_sp(sp_data)
