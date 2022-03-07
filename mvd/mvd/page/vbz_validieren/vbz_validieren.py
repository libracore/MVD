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
        'validierung': {
            'qty': len(frappe.get_list('Mitgliedschaft', fields='name', filters={'validierung_notwendig': 1}, limit=100, distinct=True, ignore_ifnull=True)),
            'online_beitritt': {
                'qty': len(frappe.get_list('Mitgliedschaft', fields='name', filters={'validierung_notwendig': 1, 'status_c': 'Online-Beitritt'}, limit=100, distinct=True, ignore_ifnull=True))
            },
            'online_anmeldung': {
                'qty': len(frappe.get_list('Mitgliedschaft', fields='name', filters={'validierung_notwendig': 1, 'status_c': 'Online-Anmeldung'}, limit=100, distinct=True, ignore_ifnull=True))
            },
            'online_kuendigung': {
                'qty': len(frappe.get_list('Mitgliedschaft', fields='name', filters={'validierung_notwendig': 1, 'status_c': 'Online-Kündigung'}, limit=100, distinct=True, ignore_ifnull=True))
            },
            'online_mutation': {
                'qty': len(frappe.get_list('Mitgliedschaft', fields='name', filters={'validierung_notwendig': 1, 'status_c': 'Online-Mutation'}, limit=100, distinct=True, ignore_ifnull=True))
            },
            'zuzug': {
                'qty': len(frappe.get_list('Mitgliedschaft', fields='name', filters={'validierung_notwendig': 1, 'status_c': 'Zuzug'}, limit=100, distinct=True, ignore_ifnull=True))
            }
        }
    }
    
    return open_data
