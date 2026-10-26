# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.email.email_body import get_message_id
from frappe.utils import cint, flt, getdate
import re
from mvd.mvd.utils.nextcloud import NCSettings
import os

def resave_mitgliedschaft(sinv, event):
    if sinv.mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", sinv.mv_mitgliedschaft)
        mitgliedschaft.zuzug_massendruck = 0
        mitgliedschaft.zuzugs_rechnung = None
        mitgliedschaft.letzte_bearbeitung_von = 'SP'
        mitgliedschaft.save()

def todo_permissions(todo, event):
    try:
        if frappe.db.exists("Sektion", {'virtueller_user': todo.owner}):
            sektion = frappe.db.get_value("Sektion", {"virtueller_user": todo.owner}, ["name"])
            users = frappe.get_all('User Permission', fields='user', filters={'for_value': sektion, 'allow': 'Sektion', 'is_default': 1}, limit=100, distinct=True, ignore_ifnull=True)
            for user in users:
                frappe.share.add('ToDo', todo.name, user=user.user, read=1, write=1, flags={'ignore_share_permission': True})
        else:
            if frappe.db.exists("ToDo Gruppe", todo.owner):
                todo_gruppe_user = frappe.db.sql("""SELECT `user` FROM `tabToDo Gruppen Multiselect` WHERE `parent` = '{owner}'""".format(owner=todo.owner), as_dict=True)
                if len(todo_gruppe_user) > 0:
                    for user in todo_gruppe_user:
                        frappe.share.add('ToDo', todo.name, user=user.user, read=1, write=1, flags={'ignore_share_permission': True})
                else:
                    users = frappe.share.get_users('ToDo', todo.name)
                    for user in users:
                        frappe.share.remove("ToDo", todo.name, user.user, flags={'ignore_share_permission': True, 'ignore_permissions': True})
            else:
                users = frappe.share.get_users('ToDo', todo.name)
                for user in users:
                    frappe.share.remove("ToDo", todo.name, user.user, flags={'ignore_share_permission': True, 'ignore_permissions': True})
    except:
        pass
    
    if todo.status == 'Open':
        if todo.reference_type == 'Beratung':
            frappe.db.set_value("Beratung", todo.reference_name, "zuweisung", 1)
    else:
        if todo.reference_type == 'Beratung':
            beratung = frappe.get_doc("Beratung", todo.reference_name)
            if len(beratung.get_assigned_users()) > 0:
                frappe.db.set_value("Beratung", todo.reference_name, "zuweisung", 1)
            else:
                frappe.db.set_value("Beratung", todo.reference_name, "zuweisung", 0)

def unlink_fr(sinv, event):
    hv_fr = frappe.db.sql("""SELECT `name` FROM `tabFakultative Rechnung` WHERE `docstatus` = 1 AND `sales_invoice` = '{sinv}'""".format(sinv=sinv.name), as_dict=True)
    if len(hv_fr) > 0:
        if len(hv_fr) > 1:
            frappe.throw("Es gibt mehere FR-Rechnungen zu dieser Rechnung. Bitte kontaktieren Sie den Support.")
        else:
            update_fr = frappe.db.sql("""UPDATE `tabFakultative Rechnung` SET `sales_invoice` = '' WHERE `name` = '{hv_fr}'""".format(hv_fr=hv_fr[0].name), as_list=True)
            frappe.db.commit()
            sinv.zugehoerige_fr = hv_fr=hv_fr[0].name

def relink_fr(sinv, event):
    skip = False
    if sinv.rechnungs_jahresversand:
        from frappe.utils.data import add_to_date
        ref_date = add_to_date(date=sinv.creation, hours=12)
        if sinv.modified < ref_date:
            skip = True
    if not skip:
        if sinv.zugehoerige_fr:
            update_fr = frappe.db.sql("""UPDATE `tabFakultative Rechnung` SET `sales_invoice` = '{sinv}' WHERE `name` = '{hv_fr}'""".format(sinv=sinv.name, hv_fr=sinv.zugehoerige_fr), as_list=True)
            frappe.db.commit()
            sinv.zugehoerige_fr = None

def remove_admin_and_guest_mails(self, event):
    recipients_to_remove = [
        'Administrator',
        'admin@example.com',
        'guest@example.com',
        'Administrator <joel@msmr.ch>',
        'updatech API <updatech@api.live>'
    ]
    cc_to_remove = [
        'Administrator &lt;joel@msmr.ch&gt;',
        '"update.ch API" &lt;updatech@api.live&gt;',
        'Guest &lt;guest@example.com&gt;'
    ]
    if self.recipients:
        removed_row = False
        for recipient in self.recipients:
            if recipient.recipient in recipients_to_remove:
                # entferne Admin/Guest/updateAPI Zeile
                self.remove(recipient)
                removed_row = True
        if removed_row:
            if len(self.recipients) > 0:
                # check for CC's
                for cc in cc_to_remove:
                    self.show_as_cc = self.show_as_cc.replace(cc, "")
                self.save()
            else:
                self.delete()

def check_manual_address(sinv, event):
    if cint(sinv.manuelle_adresseingabe) == 1:
        sinv.manuelle_adresse = '{0}\n{1}{2} {3}\n{4}-{5} {6}'.format(sinv.ma_name, "{0}\n".format(sinv.ma_adressen_zusatzzeile) if sinv.ma_adressen_zusatzzeile else '', sinv.ma_strasse, sinv.ma_nummer, sinv.ma_laendercode, sinv.ma_plz, sinv.ma_ort)

def pe_after_submit_hooks(pe, event):
    from mvd.mvd.doctype.mitgliedschaft.finance_utils import check_mitgliedschaft_in_pe
    check_mitgliedschaft_in_pe(pe)
    send_zahlungsbestaetigungen(pe)

def send_zahlungsbestaetigungen(pe):
    if pe.payment_type != 'Receive' or not pe.posting_date:
        return
    zahlungsdatum = getdate(pe.posting_date)

    # Alle referenzierten Rechnungen
    rechnungsnamen = list(set(
        row.reference_name for row in pe.references
        if row.reference_doctype == 'Sales Invoice' and row.reference_name and flt(row.allocated_amount) > 0
    ))
    if not rechnungsnamen:
        return

    # Alle relevanten Daten der referenzierten Rechnungen
    rechnungen = frappe.get_all(
        'Sales Invoice',
        filters={
            'name': ['in', rechnungsnamen],
            'docstatus': 1,
            'status': 'Paid'
        },
        fields=['name', 'sektion_id', 'mrj', 'mv_mitgliedschaft']
    )
    sektionen = list(set(row.sektion_id for row in rechnungen if row.sektion_id))
    if not sektionen:
        return

    # Alle sektionsspezifischen E-Mail Regeln
    regeln = frappe.get_all(
        'Zahlungsbestaetigung per Mail',
        filters={
            'parent': ['in', sektionen],
            'parenttype': 'Sektion',
            'parentfield': 'zahlungsbestaetigung_per_mail',
            'e_mail_ausloesen_bis': ['>=', zahlungsdatum]
        },
        fields=['parent', 'aus_mrj', 'e_mail_vorlage'],
        order_by='e_mail_ausloesen_bis asc, idx asc'
    )

    passende_regeln = {}
    for regel in regeln:
        key = (regel.parent, bool(cint(regel.aus_mrj)))
        # Der früheste passende Stichtag gewinnt, bei gleichem Datum der erste Eintrag
        if key not in passende_regeln:
            passende_regeln[key] = regel

    absender = {}
    vorlagen = {}
    mitglieder = {}
    mitglied_dokumente = {}
    for sinv in rechnungen:
        regel = passende_regeln.get((sinv.sektion_id, bool(sinv.mrj)))
        if not regel or not regel.e_mail_vorlage or not sinv.mv_mitgliedschaft:
            # Keine passende Regel, kein Email Template oder keine Mitgliedschaft -> skip
            continue

        if sinv.mv_mitgliedschaft not in mitglieder:
            mitglieder[sinv.mv_mitgliedschaft] = frappe.db.get_value('Mitgliedschaft', sinv.mv_mitgliedschaft, ['abweichende_rechnungsadresse', 'unabhaengiger_debitor', 'rg_e_mail', 'e_mail_1'], as_dict=True)
        mitglied = mitglieder[sinv.mv_mitgliedschaft]
        if not mitglied:
            # Keine Mitgliedschaft -> skip
            continue

        recipient = mitglied.rg_e_mail if cint(mitglied.abweichende_rechnungsadresse) and cint(mitglied.unabhaengiger_debitor) == 1 else mitglied.e_mail_1
        if not recipient:
            # Kein Empfänger -> Skip
            continue

        if regel.e_mail_vorlage not in vorlagen:
            vorlagen[regel.e_mail_vorlage] = frappe.db.get_value('Email Template', regel.e_mail_vorlage, ['sektion_id', 'subject', 'response'], as_dict=True)
        vorlage = vorlagen[regel.e_mail_vorlage]
        if not vorlage or vorlage.sektion_id != sinv.sektion_id or not vorlage.response:
            # Kein passendes E-Mail Template -> skip
            continue

        if sinv.sektion_id not in absender:
            absender[sinv.sektion_id] = frappe.db.get_value('Sektion', sinv.sektion_id, ['serien_email_absender_name', 'serien_email_absender_adresse'], as_dict=True)
        sender = absender[sinv.sektion_id]
        if not sender or not sender.serien_email_absender_adresse:
            # Kein Absender -> Skip
            continue

        try:
            subject = vorlage.subject or 'Zahlungsbestätigung'
            message = vorlage.response

            # Anwendung Jinja wenn vorhanden
            if any('{{' in text or '{%' in text for text in (subject, message)):
                rechnung = frappe.get_doc('Sales Invoice', sinv.name)
                context = dict(rechnung.as_dict(), doc=rechnung, payment_entry=pe)
                if '{{' in subject or '{%' in subject:
                    subject = frappe.render_template(subject, context)
                if '{{' in message or '{%' in message:
                    message = frappe.render_template(message, context)
            
            # Anwendung MV Platzhalter wenn vorhanden
            if '%%' in subject or '%%' in message:
                from mvd.mvd.doctype.druckvorlage.druckvorlage import replace_mv_keywords
                if sinv.mv_mitgliedschaft not in mitglied_dokumente:
                    mitglied_dokumente[sinv.mv_mitgliedschaft] = frappe.get_doc('Mitgliedschaft', sinv.mv_mitgliedschaft)
                mitglied_doc = mitglied_dokumente[sinv.mv_mitgliedschaft]
                subject = replace_mv_keywords(subject, mitglied_doc)
                message = replace_mv_keywords(message, mitglied_doc)

            # Erstellung Kommunikation damit das Mail in der Timeline der Sales Invoice angezeigt wird
            communication = frappe.get_doc({
                'doctype': 'Communication',
                'communication_type': 'Communication',
                'communication_medium': 'Email',
                'sent_or_received': 'Sent',
                'sender': sender.serien_email_absender_adresse,
                'sender_full_name': sender.serien_email_absender_name,
                'recipients': recipient,
                'subject': subject,
                'content': message,
                'reference_doctype': 'Sales Invoice',
                'reference_name': sinv.name,
                'message_id': get_message_id().strip(' <>')
            }).insert(ignore_permissions=True)

            frappe.sendmail(
                sender='{0} <{1}>'.format(sender.serien_email_absender_name or '', sender.serien_email_absender_adresse),
                recipients=[recipient],
                message=message,
                subject=subject,
                reply_to=sender.serien_email_absender_adresse,
                reference_doctype='Sales Invoice',
                reference_name=sinv.name,
                communication=communication.name,
                message_id=communication.message_id
            )
        except Exception:
            frappe.log_error('{0}\n\nZahlung: {1}\nRechnung: {2}\nVorlage: {3}'.format(frappe.get_traceback(), pe.name, sinv.name, regel.e_mail_vorlage), 'Zahlungsbestätigung per Mail failed')

def email_queue_after_insert_hook(queue, event):
    remove_admin_and_guest_mails(queue, event)
    # mrj_mail_utf_replace(queue, event) --> Obsolet!

# def mrj_mail_utf_replace(queue, event):
#     if "From: =?utf-8?q?MV_Z=C3=BCrich_=3Cno-reply=40mvd=2Emieterverband=2Ech=3E?=" in queue.message:
#         queue.message = queue.message.replace("From: =?utf-8?q?MV_Z=C3=BCrich_=3Cno-reply=40mvd=2Emieterverband=2Ech=3E?=", "From: =?utf-8?q?MV_Z=C3=BCrich?= <no-reply@mvd.mieterverband.ch>")

def sync_file_to_nextcloud(file, event):
    '''
    ACHTUNG Konfliktpotenzial
    Unbedingt mvd.mvd.doctype.beratung.beratung.sync_mail_attachements prüfen/abstimmen!
    '''
    def delete_local_file_from_disk(file_doc):
        """
        Löscht die physische Datei eines Frappe File-Dokuments vom lokalen Dateisystem,
        aber lässt das File-Dokument in der DB bestehen.

        Erwartet ein geladenes File-Dokument.
        """
        if file_doc.doctype != "File":
            return

        if not file_doc.file_url:
            return

        # Nur lokale Dateien löschen, keine externen URLs
        if file_doc.file_url.startswith("http://") or file_doc.file_url.startswith("https://"):
            return

        file_path = frappe.get_site_path(file_doc.file_url.lstrip("/"))

        if os.path.exists(file_path) and os.path.isfile(file_path):
            os.remove(file_path)
            return

        return

    def sanitize_windows_filename(filename):
        '''
            Sicherstellung Windows-kompatibeler Dateiname
        '''
        WINDOWS_RESERVED_NAMES = {
            "CON", "PRN", "AUX", "NUL",
            "COM1", "COM2", "COM3", "COM4", "COM5",
            "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
            "LPT6", "LPT7", "LPT8", "LPT9",
        }

        # Ungültige Zeichen ersetzen
        filename = re.sub(r'[<>:"/\\|?*#%&{}~\x00-\x1F]', "_", filename)

        # Keine Punkte oder Leerzeichen am Ende
        filename = filename.rstrip(" .")

        # Leerer Name?
        if not filename:
            filename = "_"

        # Reservierte Namen prüfen (ohne Datei-Endung)
        parts = filename.rsplit(".", 1)
        basename = parts[0]

        if basename.upper() in WINDOWS_RESERVED_NAMES:
            filename = "_" + filename

        return filename

    sektion = None
    folder_path = None

    # Liegt bereits auf der Nextcloud oder soll zwingend lokal gehalten werden -> Abbruch
    if file.nc_remote_path or file.flags.keep_local_for_rsv_zip:
        return

    # -------------------------------------------------------------------------
    # File gehört direkt zu einer Mitgliedschaft
    # -------------------------------------------------------------------------
    if file.attached_to_doctype == 'Mitgliedschaft':
        mitgliedschaft = frappe.get_doc(
            "Mitgliedschaft",
            file.attached_to_name
        )

        sektion = mitgliedschaft.sektion_id

        if not sektion:
            return

        ncs = NCSettings(sektion)

        if not ncs.IS_ENABLED:
            return

        # Zentrale Pfadermittlung:
        # - Mitglied       -> Mitglieder/<Gruppe>/<Mitgliednummer>
        # - Interessent*in -> Interessenten/<Mitgliedschaft>
        folder_path = ncs.get_mitgliedschaft_path(
            mitgliedschaft
        )

        if not folder_path:
            return

    # -------------------------------------------------------------------------
    # File gehört zu einer Beratung
    # -------------------------------------------------------------------------
    if file.attached_to_doctype == 'Beratung':
        beratung = frappe.get_doc(
            "Beratung",
            file.attached_to_name
        )

        sektion = beratung.sektion_id

        if not sektion:
            return

        ncs = NCSettings(sektion)

        if not ncs.IS_ENABLED:
            return

        # Beratung mit Mitgliedschaft
        if beratung.mv_mitgliedschaft:
            base_mitglied_beratung = ncs.get_mitgliedschaft_beratung_path(
                beratung.mv_mitgliedschaft
            )

            if not base_mitglied_beratung:
                return

            folder_path = "{0}/{1}".format(
                base_mitglied_beratung,
                beratung.name
            )

        # Beratung ohne Mitgliedschaft
        else:
            folder_path = "{0}/{1}".format(
                ncs.BASE_BERATUNG,
                beratung.name
            )

    # -------------------------------------------------------------------------
    # File gehört zu einem RSV-Fall
    # -------------------------------------------------------------------------
    if file.attached_to_doctype == 'RSVMitglied':
        rsvmitglied = frappe.get_doc('RSVMitglied', file.attached_to_name)
        sektion = rsvmitglied.sektion_id
        ncs = NCSettings(sektion)
        if not ncs.IS_ENABLED:
            return
        folder_path = ncs.get_rsvmitglied_path(rsvmitglied)

    # -------------------------------------------------------------------------
    # File auf Nextcloud hochladen
    # -------------------------------------------------------------------------
    if sektion and folder_path:
        file_content = file.get_content()  # liefert Bytes
        file_name = sanitize_windows_filename(file.file_name)

        uploaded_files = ncs.upload_files(
            folder_path,
            [(file_name, file_content)]
        )

        if len(uploaded_files) > 0 and uploaded_files[0]['file_url']:
            delete_local_file_from_disk(file)

            frappe.db.set_value(
                "File",
                file.name,
                "file_url",
                uploaded_files[0]['file_url']
            )

            frappe.db.set_value(
                "File",
                file.name,
                "nc_remote_path",
                uploaded_files[0]['remote_path']
            )
            if file.attached_to_doctype == 'RSVMitglied':
                # Der Upload-Dialog muss bereits die neue URL erhalten
                file.file_url = uploaded_files[0]['file_url']
                file.nc_remote_path = uploaded_files[0]['remote_path']

    return

def remove_file_from_nextcloud(file, event):
    if not file.nc_remote_path:
        return
    
    sektion = None

    if file.attached_to_doctype == 'Mitgliedschaft':
        sektion = frappe.db.get_value("Mitgliedschaft", file.attached_to_name, "sektion_id")
    
    if file.attached_to_doctype == 'Beratung':
        sektion = frappe.db.get_value("Beratung", file.attached_to_name, "sektion_id")
    if file.attached_to_doctype == 'RSVMitglied':
        sektion = frappe.db.get_value("RSVMitglied", file.attached_to_name, "sektion_id")
    
    if sektion:
        ncs = NCSettings(sektion)

        if not ncs.IS_ENABLED:
            return
        
        remote_path = file.nc_remote_path
        if file.attached_to_doctype == 'RSVMitglied':
            # File-ID bleibt auch nach einem Umzug des Mitgliedschaftsordners stabil
            file_id = (file.file_url or '').rstrip('/').split('/')[-1]
            if not file_id.isdigit():
                frappe.throw("Die Nextcloud-Datei besitzt keine gültige File-ID.")
            remote_path = ncs.get_nextcloud_remote_path(file_id)
            if not remote_path:
                return
        ncs.delete_file(remote_path)
