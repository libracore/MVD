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
            'datenstand_as': now_datetime().strftime("%d.%m.%Y %H:%M:%S"),
            's_as': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Eingang'}, limit=100, distinct=True)),
            's1_as': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Eingang', 'mv_mitgliedschaft': ['is', 'not set']}, limit=100, distinct=True)),
            's2_as': len(frappe.get_list('Beratung', fields='name', filters={'status': ['!=', 'Closed'], 's8': 1}, limit=100, distinct=True)),
            's3_as': len(frappe.get_list('Beratung', fields='name', filters={'ungelesen': 1, 'status': 'Zusammengeführt'}, limit=100, distinct=True)),
            's4_as': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['is', 'not set'], 'ungelesen': 0}, limit=100, distinct=True)),
            's5_as': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['is', 'not set'], 'ungelesen': 1}, limit=100, distinct=True)),
            'a1_as': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'kontaktperson': ['like', 'Administration%']}, limit=100, distinct=True)),
            'r_as': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open'}, limit=100, distinct=True)),
            'r1_as': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'beratung_prio': 'Hoch'}, limit=100, distinct=True)),
            'r2_as': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'kontaktperson': ['like', 'Rechtsberatung Pool%'], 'beratung_prio': ['!=', 'Hoch']}, limit=100, distinct=True)),
            'r3_as': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'kontaktperson': ['not like', 'Rechtsberatung Pool%']}, limit=100, distinct=True)),
            'r4_as': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['is', 'set'], 'ungelesen': 0}, limit=100, distinct=True)),
            'r5_as': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['is', 'set'], 'ungelesen': 1}, limit=100, distinct=True)),
            'r6_as': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['not like', 'Rechtsberatung Pool%'], 'kontaktperson': ['is', 'set'], 'ungelesen': 1}, limit=100, distinct=True)),
            'r7_as': len(frappe.get_list('Beratung', fields='name', filters={'status': ['!=', 'Closed'], 'hat_termine': 1}, limit=100, distinct=True)),
            'r8_as': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Closed', 'hat_termine': 1}, limit=100, distinct=True)),
            'r9_as': len(frappe.get_list('Beratung', fields='name', filters={'status': ['not in', ['Rückfragen', 'Open', 'Zusammengeführt']], 'ungelesen': 1}, limit=100, distinct=True)),
            'r10_bs': len(frappe.get_list('Beratung', fields='name', filters={'status': ['!=', 'Closed'],'_user_tags': ['like', '%MNE-MVBS%']}, limit=100, distinct=True)),
            'r11_bs': len(frappe.get_list('Beratung', fields='name', filters={'status': ['!=', 'Closed'],'_user_tags': ['like', '%Mandat-MVBS%']}, limit=100, distinct=True)),
            'r12_bs': len(frappe.get_list('Beratung', fields='name', filters={'status': ['!=', 'Closed'],'_user_tags': ['like', '%PHF-MVBS%']}, limit=100, distinct=True)),
            'p1_as': get_p1(frappe.session.user),
            'p2_as': get_p2(frappe.session.user),
            'p3_as': get_p3(frappe.session.user),
            'p4_as': get_p4(frappe.session.user)
        }
    }
    
    return open_data

def get_p1(user):
    p1_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                            WHERE `kontaktperson` IN (
                                                SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  
                                                AND `parent` NOT LIKE 'Rechtsberatung Pool (%)'
                                                AND `parent` NOT LIKE 'Administration (%)'
                                            )
                                            AND `status` = 'Open'""".format(user=user), as_dict=True)[0].qty
    return p1_qty or 0

def get_p2(user):
    p2_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                            WHERE `kontaktperson` IN (
                                                SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  
                                                AND `parent` NOT LIKE 'Rechtsberatung Pool (%)'
                                                AND `parent` NOT LIKE 'Administration (%)'
                                            )
                                            AND `status` = 'Rückfragen'
                                            AND `ungelesen` = 0""".format(user=user), as_dict=True)[0].qty
    return p2_qty or 0

def get_p3(user):
    p3_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                            WHERE `kontaktperson` IN (
                                                SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  AND `parent` NOT LIKE 'Rechtsberatung Pool (%)'
                                                AND `parent` NOT LIKE 'Administration (%)'
                                            )
                                            AND `status` = 'Rückfragen'
                                            AND `ungelesen` = 1""".format(user=user), as_dict=True)[0].qty
    return p3_qty or 0

def get_p4(user):
    p4_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                            WHERE `kontaktperson` IN (
                                                SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  
                                                AND `parent` NOT LIKE 'Rechtsberatung Pool (%)'
                                                AND `parent` NOT LIKE 'Administration (%)'
                                            )
                                            AND `status` = 'Termin vereinbart'""".format(user=user), as_dict=True)[0].qty
    return p4_qty or 0

@frappe.whitelist()
def get_user_kontaktperson(only_session_user=False):
    user_kontaktperson = frappe.db.sql("""SELECT `parent`
                                        FROM `tabTermin Kontaktperson Multi User`
                                        WHERE `user` = '{user}' 
                                        AND `parent` NOT LIKE 'Rechtsberatung Pool (%)'
                                        AND `parent` NOT LIKE 'Administration (%)'""".format(user=frappe.session.user), as_dict=True)
    user_kontaktpersonen = []
    for uk in user_kontaktperson:
        if not only_session_user:
            user_kontaktpersonen.append(uk.parent)
        else:
            if frappe.db.count('Termin Kontaktperson Multi User', {'parent': uk.parent}) < 2:
                user_kontaktpersonen.append(uk.parent)
    return user_kontaktpersonen
                
