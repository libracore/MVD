# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def check_mitgliedschaft_in_pe(pe, event):
    if not pe.mv_mitgliedschaft:
        mitgliedschaft = suche_nach_mitgliedschaft(pe.party)
        if mitgliedschaft:
            frappe.db.sql("""UPDATE `tabPayment Entry` SET `mv_mitgliedschaft` = '{mitgliedschaft}' WHERE `name` = '{pe}'""".format(mitgliedschaft=mitgliedschaft, pe=pe.name), as_list=True)
            frappe.db.commit()

def suche_nach_mitgliedschaft(customer):
    mitgliedschaften = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `kunde_mitglied` = '{customer}' OR `rg_kunde` = '{customer}'""".format(customer=customer), as_list=True)
    if len(mitgliedschaften) > 0:
        return mitgliedschaften[0][0]
    else:
        return False

def resave_mitgliedschaft(sinv, event):
    if sinv.mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", sinv.mv_mitgliedschaft)
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
        ref_date = add_to_date(date=sinv.creation, hours=1)
        if sinv.modified < ref_date:
            skip = True
    if not skip:
        if sinv.zugehoerige_fr:
            update_fr = frappe.db.sql("""UPDATE `tabFakultative Rechnung` SET `sales_invoice` = '{sinv}' WHERE `name` = '{hv_fr}'""".format(sinv=sinv.name, hv_fr=sinv.zugehoerige_fr), as_list=True)
            frappe.db.commit()
            sinv.zugehoerige_fr = None
