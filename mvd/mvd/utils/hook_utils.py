# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint

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
    def get_recipient(mitglied):
        abw_debitor = 0
        abw_rg_adr = frappe.db.get_value("Mitgliedschaft", mitglied, "abweichende_rechnungsadresse") or 0
        if abw_rg_adr:
            abw_debitor = frappe.db.get_value("Mitgliedschaft", mitglied, "unabhaengiger_debitor") or 0
        if abw_debitor == 1:
            return frappe.db.get_value("Mitgliedschaft", mitglied, "rg_e_mail") or None
        
        return frappe.db.get_value("Mitgliedschaft", mitglied, "e_mail_1") or None
    
    
    from mvd.mvd.doctype.mitgliedschaft.finance_utils import check_mitgliedschaft_in_pe
    check_mitgliedschaft_in_pe(pe)
    
    return 
    # Bestätigungs Mail wenn Zahlung aus MRJ-2026
    # Vorübergehend deaktiviert!
    for sinv in pe.references:
        if frappe.db.get_value("Sales Invoice", sinv.reference_name, "status") == "Paid":
            if frappe.db.get_value("Sales Invoice", sinv.reference_name, "mrj") and \
            'MRJ-2026' in frappe.db.get_value("Sales Invoice", sinv.reference_name, "mrj"):
                mail_txt = """
                    Guten Tag
                    Wir haben Ihre Zahlung per {0} erhalten - Danke, dass Sie sich für die digitale Zahlung entschieden haben! Das spart Zeit und schont erst noch die Umwelt. Damit verlängert sich Ihre Mitgliedschaft beim Mieterinnen- und Mieterverband bis zum 31. Dezember 2026. Sollten Sie dennoch eine Papierrechnung erhalten, betrachten Sie bitte diese als gegenstandslos.<br><br>
                    Als Mitglied erhalten Sie eine umfassende mietrechtliche Beratung durch Ihre Sektion und finden auf der Webseite mieterverband.ch hilfreiche Informationen, Merkblätter, Vorlagen und Checklisten zu allen Fragen rund um das Mieten und Wohnen. Zudem stärken Sie mit Ihrer Mitgliedschaft die Interessenvertretung der Mieter*innen in der Schweiz.<br><br>
                    Besten Dank für Ihr Vertrauen!<br><br>
                    Mit freundlichen Grüssen Ihr Mieterinnen- und Mieterverband
                """.format(frappe.utils.get_datetime(pe.posting_date).strftime('%d.%m.%Y'))

                recipient = get_recipient(frappe.db.get_value("Sales Invoice", sinv.reference_name, "mv_mitgliedschaft"))
                
                if recipient:
                    frappe.sendmail(sender="{0} <{1}>".format(frappe.get_value("Sektion", pe.sektion_id, "serien_email_absender_name"), frappe.db.get_value("Sektion", pe.sektion_id, "serien_email_absender_adresse")),
                        recipients=[recipient],
                        message=mail_txt,
                        subject="Zahlungsbestätigung",
                        reply_to=frappe.db.get_value("Sektion", pe.sektion_id, "serien_email_absender_adresse"))

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
    from mvd.mvd.utils.nextcloud import NCSettings
    import os
    import frappe


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
    
    sektion = None
    folder_path = None

    if file.attached_to_doctype == 'Mitgliedschaft':
        mitglied_nr = frappe.db.get_value("Mitgliedschaft", file.attached_to_name, "mitglied_nr")
        if not mitglied_nr or mitglied_nr == "MV":
            return
        
        sektion = frappe.db.get_value("Mitgliedschaft", file.attached_to_name, "sektion_id")
        ncs = NCSettings(sektion)

        if not ncs.IS_ENABLED:
            return
        
        folder_path = "{0}/{1}".format(ncs.BASE_MITGLIED, mitglied_nr)
    
    if file.attached_to_doctype == 'Beratung':
        beratung = frappe.get_doc("Beratung", file.attached_to_name)
        sektion = beratung.sektion_id

        if not sektion:
            return
        
        ncs = NCSettings(sektion)
        mitglied_nr = None
        
        if beratung.mv_mitgliedschaft:
            mitglied_nr = frappe.db.get_value("Mitgliedschaft", beratung.mv_mitgliedschaft, "mitglied_nr")
        
        if mitglied_nr and mitglied_nr != "MV":
            folder_path = "{0}/{1}".format(ncs.BASE_MITGLIED_BERATUNG.replace("<platzhalter>", mitglied_nr), beratung.name)
        else:
            folder_path = "{0}/{1}".format(ncs.BASE_BERATUNG, beratung.name)

    if sektion and folder_path:
        file_content = file.get_content()   # liefert Bytes
        uploaded_files = ncs.upload_files(
            folder_path,
            [(file.file_name, file_content)]
        )
        
        if len(uploaded_files) > 0 and uploaded_files[0]['file_url']:
            delete_local_file_from_disk(file)
            frappe.db.set_value("File", file.name, "file_url", uploaded_files[0]['file_url'])
            frappe.db.set_value("File", file.name, "nc_remote_path", uploaded_files[0]['remote_path'])
        
    return

def remove_file_from_nextcloud(file, event):
    from mvd.mvd.utils.nextcloud import NCSettings

    if not file.nc_remote_path:
        return
    
    sektion = None

    if file.attached_to_doctype == 'Mitgliedschaft':
        sektion = frappe.db.get_value("Mitgliedschaft", file.attached_to_name, "sektion_id")
    
    if file.attached_to_doctype == 'Beratung':
        sektion = frappe.db.get_value("Beratung", file.attached_to_name, "sektion_id")
    
    if sektion:
        ncs = NCSettings(sektion)

        if not ncs.IS_ENABLED:
            return
        
        ncs.delete_file(file.nc_remote_path)