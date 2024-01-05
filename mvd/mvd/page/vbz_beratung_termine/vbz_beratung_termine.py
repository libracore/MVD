# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from PyPDF2 import PdfFileWriter
from frappe.utils.data import add_days, getdate, now, today, now_datetime, get_datetime
from frappe.boot import get_bootinfo

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
                                        `beratung`.`sektion_id`
                                    FROM `tabBeratung Termin` AS `berTer`
                                    LEFT JOIN `tabBeratung` AS `beratung` ON `berTer`.`parent` = `beratung`.`name`
                                    WHERE `berTer`.`von` >= '{datum_von} 00:00:00'
                                    ORDER BY `berTer`.`von` DESC
                                 """.format(datum_von=today()), as_dict=True)
    for termin in alle_termine:
        if not erlaubte_sektionen or termin.sektion_id in erlaubte_sektionen:
            termin_data = {
                'von_date': get_datetime(termin.von).strftime('%d.%m.%Y'),
                'von_time': get_datetime(termin.von).strftime('%H:%M:%S'),
                'bis_time': get_datetime(termin.bis).strftime('%H:%M:%S'),
                'art': termin.art,
                'ort': termin.ort,
                'beratung': termin.parent,
                'beraterinn': termin.berater_in
            }
            alle.append(termin_data)
        if termin.berater_in in kontaktperson_multi_user:
            meine.append(termin_data)
    return alle, meine

def get_kontaktperson_multi_user(user):
    kontaktperson_multi_user = frappe.db.sql("""SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  """.format(user=user), as_dict=True)
    user_list = []
    for multi_user in kontaktperson_multi_user:
        user_list.append(multi_user.parent)
    return user_list
