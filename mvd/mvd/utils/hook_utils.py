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
    if self.recipients:
        removed_row = False
        for recipient in self.recipients:
            if recipient.recipient == 'Administrator ' or \
            'admin@example.com' in recipient.recipient or \
            recipient.recipient == 'Guest ' or \
            'guest@example.com' in recipient.recipient:
                # entferne Admin/Guest Zeile
                self.remove(recipient)
                removed_row = True
        if removed_row:
            if len(self.recipients) > 0:
                # check for CC's
                self.show_as_cc = self.show_as_cc.replace("Administrator &lt;admin@example.com&gt;", "").replace("Guest &lt;guest@example.com&gt;", "")
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

    # Bestätigungs Mail wenn Zahlung aus MRJ-2026
    for sinv in pe.references:
        if sinv.outstanding_amount == sinv.allocated_amount:
            if 'MRJ-2026' in frappe.db.get_value("Sales Invoice", sinv.reference_name, "mrj"):
                mail_txt = """
                    Guten Tag
                    Wir haben Ihre Zahlung per {0} erhalten - Danke, dass Sie sich für die digitale Zahlung entschieden haben! Das spart Zeit und schont erst noch die Umwelt. Damit verlängert sich Ihre Mitgliedschaft beim Mieterinnen- und Mieterverband bis zum 31. Dezember 2026. Sollten Sie dennoch eine Papierrechnung erhalten, betrachten Sie bitte diese als gegenstandslos.<br><br>
                    Als Mitglied erhalten Sie eine umfassende mietrechtliche Beratung durch Ihre Sektion vor Ort und finden auf der Webseite mieterverband.ch hilfreiche Informationen, Merkblätter, Vorlagen und Checklisten zu allen Fragen rund um das Mieten und Wohnen. Zudem stärken Sie mit Ihrer Mitgliedschaft die Interessenvertretung der Mieter*innen in der Schweiz.<br><br>
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