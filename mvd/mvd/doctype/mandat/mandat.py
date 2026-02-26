# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import sendmail
from frappe.email.doctype.email_template.email_template import get_email_template
from frappe.utils.pdf import get_pdf
from frappe import attach_print

class Mandat(Document):
    pass

@frappe.whitelist()
def create_mandat(sektion, beratung, mitglied, berater_in, typ, bemerkung):
    mandat = frappe.new_doc("Mandat")

    mandat.mv_mitgliedschaft = mitglied
    mandat.sektion_id = sektion
    mandat.beratung = beratung
    mandat.kontaktperson = berater_in
    mandat.typ = typ
    mandat.bemerkung = bemerkung

    mandat.insert(ignore_permissions=True)
    if mandat.typ == "Rechtsschutzversicherung":
        send_confirmation_email(mandat)

    return mandat.name

def send_confirmation_email(mandat):
    if not mandat.kontaktperson:
        return
    try:
        raw_recipients = frappe.db.get_all("Termin Kontaktperson Multi User", 
            filters={"parent": mandat.kontaktperson}, 
            fields=["user"]
        )
        recipients = [d.user for d in raw_recipients if d.user]
        
        sektion_data = frappe.db.get_value("Sektion", mandat.sektion_id, 
            ["visierende_person", "template_bestaetigung_kontaktperson", "template_bestaetigung_mitglied"], as_dict=True)
        
        mitglied_email = frappe.db.get_value("Mitgliedschaft", mandat.mv_mitgliedschaft, "e_mail_1")

        # --- 1. EMAIL AN BERATER (mit CC und Attachment) ---
        template_berater = sektion_data.get("template_bestaetigung_kontaktperson")

        if not recipients:
            frappe.log_error("Keine Empfänger für Kontaktperson {0} gefunden.".format(mandat.kontaktperson), "Mandat Email Error")
        elif not template_berater:
            frappe.log_error("In Sektion {0} unter Mandat: Kein Template für Kontaktperson hinterlegt.".format(mandat.sektion_id), "Mandat Email Error")
        else:
            rendered_berater = get_email_template(template_berater, {"doc": mandat})

            # Wir schicken das Stammdatenblatt als Anhang
            attachments = []
            if mandat.mv_mitgliedschaft:
                pdf_content = frappe.get_print("Mitgliedschaft", mandat.mv_mitgliedschaft, "Stammdatenblatt", as_pdf=True)
                filename = "Stammdatenblatt_{0}.pdf".format(mandat.mv_mitgliedschaft)
                
                file_doc = frappe.get_doc({
                    "doctype": "File",
                    "file_name": filename,
                    "attached_to_doctype": "Mandat",
                    "attached_to_name": mandat.name,
                    "content": pdf_content,
                    "is_private": 1
                })
                file_doc.insert(ignore_permissions=True)
                attachments.append({"fid": file_doc.name})
        
            cc_email = sektion_data.get("visierende_person")

            sendmail(
                recipients=recipients,
                subject=rendered_berater.get("subject"),
                content=rendered_berater.get("message"),
                cc=cc_email,
                attachments=attachments,
                reference_doctype=mandat.doctype,
                reference_name=mandat.name,
                now=False,
                unsubscribe_method=None,
                unsubscribe_params=None,
                unsubscribe_message=None,
            )
        
        # --- 2. EMAIL AN MITGLIED ---
        template_mitglied = sektion_data.get("template_bestaetigung_mitglied")
        
        if not mitglied_email:
            frappe.log_error("Beim Mitglied {0} ist keine Email hinterlegt.".format(mandat.mv_mitgliedschaft), "Mandat Email Error")
        elif not template_mitglied:
            frappe.log_error("In Sektion {0} unter Mandat: Kein Template für Mitglied hinterlegt.".format(mandat.sektion_id), "Mandat Email Error")
        else:
            rendered_mitglied = get_email_template(template_mitglied, {"doc": mandat})
            
            sendmail(
                recipients=mitglied_email,
                subject=rendered_mitglied.get("subject"),
                content=rendered_mitglied.get("message"),
                reference_doctype=mandat.doctype,
                reference_name=mandat.name,
                now=False,
                unsubscribe_method=None,
                unsubscribe_params=None,
                unsubscribe_message=None,
            )
            
    except Exception:
        frappe.log_error(
            title="Mandat Confirmation Email Error",
            message=frappe.get_traceback()
        )