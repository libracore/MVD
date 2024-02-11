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
            'datenstand': now_datetime().strftime("%d.%m.%Y %H:%M:%S"),
            's': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Eingang', 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            's1': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Eingang', 'mv_mitgliedschaft': ['is', 'not set'], 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            's2': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Eingang', 'beratungskategorie': ['in', ['202 - MZ-Erhöhung', '300 - Nebenkosten']], 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            's3': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfrage: Termin vereinbaren', 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            's4': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['is', 'not set'], 'ungelesen': 0, 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            's5': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['is', 'not set'], 'ungelesen': 1, 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            's6': len(frappe.get_list('Beratung', fields='name', filters={'status': ['not in', ['Rückfragen', 'Rückfrage: Termin vereinbaren', 'Eingang', 'Open', 'Zusammengeführt']], 'ungelesen': 1, 'kontaktperson': ['is', 'not set'], 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            's7': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'kontaktperson': ['is', 'not set'], 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            's8': len(frappe.get_list('Beratung', fields='name', filters={'status': ['!=', 'Closed'], 's8': 1, 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True, ignore_ifnull=True)),
            's9': len(frappe.get_list('Beratung', fields='name', filters={'ungelesen': 1, 'status': 'Zusammengeführt', 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True, ignore_ifnull=True)),
            'r': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            'r1': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'beratung_prio': 'Hoch', 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            'r2': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'beratung_prio': ['!=', 'Hoch'], 'kontaktperson': 'Rechtsberatung Pool (MVBE)', 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            'r3': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Open', 'kontaktperson': ['!=', 'Rechtsberatung Pool (MVBE)'], 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            'r4': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['is', 'set'], 'ungelesen': 0, 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            'r5': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['is', 'set'], 'ungelesen': 1, 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            'r6': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['!=', 'Rechtsberatung Pool (MVBE)'], 'kontaktperson': ['is', 'set'], 'ungelesen': 1, 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            'r7': len(frappe.get_list('Beratung', fields='name', filters={'status': ['!=', 'Closed'], 'hat_termine': 1, 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            'r8': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Closed', 'hat_termine': 1, 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            'r9': len(frappe.get_list('Beratung', fields='name', filters={'status': ['not in', ['Rückfragen', 'Open', 'Zusammengeführt']], 'ungelesen': 1, 'kontaktperson': ['is', 'set'], 'sektion_id': ['!=', 'MVDF']}, limit=100, distinct=True)),
            'p1': get_p1(frappe.session.user),
            'p2': get_p2(frappe.session.user),
            'p3': get_p3(frappe.session.user),
            'p4': get_p4(frappe.session.user)
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
                                            )
                                            AND `status` = 'Open'
                                            AND `sektion_id` != 'MVDF'""".format(user=user), as_dict=True)[0].qty
    return p1_qty or 0

def get_p2(user):
    p2_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                            WHERE `kontaktperson` IN (
                                                SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  
                                                AND `parent` NOT LIKE 'Rechtsberatung Pool (%)'
                                            )
                                            AND `status` = 'Rückfragen'
                                            AND `ungelesen` = 0
                                            AND `sektion_id` != 'MVDF'""".format(user=user), as_dict=True)[0].qty
    return p2_qty or 0

def get_p3(user):
    p3_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                            WHERE `kontaktperson` IN (
                                                SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  AND `parent` NOT LIKE 'Rechtsberatung Pool (%)'
                                            )
                                            AND `status` = 'Rückfragen'
                                            AND `ungelesen` = 1
                                            AND `sektion_id` != 'MVDF'""".format(user=user), as_dict=True)[0].qty
    return p3_qty or 0

def get_p4(user):
    p4_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                            WHERE `kontaktperson` IN (
                                                SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  
                                                AND `parent` NOT LIKE 'Rechtsberatung Pool (%)'
                                            )
                                            AND `status` = 'Termin vereinbart'
                                            AND `hat_termine` = 1
                                            AND `sektion_id` != 'MVDF'""".format(user=user), as_dict=True)[0].qty
    return p4_qty or 0

@frappe.whitelist()
def get_user_kontaktperson(only_session_user=False):
    user_kontaktperson = frappe.db.sql("""SELECT `parent`
                                        FROM `tabTermin Kontaktperson Multi User`
                                        WHERE `user` = '{user}' 
                                        AND `parent` NOT LIKE 'Rechtsberatung Pool (%)'""".format(user=frappe.session.user), as_dict=True)
    user_kontaktpersonen = []
    for uk in user_kontaktperson:
        if not only_session_user:
            user_kontaktpersonen.append(uk.parent)
        else:
            if frappe.db.count('Termin Kontaktperson Multi User', {'parent': uk.parent}) < 2:
                user_kontaktpersonen.append(uk.parent)
    return user_kontaktpersonen
                
