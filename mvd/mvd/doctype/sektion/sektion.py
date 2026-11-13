# -*- coding: utf-8 -*-
# Copyright (c) 2021 - 2026, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Sektion(Document):
    def validate(self):
        if self.legacy_mode != '0':
            if not self.legacy_email:
                frappe.throw("Bitte hinterlegen Sie eine Sektionsspezifische E-Mail Adresse für den E-Mail Beratung Legacy Mode")
        
        self.validate_verrechnungskonten()

    def validate_verrechnungskonten(self):
        for field, root_type in (
                ('firmenverrechnung_verbindlichkeitskonto', 'Liability'),
                ('firmenverrechnung_forderungskonto', 'Asset')):
            name = self.get(field)
            if not name:
                continue

            account = frappe.get_cached_doc('Account', name)
            if (account.company != self.company or account.is_group or account.disabled or
                    account.docstatus == 2 or account.root_type != root_type or
                    account.account_type in ('Bank', 'Cash', 'Receivable', 'Payable')):
                frappe.throw('Das Standardkonto {0} für Firmenverrechnungen muss ein aktives {1}-Bilanzkonto '
                             'der Firma {2} ohne Bank-, Kassen-, Debitoren- oder Kreditorentyp sein.'.format(
                                 name, 'Passiv' if root_type == 'Liability' else 'Aktiv', self.company))
            
            currency = frappe.get_cached_value('Company', self.company, 'default_currency')
            if account.account_currency and account.account_currency != currency:
                frappe.throw('Das Standardkonto {0} für Firmenverrechnungen muss die Firmenwährung {1} verwenden.'.format(name, currency))
    
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
