# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import io
import zipfile
import frappe
from frappe.model.document import Document
from frappe.core.doctype.communication.email import make
from frappe import sendmail
from frappe.utils import datetime
from frappe.model.naming import make_autoname
from frappe.email.doctype.email_template.email_template import get_email_template
from frappe.utils.pdf import get_pdf
from frappe import attach_print
from frappe.utils import get_url_to_form, get_url
from frappe.utils.file_manager import get_file_path

class Mandat(Document):
    def autoname(self):
        jahr = datetime.date.today().year
        if self.mv_mitgliedschaft:
            sektion = frappe.db.get_value("Mitgliedschaft", self.mv_mitgliedschaft, "sektion_id")
        else:
            sektion = 'MVD'
        self.name = make_autoname("{0}-{1}-.#".format(sektion, jahr))

    def before_save(self):
            if not self.kontaktperson:
                self.status = "Unzugewiesen"

    def on_update(self):
        # Bestätigungs-Email senden
        if (self.typ == "Rechtsschutzversicherung" and 
            self.kontaktperson and 
            not self.bestaetigungs_email_gesendet):
        
            email_sent = send_confirmation_email(self)
            if email_sent:
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
        email_sent = True
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
            email_sent = False
        elif not template_berater:
            frappe.log_error("In Sektion {0} unter Mandat: Kein Template für Kontaktperson hinterlegt.".format(mandat.sektion_id), "Mandat Email Error")
            email_sent = False
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

            # Wir schicken das Stammdatenblatt und die Dokumente der Beratung als Anhang
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
            
            zip_data = get_beratung_zip_attachment(mandat.beratung)
            zip_link_html = ""
            if zip_data:
                zip_file_doc = frappe.get_doc({
                    "doctype": "File",
                    "file_name": zip_data["fname"],
                    "attached_to_doctype": "Mandat",
                    "attached_to_name": mandat.name,
                    "content": zip_data["fcontent"],
                    "is_private": 1
                })
                zip_file_doc.insert(ignore_permissions=True)
                # Falls ZIP kleiner als 8 MB hängen wir es dem Email an
                if len(zip_data["fcontent"]) <= 8 * 1024 * 1024:
                    attachments.append({"fid": zip_file_doc.name})
                    zip_link_html = "Alle Anlagen: Als ZIP-Datei im Anhang"
                else:
                    zip_url = get_url(zip_file_doc.file_url)
                    zip_link_html = """<a href="{0}">Download alle Anlagen als ZIP</a> """.format(zip_url)

            footer_links = """
                <br><br>
                <hr>
                <p style="font-size: 12px; color: #555;">
                    <b>Interne Links für Berater:</b><br>
                    - <a href="{0}">Direkt zur Beratung: {1}</a><br>
                    - <a href="{2}">Direkt zum Mandat: {3}</a><br>
                    - <a href="{4}">Zur Mitgliedschaft: {5}</a><br>
                    - {6}
                </p>
            """.format(link_beratung, mandat.beratung,link_mandat, mandat.name, link_mitglied, mitglied_label, zip_link_html)
            
            full_message = rendered_berater.get("message") + footer_links
            cc_email = sektion_data.get("visierende_person")

            comm = make(
                recipients=recipients,
                sender=absender_format,
                subject=rendered_berater.get("subject"),
                content=full_message,
                doctype='Mandat',
                name=mandat.name,
                send_email=False
            )["name"]
            sendmail(
                recipients=recipients,
                sender=absender_format,
                subject=rendered_berater.get("subject"),
                content=full_message,
                cc=cc_email,
                attachments=attachments,
                reference_doctype=mandat.doctype,
                reference_name=mandat.name,
                unsubscribe_method=None,
                unsubscribe_params=None,
                unsubscribe_message=None,
                communication=comm,
                delayed=True,
                message_id=frappe.get_value("Communication", comm, "message_id")
            )
        
        # --- 2. EMAIL AN MITGLIED ---
        # template_mitglied = sektion_data.get("template_bestaetigung_mitglied")
        # if not mandat.mv_mitgliedschaft or not mitglied_email:
        #     msg = "Mitglied-Bestätigung (Mandat {0}) fehlgeschlagen (E-Mail fehlt oder kein Mitglied hinterlegt).".format(mandat.name)
        #     sendmail(recipients=sektion_data.get("pw_email"), sender="libracore@mvd.mieterverband.ch", 
        #              subject="Fehler: Bestätigung Mandat", content=msg, reference_doctype="Mandat", reference_name=mandat.name)
            
        # elif not template_mitglied:
        #     frappe.log_error("In Sektion {0} unter Mandat: Kein Template für Mitglied hinterlegt.".format(mandat.sektion_id), "Mandat Email Error")
        #     email_sent = False
        # else:
        #     rendered_mitglied = get_email_template(template_mitglied, {"doc": mandat})
        #     comm = make(
        #         recipients=mitglied_email,
        #         sender=absender_format,
        #         subject=rendered_mitglied.get("subject"),
        #         content=rendered_mitglied.get("message"),
        #         doctype='Mandat',
        #         name=mandat.name,
        #         send_email=False
        #     )["name"]
        #     sendmail(
        #         recipients=mitglied_email,
        #         sender=absender_format,
        #         subject=rendered_mitglied.get("subject"),
        #         content=rendered_mitglied.get("message"),
        #         reference_doctype=mandat.doctype,
        #         reference_name=mandat.name,
        #         unsubscribe_method=None,
        #         unsubscribe_params=None,
        #         unsubscribe_message=None,
        #         communication=comm,
        #         delayed=True,
        #         message_id=frappe.get_value("Communication", comm, "message_id")
        #     )
        
        return email_sent
    
    except Exception:
        frappe.log_error(
            title="Mandat Confirmation Email Error",
            message=frappe.get_traceback()
        )
        return False


def get_beratung_zip_attachment(beratung_id):
    files = frappe.get_all("File", filters={
        "attached_to_doctype": "Beratung",
        "attached_to_name": beratung_id
    }, fields=["file_name", "file_url", "file_size"])

    if not files:
        return None
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for f in files:
            try:
                file_path = get_file_path(f.file_name) if not f.file_url.startswith('/') else f.file_url.lstrip('/')
                full_path = frappe.get_site_path(file_path)
                
                with open(full_path, "rb") as content:
                    zip_file.writestr(f.file_name, content.read())
            except Exception as e:
                frappe.log_error("Fehler beim Zippen von {0}: {1}".format(f.file_name, str(e)))

    return {
        "fname": "Anlagen_Beratung_{0}.zip".format(beratung_id),
        "fcontent": zip_buffer.getvalue()
    }


@frappe.whitelist()
def suche_vertrauensanwaeltin(mandat_id, sektion_id):
    anwaelte = frappe.db.get_all("Termin Kontaktperson", 
        filters={"ist_vertrauensanwaeltin": 1, "sektion_id": sektion_id}, 
        fields=["name"]
    )
    if not anwaelte:
        frappe.throw("Es wurden keine Kontaktpersonen mit dem Status 'Vertrauensanwält*in' gefunden.")
    
    anwaelte_liste = [d.name for d in anwaelte]
    raw_recipients = frappe.db.get_all("Termin Kontaktperson Multi User", 
        filters={"parent": ["in", anwaelte_liste]}, 
        fields=["user"]
    )
    
    recipients_list = list(set([d.user for d in raw_recipients if d.user]))
    if not recipients_list:
        frappe.throw("Es wurden keine Vertrauensanwält*innen mit hinterlegter E-Mail-Adresse gefunden.")
        
    recipients_string = ", ".join(recipients_list)
    subject = "Neues unzugewiesenes Mandat verfügbar: {0}".format(mandat_id)

    email_template = frappe.db.get_value("Sektion", sektion_id, "template_suche_vertrauensanwaeltin")

    return {
        "recipients": recipients_string,
        "subject": subject,
        "email_template": email_template or ''
    }