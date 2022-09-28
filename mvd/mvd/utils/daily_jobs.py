# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.data import today, getdate, now
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_ampelfarbe
from mvd.mvd.doctype.region.region import _regionen_zuteilung
from frappe.utils.background_jobs import enqueue

def set_inaktiv():
    mitgliedschaften = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `status_c` IN ('Gestorben', 'Ausschluss', 'Wegzug') OR (`status_c` = 'Regulär' AND `kuendigung` IS NOT NULL)""", as_dict=True)
    submit_counter = 1
    for mitgliedschaft in mitgliedschaften:
        m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
        if m.status_c in ('Regulär', 'Gestorben'):
            if m.kuendigung and m.kuendigung <= getdate(today()):
                change_log_row = m.append('status_change', {})
                change_log_row.datum = now()
                change_log_row.status_alt = m.status_c + ' &dagger;' if m.status_c == 'Regulär' else m.status_c
                change_log_row.status_neu = 'Inaktiv'
                change_log_row.grund = 'Autom. Inaktivierung'
                m.status_c = 'Inaktiv'
                m.save(ignore_permissions=True)
            else:
                if m.austritt and m.austritt <= getdate(today()):
                    change_log_row = m.append('status_change', {})
                    change_log_row.datum = now()
                    change_log_row.status_alt = m.status_c
                    change_log_row.status_neu = 'Inaktiv'
                    change_log_row.grund = 'Autom. Inaktivierung'
                    m.status_c = 'Inaktiv'
                    m.save(ignore_permissions=True)
        elif m.status_c == 'Ausschluss':
            if m.austritt and m.austritt <= getdate(today()):
                change_log_row = m.append('status_change', {})
                change_log_row.datum = now()
                change_log_row.status_alt = m.status_c
                change_log_row.status_neu = 'Inaktiv'
                change_log_row.grund = 'Autom. Inaktivierung'
                m.status_c = 'Inaktiv'
                m.save(ignore_permissions=True)
        elif m.status_c == 'Wegzug':
            change_log_row = m.append('status_change', {})
            change_log_row.datum = now()
            change_log_row.status_alt = m.status_c
            change_log_row.status_neu = 'Inaktiv'
            change_log_row.grund = 'Wegzug zu Sektion {0}'.format(m.wegzug_zu)
            m.status_c = 'Inaktiv'
            m.save(ignore_permissions=True)
        if submit_counter == 100:
            frappe.db.commit()
            submit_counter = 1
        else:
            submit_counter += 1
    frappe.db.commit()

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

def regionen_zuteilung():
    _regionen_zuteilung()

def spenden_versand():
        spenden_jahresversand = frappe.db.sql("""SELECT `name` FROM `tabSpendenversand` WHERE `status` = 'Vorgemerkt' AND `docstatus` = 1""", as_dict=True)
        if len(spenden_jahresversand) > 0:
            for lauf in spenden_jahresversand:
                lauf = frappe.get_doc("Spendenversand", lauf.name)
                lauf.status = 'In Arbeit'
                lauf.save()
                args = {
                    'doc': lauf
                }
                enqueue("mvd.mvd.doctype.spendenversand.spendenversand.spenden_versand", queue='long', job_name='Spendenversand {0}'.format(lauf.name), timeout=5000, **args)

def rechnungs_jahresversand():
        rechnungs_jahresversand = frappe.db.sql("""SELECT `name` FROM `tabRechnungs Jahresversand` WHERE `status` = 'Vorgemerkt' AND `docstatus` = 1""", as_dict=True)
        if len(rechnungs_jahresversand) > 0:
            for lauf in rechnungs_jahresversand:
                jahresversand = frappe.get_doc("Rechnungs Jahresversand", lauf.name)
                jahresversand.status = 'In Arbeit'
                jahresversand.save()
                args = {
                    'jahresversand': lauf.name
                }
                enqueue("mvd.mvd.doctype.rechnungs_jahresversand.rechnungs_jahresversand.create_invoices", queue='long', job_name='Rechnungs Jahresversand {0}'.format(lauf.name), timeout=6000, **args)
