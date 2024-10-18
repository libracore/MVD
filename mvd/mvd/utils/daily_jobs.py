# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.data import today, getdate, now
from mvd.mvd.doctype.mitgliedschaft.utils import get_ampelfarbe
from mvd.mvd.doctype.region.region import _regionen_zuteilung
from frappe.utils.background_jobs import enqueue
from frappe.utils import cint

def create_daily_snap():
    new_daily_snap = frappe.get_doc({'doctype': 'Daily Snap'})
    new_daily_snap.insert()

def set_inaktiv():
    args = {}
    enqueue("mvd.mvd.utils.daily_jobs._set_inaktiv", queue='long', job_name='Nächtliche Inaktivierungen', timeout=5000, **args)

def _set_inaktiv():
    mitgliedschaften = frappe.db.sql("""
                                    SELECT
                                        `name`
                                    FROM `tabMitgliedschaft`
                                    WHERE
                                        (
                                            `status_c` IN ('Gestorben', 'Regulär')
                                            AND `kuendigung` IS NOT NULL
                                            AND `kuendigung` <= CURDATE()
                                        ) OR (
                                            `status_c` IN ('Gestorben', 'Regulär')
                                            AND `austritt` IS NOT NULL
                                            AND `austritt` <= CURDATE()
                                        ) OR (
                                            `status_c` = 'Ausschluss'
                                            AND `austritt` IS NOT NULL
                                            AND `austritt` <= CURDATE()
                                        ) OR (
                                        `status_c` = 'Wegzug'
                                        )
                                    LIMIT 1000""", as_dict=True)
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
                m.letzte_bearbeitung_von = 'User'
                m.save(ignore_permissions=True)
            else:
                if m.austritt and m.austritt <= getdate(today()):
                    change_log_row = m.append('status_change', {})
                    change_log_row.datum = now()
                    change_log_row.status_alt = m.status_c
                    change_log_row.status_neu = 'Inaktiv'
                    change_log_row.grund = 'Autom. Inaktivierung'
                    m.status_c = 'Inaktiv'
                    m.letzte_bearbeitung_von = 'User'
                    m.save(ignore_permissions=True)
        elif m.status_c == 'Ausschluss':
            if m.austritt and m.austritt <= getdate(today()):
                change_log_row = m.append('status_change', {})
                change_log_row.datum = now()
                change_log_row.status_alt = m.status_c
                change_log_row.status_neu = 'Inaktiv'
                change_log_row.grund = 'Autom. Inaktivierung'
                m.status_c = 'Inaktiv'
                m.letzte_bearbeitung_von = 'User'
                m.save(ignore_permissions=True)
        elif m.status_c == 'Wegzug':
            change_log_row = m.append('status_change', {})
            change_log_row.datum = now()
            change_log_row.status_alt = m.status_c
            change_log_row.status_neu = 'Inaktiv'
            change_log_row.grund = 'Wegzug zu Sektion {0}'.format(m.wegzug_zu)
            m.status_c = 'Inaktiv'
            m.letzte_bearbeitung_von = 'User'
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
    args = {}
    enqueue("mvd.mvd.doctype.region.region._regionen_zuteilung", queue='long', job_name='Regionen Zuteilung', timeout=5000, **args)

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
    from mvd.mvd.doctype.rechnungs_jahresversand.rechnungs_jahresversand import run_jahresversand_verbuchung
    run_jahresversand_verbuchung()

def reset_geschenk_mitgliedschaften():
    mitgliedschaften = frappe.db.sql("""
            SELECT
                `mv_mitgliedschaft`
            FROM `tabSales Invoice`
            WHERE `name` IN (
                SELECT
                    `geschenk_reset_rechnung`
                FROM `tabMitgliedschaft`
                WHERE `geschenk_reset_rechnung` LIKE 'R%'
            )
            AND `status` = 'Paid'
        """, as_dict=True)
    for mitgliedschaft in mitgliedschaften:
        ms = frappe.get_doc("Mitgliedschaft", mitgliedschaft.mv_mitgliedschaft)
        if not ms.validierung_notwendig and cint(ms.ist_einmalige_schenkung) == 1:
            # erstelle status change log und entferne Mitgliedschafts CBs
            change_log_row = ms.append('status_change', {})
            change_log_row.datum = today()
            change_log_row.status_alt = ms.status_c + " (Geschenk)"
            change_log_row.status_neu = ms.status_c
            change_log_row.grund = 'Weiterführung Mitgliedschaft'
            ms.ist_geschenkmitgliedschaft = None
            ms.ist_einmalige_schenkung = None
            ms.geschenkunterlagen_an_schenker = None
            ms.geschenk_reset_rechnung = None
            ms.save()

def mahnlauf_ausschluss():
    rgs_ohne_mitgl_mit = frappe.db.sql("""
                                        SELECT
                                            `name`,
                                            `mv_mitgliedschaft`
                                        FROM `tabSales Invoice`
                                        WHERE `sektion_id` != 'MVD'
                                        AND `docstatus` = 1
                                        AND `mv_mitgliedschaft` IS NOT NULL
                                        AND `exclude_from_payment_reminder_until` IS NULL
                                        AND `mv_mitgliedschaft` IN (
                                            SELECT `name` FROM `tabMitgliedschaft` WHERE `mahnstopp` IS NOT NULL
                                        )""", as_dict=True)
    
    for rg in rgs_ohne_mitgl_mit:
        mahnstopp = frappe.db.get_value("Mitgliedschaft", rg.mv_mitgliedschaft, 'mahnstopp')
        frappe.db.set_value("Sales Invoice", rg.name, 'exclude_from_payment_reminder_until', mahnstopp)
    
    rgs_mit_mitgl_ohne = frappe.db.sql("""
                                        SELECT
                                            `name`,
                                            `mv_mitgliedschaft`
                                        FROM `tabSales Invoice`
                                        WHERE `sektion_id` != 'MVD'
                                        AND `docstatus` = 1
                                        AND `mv_mitgliedschaft` IS NOT NULL
                                        AND `exclude_from_payment_reminder_until` IS NOT NULL
                                        AND `mv_mitgliedschaft` IN (
                                            SELECT `name` FROM `tabMitgliedschaft` WHERE `mahnstopp` IS NULL
                                        )""", as_dict=True)
    
    for rg in rgs_mit_mitgl_ohne:
        frappe.db.set_value("Sales Invoice", rg.name, 'exclude_from_payment_reminder_until', None)

def cleanup_beratungen():
    beratungen = frappe.db.sql("""
                                SELECT `name`
                                FROM `tabBeratung`
                                WHERE `status` != 'Closed'
                                AND `beratungskategorie` IS NOT NULL
                                AND `beratungskategorie` != ''
                                AND `name` IN (
                                    SELECT `parent` FROM `tabBeratung Termin`
                                    WHERE `bis` < CURDATE()
                                )""", as_dict=True)
    for beratung in beratungen:
        # prüfung ob es einen zweiten Termin gibt, welcher noch nicht in Vergangenheit liegt
        free_to_close = True
        b = frappe.get_doc("Beratung", beratung.name)
        if len(b.termin) > 1:
            for termin in b.termin:
                if getdate(termin.bis) >= getdate():
                    free_to_close = False
        
        if free_to_close:
            # bestehende ToDos entfernen
            todos_to_remove = frappe.db.sql("""
                                                SELECT
                                                    `name`
                                                FROM `tabToDo`
                                                WHERE `status` = 'Open'
                                                AND `reference_type` = 'Beratung'
                                                AND `reference_name` = '{0}'""".format(beratung.name), as_dict=True)
            for todo in todos_to_remove:
                t = frappe.get_doc("ToDo", todo.name)
                t.status = 'Cancelled'
                t.save(ignore_permissions=True)
            
            # Beratungs-Status auf Geschlossen setzen
            b.status = 'Closed'
            b.save()

def mark_beratungen_as_s8():
    beratungen = frappe.db.sql("""
                                SELECT `name`
                                FROM `tabBeratung`
                                WHERE `status` != 'Closed'
                                AND (
                                    `beratungskategorie` IS NULL
                                    OR `beratungskategorie` = ''
                                )
                                AND `name` IN (
                                    SELECT `parent` FROM `tabBeratung Termin`
                                    WHERE `bis` < CURDATE()
                                )""", as_dict=True)
    for beratung in beratungen:
        # prüfung ob es einen zweiten Termin gibt, welcher noch nicht in Vergangenheit liegt
        affected = True
        b = frappe.get_doc("Beratung", beratung.name)
        if len(b.termin) > 1:
            for termin in b.termin:
                if getdate(termin.bis) >= getdate():
                    affected = False
        
        if affected:
            frappe.db.set_value("Beratung", b.name, 's8', 1)
