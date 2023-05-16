# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from PyPDF2 import PdfFileWriter
from frappe.utils.data import add_days, getdate, now, today, now_datetime
from frappe.utils.pdf import get_file_data_from_writer

@frappe.whitelist()
def get_open_data():
    open_data = {
        'beratung': {
            'eingang': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Eingang'}, limit=100, distinct=True, ignore_ifnull=True)),
            'eingang_ohne_zuordnung': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Eingang', 'mv_mitgliedschaft': ['is', 'not set']}, limit=100, distinct=True, ignore_ifnull=True)),
            'eingang_ungelesen': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Eingang', 'ungelesen': 1}, limit=100, distinct=True, ignore_ifnull=True)),
            'offen': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open'}, limit=100, distinct=True, ignore_ifnull=True)),
            'offen_dringend': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'beratung_prio': 'Hoch'}, limit=100, distinct=True, ignore_ifnull=True)),
            'offen_zuweisung_ja': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'zuweisung': 1}, limit=100, distinct=True, ignore_ifnull=True)),
            'offen_zuweisung_nein': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'zuweisung': 0}, limit=100, distinct=True, ignore_ifnull=True)),
            'offen_ungelesen': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'ungelesen': 1}, limit=100, distinct=True, ignore_ifnull=True)),
            'rueckfragen': len(frappe.get_list('Beratung', fields='name', filters={'status': ['IN', ['Rückfragen', 'Rückfrage: Termin vereinbaren']]}, limit=100, distinct=True, ignore_ifnull=True)),
            'termine': len(frappe.get_list('Beratung', fields='name', filters={'hat_termine': 1, 'status': ['!=', 'Closed']}, limit=100, distinct=True, ignore_ifnull=True)),
            'ungelesen': len(frappe.get_list('Beratung', fields='name', filters={'ungelesen': 1}, limit=100, distinct=True, ignore_ifnull=True)),
            'zugewiesene_beratungen': zugewiesene_beratungen(frappe.session.user),
            'zugewiesene_termine': get_zugewiesene_termine(frappe.session.user),
            'zugewiesene_ungelesene_beratungen': get_zugewiesene_ungelesene_beratungen(frappe.session.user),
            'datenstand': now_datetime().strftime("%d.%m.%Y %H:%M:%S"),
            'exklusive_zuweisungen': get_exklusive_zuweisungen(frappe.session.user)
        }
    }
    
    return open_data

def get_exklusive_zuweisungen(user, names=False):
    if not names:
        response_filter = """COUNT(`name`) AS `qty`"""
    else:
        response_filter = """`name`"""
    exklusive_zuweisungen = frappe.db.sql("""SELECT
                                                {response_filter}
                                            FROM (
                                                SELECT
                                                    `name`,
                                                    `owner`
                                                FROM (
                                                    SELECT
                                                        COUNT(`name`) AS `qty`,
                                                        `name`,
                                                        `owner`
                                                    FROM `tabToDo`
                                                    WHERE `status` = 'Open'
                                                    GROUP BY `reference_name`
                                                ) AS `unique`
                                                WHERE `unique`.`qty` = 1
                                            ) AS `exklusiv`
                                            WHERE `exklusiv`.`owner` = '{user}'""".format(response_filter=response_filter, user=user), as_dict=True)
    if len(exklusive_zuweisungen) > 0:
        if not names:
            return exklusive_zuweisungen[0].qty
    else:
        if not names:
            return 0

def zugewiesene_beratungen(user):
    zugewiesene_beratungen = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                            WHERE `name` IN (
                                                SELECT `reference_name`
                                                FROM `tabToDo`
                                                WHERE `reference_type` = 'Beratung'
                                                AND `status` = 'Open'
                                                AND `owner` = '{user}'
                                            )
                                            AND `status` != 'Closed'""".format(user=user), as_dict=True)
    if len(zugewiesene_beratungen) > 0:
        return zugewiesene_beratungen[0].qty
    else:
        return 0

def get_zugewiesene_termine(user):
    zugewiesene_termine = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                            WHERE `name` IN (
                                                SELECT `reference_name`
                                                FROM `tabToDo`
                                                WHERE `reference_type` = 'Beratung'
                                                AND `status` = 'Open'
                                                AND `owner` = '{user}'
                                            )
                                            AND `name` IN (
                                                SELECT `parent` FROM `tabBeratung Termin`
                                            )
                                            AND `status` != 'Closed'""".format(user=user), as_dict=True)
    if len(zugewiesene_termine) > 0:
        return zugewiesene_termine[0].qty
    else:
        return 0

def get_zugewiesene_ungelesene_beratungen(user):
    beratungen = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                WHERE `name` IN (
                                    SELECT `reference_name`
                                    FROM `tabToDo`
                                    WHERE `reference_type` = 'Beratung'
                                    AND `status` = 'Open'
                                    AND `owner` = '{user}'
                                )
                                AND `ungelesen` = 1""".format(user=user), as_dict=True)
    if len(beratungen) > 0:
        return beratungen[0].qty
    else:
        return 0
