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
from frappe.utils import get_url_to_form

class Mandat(Document):
    def on_update(self):
        # Bestätigungs-Email senden
        if (self.typ == "Rechtsschutzversicherung" and 
            self.kontaktperson and 
            not self.bestaetigungs_email_gesendet):
        
            send_confirmation_email(self)
            self.db_set("bestaetigungs_email_gesendet", 1)

@frappe.whitelist()
def create_mandat(sektion, beratung, mitglied, berater_in, typ, bemerkung, persoenliche_bemerkung):
    mandat = frappe.new_doc("Mandat")

    mandat.mv_mitgliedschaft = mitglied
    mandat.sektion_id = sektion
    mandat.beratung = beratung
    mandat.kontaktperson = berater_in
    mandat.typ = typ
    mandat.bemerkung = bemerkung
    mandat.persoenliche_bemerkung = persoenliche_bemerkung

    mandat.insert(ignore_permissions=True)

    return mandat.name

def send_confirmation_email(mandat):
    try:
        raw_recipients = frappe.db.get_all("Termin Kontaktperson Multi User", 
            filters={"parent": mandat.kontaktperson}, 
            fields=["user"]
        )
        recipients = [d.user for d in raw_recipients if d.user]
        
        sektion_data = frappe.db.get_value("Sektion", mandat.sektion_id, 
            ["visierende_person", 
             "template_bestaetigung_kontaktperson", 
             "template_bestaetigung_mitglied",
             "legacy_mail_absender_mail", 
             "legacy_mail_absende_name",
             "pw_email"], as_dict=True)
        
        mitglied_email = frappe.db.get_value("Mitgliedschaft", mandat.mv_mitgliedschaft, "e_mail_1")

        # Absender definieren
        absender_format = "{0} <{1}>".format(
            sektion_data.get("legacy_mail_absende_name") or "Mieterverband", 
            sektion_data.get("legacy_mail_absender_mail")
        )

        # --- 1. EMAIL AN BERATER (mit CC und Attachment) ---
        template_berater = sektion_data.get("template_bestaetigung_kontaktperson")

        if not recipients:
            frappe.log_error("Keine Empfänger für Kontaktperson {0} gefunden.".format(mandat.kontaktperson), "Mandat Email Error")
        elif not template_berater:
            frappe.log_error("In Sektion {0} unter Mandat: Kein Template für Kontaktperson hinterlegt.".format(mandat.sektion_id), "Mandat Email Error")
        else:
            rendered_berater = get_email_template(template_berater, {"doc": mandat})

            link_beratung = get_url_to_form("Beratung", mandat.beratung)
            link_mandat = get_url_to_form("Mandat", mandat.name)
            if mandat.mv_mitgliedschaft:
                link_mitglied = get_url_to_form("Mitgliedschaft", mandat.mv_mitgliedschaft)
                mitglied_label = str(mandat.mv_mitgliedschaft)
            else:
                link_mitglied = "#"
                mitglied_label = "Keine Mitgliedschaft verknüpft"

            footer_links = """
                <br><br>
                <hr>
                <p style="font-size: 12px; color: #555;">
                    <b>Interne Links für Berater:</b><br>
                    - <a href="{0}">Direkt zur Beratung: {1}</a><br>
                    - <a href="{2}">Direkt zum Mandat: {3}</a><br>
                    - <a href="{4}">Zur Mitgliedschaft: {5}</a>
                </p>
            """.format(link_beratung, mandat.beratung,link_mandat, mandat.name, link_mitglied, mitglied_label)
            
            full_message = rendered_berater.get("message") + footer_links

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
                sender=absender_format,
                subject=rendered_berater.get("subject"),
                content=full_message,
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
        if not mandat.mv_mitgliedschaft or not mitglied_email:
            msg = "Mitglied-Bestätigung (Mandat {0}) fehlgeschlagen (E-Mail fehlt oder kein Mitglied hinterlegt).".format(mandat.name)
            sendmail(recipients=sektion_data.get("pw_email"), sender="libracore@mvd.mieterverband.ch", 
                     subject="Fehler: Bestätigung Mandat", content=msg, reference_doctype="Mandat", reference_name=mandat.name)
            
        elif not template_mitglied:
            frappe.log_error("In Sektion {0} unter Mandat: Kein Template für Mitglied hinterlegt.".format(mandat.sektion_id), "Mandat Email Error")

        else:
            rendered_mitglied = get_email_template(template_mitglied, {"doc": mandat})
            
            sendmail(
                recipients=mitglied_email,
                sender=absender_format,
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