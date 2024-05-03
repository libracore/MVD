# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.core.doctype.communication.email import make
from frappe import sendmail, get_print
from frappe.utils import cint
from mvd.mvd.doctype.druckvorlage.druckvorlage import replace_mv_keywords

class MVDEmailQueue(Document):
    def validate(self):
        # pre send sended check
        sended = 0
        for mahnung_row in self.mahnungen:
            if mahnung_row.status == 'Send':
                sended += 1
        if sended == len(self.mahnungen):
            self.status = 'Send'
        elif sended > 0:
            self.status = 'Partially send'
        else:
            self.status = 'Not send'
        
        # send if necessary and allowed
        allowed_to_send = cint(frappe.get_value('MVD Settings', 'MVD Settings', 'email_queue'))
        if cint(self.blocked) == 1:
            allowed_to_send = False
        if self.status != 'Send' and allowed_to_send == 1:
            send_counter = 0
            max_mails = int(frappe.get_value('MVD Settings', 'MVD Settings', 'emails_per_flush'))
            for mahnung_row in self.mahnungen:
                if send_counter < max_mails:
                    if mahnung_row.status == 'Not send':
                        try:
                            mahnung = frappe.get_doc("Mahnung", mahnung_row.mahnung)
                            email_vorlage = self.email_vorlage
                            betreff = self.betreff
                            message = self.message
                            if self.email_vorlage:
                                if mahnung.mv_mitgliedschaft:
                                    mitgliedschaft = mahnung.mv_mitgliedschaft
                                else:
                                    mitgliedschaft = mahnung.mv_kunde
                                email_vorlage = frappe.get_doc("Druckvorlage", email_vorlage)
                                betreff = replace_mv_keywords(email_vorlage.e_mail_betreff, mitgliedschaft, mahnung=mahnung.name, idx=0, sinv=mahnung.sales_invoices[0].sales_invoice)
                                message = replace_mv_keywords(email_vorlage.e_mail_text, mitgliedschaft, mahnung=mahnung.name, idx=0, sinv=mahnung.sales_invoices[0].sales_invoice)
                            attachments = [frappe.attach_print("Mahnung", mahnung.name, file_name=mahnung.name, print_format='Mahnung')]
                            comm = make(
                                recipients=get_recipients(mahnung),
                                sender=frappe.get_value("Sektion", mahnung.sektion_id, "mahnung_absender_adresse"),
                                subject=betreff,
                                content=message,
                                doctype='Mahnung',
                                name=mahnung.name,
                                attachments=attachments,
                                send_email=False,
                                sender_full_name=frappe.get_value("Sektion", mahnung.sektion_id, "mahnung_absender_name")
                            )["name"]
                            
                            sendmail(
                                recipients=get_recipients(mahnung),
                                sender="{0} <{1}>".format(frappe.get_value("Sektion", mahnung.sektion_id, "mahnung_absender_name"), frappe.get_value("Sektion", mahnung.sektion_id, "mahnung_absender_adresse")),
                                subject=betreff,
                                message=message,
                                as_markdown=False,
                                delayed=True,
                                reference_doctype='Mahnung',
                                reference_name=mahnung.name,
                                unsubscribe_method=None,
                                unsubscribe_params=None,
                                unsubscribe_message=None,
                                attachments=attachments,
                                content=None,
                                doctype='Mahnung',
                                name=mahnung.name,
                                reply_to=frappe.get_value("Sektion", mahnung.sektion_id, "mahnung_absender_adresse"),
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
                                    "footer": frappe.get_value("Sektion", mahnung.sektion_id, "footer")
                                },
                                header=None,
                                print_letterhead=False
                            )
                            mahnung_row.status = 'Send'
                        except Exception as err:
                            # Mail konnte nicht erstellt werden. Error-log und Überspringen...
                            frappe.log_error("{0}\n\n{1}".format(err, frappe.utils.get_traceback() or ''), 'MVD Email Queue Error')
                            mahnung_row.status = 'Failed'
                            pass
                        # wichtig: muss nach "except" sein, damit der Fehlerhafte übersprungen wird!
                        send_counter += 1
        
        # post send sended check
        sended = 0
        for mahnung_row in self.mahnungen:
            if mahnung_row.status == 'Send':
                sended += 1
        if sended == len(self.mahnungen):
            self.status = 'Send'
        elif sended > 0:
            self.status = 'Partially send'
        else:
            self.status = 'Not send'

def get_recipients(mahnung):
    if mahnung.mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mahnung.mv_mitgliedschaft)
        if mitgliedschaft.abweichende_rechnungsadresse and mitgliedschaft.unabhaengiger_debitor and mitgliedschaft.rg_e_mail:
            return [mitgliedschaft.rg_e_mail]
        else:
            return [mitgliedschaft.e_mail_1]
    else:
        kunde = frappe.get_doc("Kunden", mahnung.mv_kunde)
        if kunde.abweichende_rechnungsadresse and kunde.unabhaengiger_debitor and kunde.rg_e_mail:
            return [kunde.rg_e_mail]
        else:
            return [kunde.e_mail]

def mvd_mail_flush():
    mail_queues = frappe.db.sql("""SELECT `name` FROM `tabMVD Email Queue` WHERE `status` != 'Send' AND `blocked` != 1 ORDER BY `creation` ASC LIMIT 1""", as_dict=True)
    if len(mail_queues) > 0:
        queue = frappe.get_doc("MVD Email Queue", mail_queues[0].name)
        queue.save()
