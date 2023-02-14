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
            'eingang_ohne_zuordnung': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Eingang', 'mv_mitgliedschaft': None}, limit=100, distinct=True, ignore_ifnull=True)),
            'offen': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open'}, limit=100, distinct=True, ignore_ifnull=True)),
            'offen_dringend': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'beratung_prio': 'Hoch'}, limit=100, distinct=True, ignore_ifnull=True)),
            'offen_zuweisung_ja': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'zuweisung': 1}, limit=100, distinct=True, ignore_ifnull=True)),
            'offen_zuweisung_nein': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'zuweisung': 0}, limit=100, distinct=True, ignore_ifnull=True)),
            'rueckfragen': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen'}, limit=100, distinct=True, ignore_ifnull=True)),
            'termine': len(frappe.get_list('Beratung', fields='name', filters={'hat_termine': 1}, limit=100, distinct=True, ignore_ifnull=True))
        }
    }
    
    return open_data
