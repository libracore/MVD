# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint
from frappe.core.doctype.communication.email import make
from frappe import sendmail

class Wohnungsabgabe(Document):
    def send_qa_mail(self):
        if cint(self.qa_mail_sended) != 1:
            if cint(self.disabled_qa_mail) != 1:
                if not self.qa_mail_druckvorlage:
                    frappe.log_error("Die Wohnungsabgabe {0} hat keine hinterlegte Druckvorlage.".format(self.name), "QA-Mail konnte nicht versendet werden")
                    return
                
                recipient = self.e_mail_1 if cint(frappe.get_value("MVD Settings", "MVD Settings", "qa_mail_an_testadresse")) != 1 else frappe.get_value("MVD Settings", "MVD Settings", "qa_mail_testadresse")
                druckvorlage = frappe.get_doc("Druckvorlage", self.qa_mail_druckvorlage)
                subject = frappe.render_template(druckvorlage.e_mail_betreff, {"doc": self})
                message = frappe.render_template(druckvorlage.e_mail_text, {"doc": self})
                comm = make(
                    recipients=[recipient],
                    sender=frappe.get_value("Sektion", self.sektion_id, "serien_email_absender_adresse"),
                    subject=subject, 
                    content=message,
                    doctype='Wohnungsabgabe',
                    name=self.name,
                    send_email=False,
                    sender_full_name=frappe.get_value("Sektion", self.sektion_id, "serien_email_absender_name")
                )["name"]
                
                sendmail(
                    recipients=[recipient],
                    sender="{0} <{1}>".format(frappe.get_value("Sektion", self.sektion_id, "serien_email_absender_name"), frappe.get_value("Sektion", self.sektion_id, "serien_email_absender_adresse")),
                    subject=subject, 
                    message=message,
                    as_markdown=False,
                    delayed=True,
                    reference_doctype='Wohnungsabgabe',
                    reference_name=self.name,
                    unsubscribe_method=None,
                    unsubscribe_params=None,
                    unsubscribe_message=None,
                    attachments=[],
                    content=None,
                    doctype='Wohnungsabgabe',
                    name=self.name,
                    reply_to=frappe.get_value("Sektion", self.sektion_id, "serien_email_absender_adresse"),
                    cc=[],
                    bcc=[],
                    message_id=frappe.get_value("Communication", comm, "message_id"),
                    in_reply_to=None,
                    send_after=None,
                    expose_recipients=None,
                    send_priority=1,
                    communication=comm,
                    retry=1,
                    now=None,
                    read_receipt=None,
                    is_notification=False,
                    inline_images=None,
                    header=None,
                    print_letterhead=False
                )
                self.qa_mail_sended = 1
                self.save()

def qa_mail():
    if cint(frappe.get_value("MVD Settings", "MVD Settings", "qa_mailversand")) == 1:
        affected_wohnungsabgaben = frappe.db.sql("""
            SELECT
                `name`
            FROM `tabWohnungsabgabe`
            WHERE `termin` <= NOW() - INTERVAL 1 DAY
            AND `qa_mail_sended` != 1
            AND `disabled_qa_mail` != 1
        """, as_dict=True)

        for wohnungsabgabe in affected_wohnungsabgaben:
            wa = frappe.get_doc("Wohnungsabgabe", wohnungsabgabe.name)
            wa.send_qa_mail()