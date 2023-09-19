# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.core.doctype.communication.email import make
from frappe import sendmail
from mvd.mvd.doctype.druckvorlage.druckvorlage import replace_mv_keywords

class SerienEmail(Document):
    def validate(self):
        for empfaenger in self.empfaenger:
            if empfaenger.status == 'E-Mail missing':
                frappe.throw("Dieser Serien E-Mail Datensatz beinhaltet Empfänger ohne gültige E-Mail Adresse.<br>Bitte korrigieren oder entfernen Sie diese zuerst.")

def send_mails():
    allowed_to_send = int(frappe.get_value('MVD Settings', 'MVD Settings', 'serien_email_queue'))
    if allowed_to_send == 1:
        sending_max = int(frappe.get_value('MVD Settings', 'MVD Settings', 'serien_email_per_flush'))
        if sending_max == 0:
            return
        sended = 0
        serien_emails = frappe.db.sql("""SELECT `name` FROM `tabSerien Email` WHERE `status` = 'Sending' ORDER BY `creation` ASC""", as_dict=True)
        for serien_email in serien_emails:
            if sended <= sending_max:
                sm = frappe.get_doc("Serien Email", serien_email.name)
                mail_sbuject = sm.betreff
                for empfaenger in sm.empfaenger:
                    if sended <= sending_max:
                        if empfaenger.status not in ('Send', 'Failed', 'E-Mail missing'):
                            mail_message = replace_mv_keywords(sm.text, empfaenger.mv_mitgliedschaft)
                            sending_status = send_mail_to(empfaenger.email, mail_sbuject, mail_message, empfaenger.mv_mitgliedschaft, sm.sektion_id)
                            if sending_status == 1:
                                empfaenger.status = 'Send'
                                sended += 1
                            else:
                                empfaenger.status = 'Failed'
                    else:
                        sm.save()
                        return
                sm.status = 'Complete'
                sm.save()
            else:
                return

def send_mail_to(email, betreff, message, mv_mitgliedschaft, sektion):
    try:
        comm = make(
            recipients=[email],
            sender=frappe.get_value("Sektion", sektion, "serien_email_absender_adresse"),
            subject=betreff,
            content=message,
            doctype='Mitgliedschaft',
            name=mv_mitgliedschaft,
            attachments=[],
            send_email=False,
            sender_full_name=frappe.get_value("Sektion", sektion, "serien_email_absender_name")
        )["name"]
        
        sendmail(
            recipients=[email],
            sender=frappe.get_value("Sektion", sektion, "serien_email_absender_adresse"),
            subject=betreff,
            message=message,
            as_markdown=False,
            delayed=True,
            reference_doctype='Mitgliedschaft',
            reference_name=mv_mitgliedschaft,
            unsubscribe_method=None,
            unsubscribe_params=None,
            unsubscribe_message=None,
            attachments=[],
            content=None,
            doctype='Mitgliedschaft',
            name=mv_mitgliedschaft,
            reply_to=frappe.get_value("Sektion", sektion, "serien_email_absender_adresse"),
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
            template='mahnung',
            args={
                "message": message,
                "footer": frappe.get_value("Sektion", sektion, "serien_email_footer")
            },
            header=None,
            print_letterhead=False
        )
        
        return 1
    except Exception as err:
        # Mail konnte nicht erstellt werden. Error-log und Überspringen...
        frappe.log_error("{0}\n\n{1}".format(err, frappe.utils.get_traceback() or ''), 'Serien Email Queue Error')
        return False
