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
    zukunft_termine = frappe.db.sql_list("SELECT DISTINCT parent FROM `tabBeratung Termin` WHERE `von` > %s", now_datetime())

    open_data = {
        'beratung': {
            'datenstand': now_datetime().strftime("%d.%m.%Y %H:%M:%S"),
            's1': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Eingang', 'mv_mitgliedschaft': ['is', 'not set'], 'faktura_kunde': ['is', 'not set']}, limit=100, distinct=True)),
            's6_wohnen': len(frappe.get_list('Beratung', fields='name', filters={'status': ['not in', ['Rückfragen', 'Rückfrage: Termin vereinbaren', 'Eingang', 'Open', 'Zusammengeführt']], 'ungelesen': 1, 'kontaktperson': ['is', 'not set'], 'typ': 'Wohnen'}, limit=100, distinct=True)),
            's6_business': len(frappe.get_list('Beratung', fields='name', filters={'status': ['not in', ['Rückfragen', 'Rückfrage: Termin vereinbaren', 'Eingang', 'Open', 'Zusammengeführt']], 'ungelesen': 1, 'kontaktperson': ['is', 'not set'], 'typ': 'Business'}, limit=100, distinct=True)),
            's10_wohnen': len(frappe.get_list('Beratung', fields='name', filters={'ungelesen': 1, 'sektion_id': ['!=', 'MVDF'], 'name': ['in', zukunft_termine], 'typ': 'Wohnen'}, limit=100, distinct=True)),
            's10_business': len(frappe.get_list('Beratung', fields='name', filters={'ungelesen': 1, 'sektion_id': ['!=', 'MVDF'], 'name': ['in', zukunft_termine], 'typ': 'Business'}, limit=100, distinct=True)),
            'r_wohnen': len(frappe.get_list('Beratung', fields='name', filters={'status': ['in', ['Open', 'In Arbeit']], 'typ': 'Wohnen'}, limit=100, distinct=True)),
            'r_business': len(frappe.get_list('Beratung', fields='name', filters={'status': ['in', ['Open', 'In Arbeit']], 'typ': 'Business'}, limit=100, distinct=True)),
            'r1_wohnen': len(frappe.get_list('Beratung', fields='name', filters={'status': ['in', ['Open', 'In Arbeit']], 'beratung_prio': 'Hoch', 'typ': 'Wohnen'}, limit=100, distinct=True)),
            'r1_business': len(frappe.get_list('Beratung', fields='name', filters={'status': ['in', ['Open', 'In Arbeit']], 'beratung_prio': 'Hoch', 'typ': 'Business'}, limit=100, distinct=True)),
            'r2_wohnen': len(frappe.get_list('Beratung', fields='name', filters={'status': ['in', ['Open', 'In Arbeit']], 'beratung_prio': ['not in', ['Hoch']], 'kontaktperson': ['like','Rechtsberatung Pool%'], 'typ': 'Wohnen'}, limit=100, distinct=True)),
            'r2_business': len(frappe.get_list('Beratung', fields='name', filters={'status': ['in', ['Open', 'In Arbeit']], 'beratung_prio': ['not in', ['Hoch']], 'kontaktperson': ['like','Rechtsberatung Pool%'], 'typ': 'Business'}, limit=100, distinct=True)),
            'r3_wohnen': len(frappe.get_list('Beratung', fields='name', filters={'status': ['in', ['Open', 'In Arbeit']], 'r3': 1, 'typ': 'Wohnen'}, limit=100, distinct=True)),
            'r3_business': len(frappe.get_list('Beratung', fields='name', filters={'status': ['in', ['Open', 'In Arbeit']], 'r3': 1, 'typ': 'Business'}, limit=100, distinct=True)),
            'r4_wohnen': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['is', 'set'], 'ungelesen': 0, 'typ': 'Wohnen'}, limit=100, distinct=True)),
            'r4_business': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['is', 'set'], 'ungelesen': 0, 'typ': 'Business'}, limit=100, distinct=True)),
            'r5_wohnen': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['like', 'Rechtsberatung Pool%'], 'ungelesen': 1, 'typ': 'Wohnen'}, limit=100, distinct=True)),
            'r5_business': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['like', 'Rechtsberatung Pool%'], 'ungelesen': 1, 'typ': 'Business'}, limit=100, distinct=True)),
            'r6_wohnen': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['not like', 'Rechtsberatung Pool%'], 'ungelesen': 1, 'typ': 'Wohnen'}, limit=100, distinct=True)),
            'r6_business': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Rückfragen', 'kontaktperson': ['not like', 'Rechtsberatung Pool%'], 'ungelesen': 1, 'typ': 'Business'}, limit=100, distinct=True)),
            'r7_wohnen': len(frappe.get_list('Beratung', fields='name', filters={'status': ['!=', 'Closed'], 'hat_termine': 1, 'typ': 'Wohnen'}, limit=100, distinct=True)),
            'r7_business': len(frappe.get_list('Beratung', fields='name', filters={'status': ['!=', 'Closed'], 'hat_termine': 1, 'typ': 'Business'}, limit=100, distinct=True)),
            'r8_wohnen': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Closed', 'hat_termine': 1, 'typ': 'Wohnen'}, limit=100, distinct=True)),
            'r8_business': len(frappe.get_list('Beratung', fields='name', filters={'status': 'Closed', 'hat_termine': 1, 'typ': 'Business'}, limit=100, distinct=True)),
            'r9_wohnen': len(frappe.get_list('Beratung', fields='name', filters={'status': ['not in', ['Rückfragen', 'Open', 'Zusammengeführt', 'Termin vereinbart', "Rückfrage: Termin vereinbaren"]], 'ungelesen': 1, 'kontaktperson': ['is', 'set'], 'typ': 'Wohnen'}, limit=100, distinct=True)),
            'r9_business': len(frappe.get_list('Beratung', fields='name', filters={'status': ['not in', ['Rückfragen', 'Open', 'Zusammengeführt', 'Termin vereinbart', "Rückfrage: Termin vereinbaren"]], 'ungelesen': 1, 'kontaktperson': ['is', 'set'], 'typ': 'Business'}, limit=100, distinct=True)),
            
            
            'p1_wohnen': get_p1(frappe.session.user, 'Wohnen'),
            'p1_business': get_p1(frappe.session.user, 'Business'),
            'p2_wohnen': get_p2(frappe.session.user, 'Wohnen'),
            'p2_business': get_p2(frappe.session.user, 'Business'),
            'p3_wohnen': get_p3(frappe.session.user, 'Wohnen'),
            'p3_business': get_p3(frappe.session.user, 'Business'),
            'p4_wohnen': get_p4(frappe.session.user, 'Wohnen'),
            'p4_business': get_p4(frappe.session.user, 'Business')
        }
    }
    
    return open_data

def get_p1(user, typ):
    p1_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                            WHERE `kontaktperson` IN (
                                                SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  
                                                AND `parent` NOT LIKE 'Rechtsberatung Pool (%)'
                                            )
                                            AND `status` IN ('Open', 'In Arbeit')
                                            AND `typ` = '{typ}'""".format(user=user, typ=typ), as_dict=True)[0].qty
    return p1_qty or 0

def get_p2(user, typ):
    p2_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                            WHERE `kontaktperson` IN (
                                                SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  
                                                AND `parent` NOT LIKE 'Rechtsberatung Pool (%)'
                                            )
                                            AND `status` = 'Rückfragen'
                                            AND `ungelesen` = 0
                                            AND `typ` = '{typ}'""".format(user=user, typ=typ), as_dict=True)[0].qty
    return p2_qty or 0

def get_p3(user, typ):
    p3_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                            WHERE `kontaktperson` IN (
                                                SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  AND `parent` NOT LIKE 'Rechtsberatung Pool (%)'
                                            )
                                            AND `status` = 'Rückfragen'
                                            AND `ungelesen` = 1
                                            AND `typ` = '{typ}'""".format(user=user, typ=typ), as_dict=True)[0].qty
    return p3_qty or 0

def get_p4(user, typ):
    p4_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratung`
                                            WHERE `kontaktperson` IN (
                                                SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  
                                                AND `parent` NOT LIKE 'Rechtsberatung Pool (%)'
                                            )
                                            AND `status` = 'Termin vereinbart'
                                            AND `hat_termine` = 1
                                            AND `typ` = '{typ}'""".format(user=user, typ=typ), as_dict=True)[0].qty
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
                
@frappe.whitelist()
def get_termine_in_zukunft():
    return frappe.db.sql_list("SELECT DISTINCT parent FROM `tabBeratung Termin` WHERE `von` > %s", now_datetime())