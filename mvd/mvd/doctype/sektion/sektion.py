# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Sektion(Document):
    def validate(self):
        if self.legacy_mode != '0':
            if not self.legacy_email:
                frappe.throw("Bitte hinterlegen Sie eine Sektionsspezifische E-Mail Adresse für den E-Mail Beratung Legacy Mode")
            # disabled aufgrund #1646
            # if self.legacy_mode == '2' or self.legacy_mode == '3':
            #     frappe.throw("Der Legacy Mode 2 und 3 steht zur Zeit nicht zur Verfügung.")
    
    def on_update(self):
        self.sync_auto_reply_to_email_account()

    def sync_auto_reply_to_email_account(self):
            if not self.legacy_mail_absender_mail or not self.emailberatung_email_text:
                return
            
            email_account_name = frappe.db.get_value("Email Account", 
                {"email_id": self.legacy_mail_absender_mail}, "name")

            if email_account_name:
                email_doc = frappe.get_doc("Email Account", email_account_name)
                
                if email_doc.auto_reply_message != self.emailberatung_email_text:
                    email_doc.auto_reply_message = self.emailberatung_email_text
                    email_doc.enable_auto_reply = 1
                    email_doc.save(ignore_permissions=True)