# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from PyPDF2 import PdfFileWriter
from frappe.utils.data import add_days, getdate, now, today, now_datetime, get_datetime
from frappe.boot import get_bootinfo
from frappe import _

no_cache=1

@frappe.whitelist()
def get_open_data():
    alle_termine, meine_termine = get_alle_beratungs_termine(frappe.session.user)
    datasets = {
        'datenstand_as': now_datetime().strftime("%d.%m.%Y %H:%M:%S"),
        'alle_termine': alle_termine,
        'meine_termine': meine_termine
    }
    return datasets

def get_alle_beratungs_termine(user):
    alle = []
    meine = []
    vergebene_termin_liste = []
    kontaktperson_multi_user = get_kontaktperson_multi_user(user)
    sektionen = frappe.db.sql("""
                                SELECT `for_value`
                                FROM `tabUser Permission`
                                WHERE `allow` = 'Sektion'
                                AND `user` = '{user}'
                                ORDER BY `is_default` DESC""".format(user=user), as_dict=True)
    if len(sektionen) > 0:
        erlaubte_sektionen = []
        for sektion in sektionen:
            erlaubte_sektionen.append(sektion.for_value)
    else:
        erlaubte_sektionen = False
    
    alle_termine = frappe.db.sql("""
                                    SELECT
                                        `berTer`.`von`,
                                        `berTer`.`bis`,
                                        `berTer`.`art`,
                                        `berTer`.`ort`,
                                        `berTer`.`parent`,
                                        `berTer`.`berater_in`,
                                        `berTer`.`telefonnummer`,
                                        `beratung`.`sektion_id`,
                                        `beratung`.`beratungskategorie`,
                                        `beratung`.`beratungskategorie_2`,
                                        `beratung`.`beratungskategorie_3`,
                                        `beratung`.`mv_mitgliedschaft`,
                                        `berTer`.`abp_referenz`
                                    FROM `tabBeratung Termin` AS `berTer`
                                    LEFT JOIN `tabBeratung` AS `beratung` ON `berTer`.`parent` = `beratung`.`name`
                                    WHERE `berTer`.`von` >= '{datum_von} 00:00:00'
                                    ORDER BY `berTer`.`von` DESC
                                 """.format(datum_von=today()), as_dict=True)
    for termin in alle_termine:
        if not erlaubte_sektionen or termin.sektion_id in erlaubte_sektionen:
            hat_attachement = 1 if frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratungsdateien` WHERE `parent` = '{termin}'""".format(termin=termin.parent), as_dict=True)[0].qty > 0 else 0
            termin_data = {
                'von_date': get_datetime(termin.von).strftime('%d.%m.%Y'),
                'von_time': get_datetime(termin.von).strftime('%H:%M'),
                'bis_time': get_datetime(termin.bis).strftime('%H:%M'),
                'art': termin.art,
                'ort': termin.ort,
                'beratung': termin.parent,
                'beraterinn': termin.berater_in,
                'hat_attachement': hat_attachement,
                'telefonnummer': termin.telefonnummer,
                'wochentag': _(get_datetime(termin.von).strftime('%A'))[:2],
                'beratungskategorie': termin.beratungskategorie.split(" - ")[0] if termin.beratungskategorie else '',
                'beratungskategorie_2': termin.beratungskategorie_2.split(" - ")[0] if termin.beratungskategorie_2 else '',
                'beratungskategorie_3': termin.beratungskategorie_3.split(" - ")[0] if termin.beratungskategorie_3 else '',
                'name_mitglied': "{0} {1}".format(frappe.db.get_value("Mitgliedschaft", termin.mv_mitgliedschaft, 'vorname_1'), frappe.db.get_value("Mitgliedschaft", termin.mv_mitgliedschaft, 'nachname_1')),
                'sort_date': frappe.utils.getdate(termin.von)
            }
            alle.append(termin_data)
        if termin.berater_in in kontaktperson_multi_user:
            meine.append(termin_data)
        if termin.abp_referenz:
            vergebene_termin_liste.append(termin.abp_referenz)
    if len(meine) < 1:
        meine.append({'show_placeholder': 1})
    
    freie_termine = frappe.db.sql("""
                                  SELECT
                                    CONCAT(`date`, ' ', `from_time`) AS `von`,
                                    CONCAT(`date`, ' ', `to_time`) AS `bis`,
                                    `art_ort` AS `ort`,
                                    `beratungsperson` AS `beraterinn`,
                                    NULL AS `von_date`,
                                    NULL AS `von_time`,
                                    NULL AS `bis_time`,
                                    '---' AS `art`,
                                    '---' AS `beratung`,
                                    0 AS `hat_attachement`,
                                    '---' AS `telefonnummer`,
                                    NULL AS `wochentag`,
                                    '---' AS `beratungskategorie`,
                                    '---' AS `beratungskategorie_2`,
                                    '---' AS `beratungskategorie_3`,
                                    '---' AS `name_mitglied`,
                                  NULL AS `sort_date`
                                  FROM `tabAPB Zuweisung`
                                  WHERE `name` NOT IN ('{vergebene_termine}')
                                  AND `date` >= '{datum_von}'
                                  """.format(vergebene_termine="', '".join(vergebene_termin_liste), datum_von=today()), as_dict=True)
    for freier_termin in freie_termine:
        freier_termin.von = frappe.utils.get_datetime(freier_termin.von)
        freier_termin.bis = frappe.utils.get_datetime(freier_termin.bis)
        freier_termin.von_date = get_datetime(termin.von).strftime('%d.%m.%Y')
        freier_termin.von_time = get_datetime(termin.von).strftime('%H:%M')
        freier_termin.bis_time = get_datetime(termin.bis).strftime('%H:%M')
        freier_termin.wochentag = _(get_datetime(termin.von).strftime('%A'))[:2]
        freier_termin.sort_date = frappe.utils.getdate(freier_termin.von)
    
    for freier_termin in freie_termine:
        alle.append(freier_termin)
    
    alle_sortiert = sorted(alle, key = lambda x: (x['sort_date'], x['beraterinn'] or 'ZZZ', x['von_time']))

    return alle_sortiert, meine

def get_kontaktperson_multi_user(user):
    kontaktperson_multi_user = frappe.db.sql("""SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  """.format(user=user), as_dict=True)
    user_list = []
    for multi_user in kontaktperson_multi_user:
        user_list.append(multi_user.parent)
    return user_list
