# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.data import today
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_ampelfarbe

def set_inaktiv():
    mitgliedschaften = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `status_c` IN ('Gestorben', 'Kündigung', 'Ausschluss')""", as_dict=True)
    submit_counter = 1
    for mitgliedschaft in mitgliedschaften:
        m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
        if m.status_c in ('Kündigung', 'Gestorben'):
            if m.kuendigung and m.kuendigung <= getdate(today()):
                m.status_c = 'Inaktiv'
                m.save(ignore_permissions=True)
        elif m.status_c == 'Ausschluss':
            if m.austritt and m.austritt <= getdate(today()):
                m.status_c = 'Inaktiv'
                m.save(ignore_permissions=True)
        if submit_counter == 100:
            frappe.db.submit()
            submit_counter = 1
        else:
            submit_counter += 1
    frappe.db.submit()

def entferne_alte_reduzierungen():
    alte_preisregeln = frappe.db.sql("""SELECT `name` FROM `tabPricing Rule` WHERE `name` LIKE 'Reduzierung%' AND `disable` = 0 AND `valid_upto` < CURDATE()""", as_dict=True)
    for alte_preisregel in alte_preisregeln:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", alte_preisregel.name.replace("Reduzierung ", ""))
        mitgliedschaft.reduzierte_mitgliedschaft = 0
        mitgliedschaft.save()
    return

def ampel_neuberechnung():
    mitgliedschaften = frappe.db.sql("""SELECT
                                        `name`
                                        FROM `tabMitgliedschaft`
                                        WHERE `ampel_farbe` = 'ampelgelb'
                                        AND `status_c` NOT IN ('Gestorben', 'Wegzug', 'Ausschluss', 'Inaktiv', 'Interessent*in')
                                        AND IFNULL(DATEDIFF(`eintrittsdatum`, now()), 0) < -29""", as_dict=True)
    
    submit_counter = 1
    for mitgliedschaft in mitgliedschaften:
        m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
        neue_ampelfarbe = get_ampelfarbe(m)
        if m.ampel_farbe != neue_ampelfarbe:
            update_ampelfarbe = frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `ampel_farbe` ='{neue_ampelfarbe}' WHERE `name` = '{id}'""".format(neue_ampelfarbe=neue_ampelfarbe, id=m.name), as_list=True)
            if submit_counter == 100:
                frappe.db.commit()
                submit_counter = 1
            else:
                submit_counter += 1
    frappe.db.commit()
