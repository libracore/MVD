# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint
from mvd.mvd.service_plattform.api import send_kampagne_to_sp

class Kampagne(Document):
    def after_insert(self):
        sp_data = {
            "Email": self.email or None,
            "NewsletterName": self.newsletter_name or None,
            "CampaignTriggerCode": self.campaign_trigger_code or None,
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
