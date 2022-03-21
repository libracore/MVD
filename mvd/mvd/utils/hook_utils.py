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
            users = frappe.share.get_users('ToDo', todo.name)
            for user in users:
                frappe.share.remove("ToDo", todo.name, user.user, flags={'ignore_share_permission': True, 'ignore_permissions': True})
    except:
        pass
