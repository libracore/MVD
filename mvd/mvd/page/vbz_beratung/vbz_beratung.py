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
            'rueckfragen': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen'}, limit=100, distinct=True, ignore_ifnull=True)),
            'termine': len(frappe.get_list('Beratung', fields='name', filters={'hat_termine': 1}, limit=100, distinct=True, ignore_ifnull=True)),
            'ungelesen': len(frappe.get_list('Beratung', fields='name', filters={'ungelesen': 1}, limit=100, distinct=True, ignore_ifnull=True)),
            'zugewiesene_beratungen': frappe.db.count('ToDo', {'status': 'Open', 'owner': frappe.session.user, 'reference_type': 'Beratung'}),
            'zugewiesene_termine': get_zugewiesene_termine(frappe.session.user),
            'zugewiesene_ungelesene_beratungen': get_zugewiesene_ungelesene_beratungen(frappe.session.user)
        }
    }
    
    return open_data

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
                                            )""".format(user=user), as_dict=True)
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
