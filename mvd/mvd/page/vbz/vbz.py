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
    
    kuendigung_qty = 0 #len(frappe.get_list('Mitgliedschaft', fields='name', filters={'kuendigung_verarbeiten': 1}, limit=100, distinct=True, ignore_ifnull=True))
    korrespondenz_qty =0 #len(frappe.get_list('Korrespondenz', fields='name', filters={'massenlauf': 1}, limit=100, distinct=True, ignore_ifnull=True))
    zuzug_qty = 0 #len(frappe.get_list('Mitgliedschaft', fields='name', filters={'zuzug_massendruck': 1}, limit=100, distinct=True, ignore_ifnull=True))
    rg_massendruck_qty = 0 #len(frappe.get_list('Mitgliedschaft', fields='name', filters={'rg_massendruck_vormerkung': 1}, limit=100, distinct=True, ignore_ifnull=True))
    begruessung_online_qty = 0 #len(frappe.get_list('Mitgliedschaft', fields='name', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 0}, limit=100, distinct=True, ignore_ifnull=True))
    begruessung_bezahlt_qty = 0 #len(frappe.get_list('Mitgliedschaft', fields='name', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 1}, limit=100, distinct=True, ignore_ifnull=True))
    mahnung_qty = 0 #len(frappe.get_list('Mahnung', fields='name', filters={'massenlauf': 1, 'docstatus': 1}, limit=100, distinct=True, ignore_ifnull=True))
    # massenlauf total
    massenlauf_total = kuendigung_qty + korrespondenz_qty + zuzug_qty + rg_massendruck_qty + begruessung_online_qty + begruessung_bezahlt_qty + mahnung_qty
    retouren_qty = len(frappe.get_list('Retouren', fields='name', filters={'status': ['!=','Abgeschlossen']}, limit=100, distinct=True, ignore_ifnull=True))
    
    # letzter CAMT Import
    last_camt_import = [] #frappe.get_list('CAMT Import', fields='creation', filters={'status': ['!=', 'Open']}, order_by='creation DESC', ignore_ifnull=True)
    if len(last_camt_import) > 0:
        last_camt_import = 'Letzer Import:<br>' + getdate(last_camt_import[0].creation).strftime("%d.%m.%Y")
    else:
        last_camt_import = ''
    
    open_data = {
        'massenlauf_total': massenlauf_total,
        'datenstand': now_datetime().strftime("%d.%m.%Y %H:%M:%S"),
        'last_camt_import': last_camt_import,
        'arbeits_backlog': {
            'qty': len(frappe.get_list('Arbeits Backlog', fields='name', filters={'status': 'Open'}, limit=100, distinct=True, ignore_ifnull=True))
        },
        'todo': {
            'qty': len(frappe.get_list('ToDo', fields='name', filters={'status': 'Open'}, limit=100, distinct=True, ignore_ifnull=True))
        },
        'termin': {
            'qty': len(frappe.get_list('Termin', fields='name', filters={'von': ['>', today()]}, limit=100, distinct=True, ignore_ifnull=True))
        },
        'kuendigung_massenlauf': {
            'qty': kuendigung_qty
        },
        'korrespondenz_massenlauf': {
            'qty': korrespondenz_qty
        },
        'zuzug_massenlauf': {
            'qty': zuzug_qty
        },
        'rg_massenlauf': {
            'qty': rg_massendruck_qty
        },
        'begruessung_online_massenlauf': {
            'qty': begruessung_online_qty
        },
        'begruessung_bezahlt_massenlauf': {
            'qty': begruessung_bezahlt_qty
        },
        'mahnung_massenlauf': {
            'qty': mahnung_qty
        },
        'retouren': {
            'qty': retouren_qty
        }
    }
    
    return open_data
