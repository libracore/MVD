# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from PyPDF2 import PdfFileWriter
from frappe.utils.data import add_days, getdate, now, today, now_datetime
from frappe.utils.pdf import get_file_data_from_writer

# Status, die bei "weitere Korrespondenz" (ehemals Zeile R9) nicht gemeint sind.
KORRESPONDENZ_STATUS_EXCLUDE = ['Rückfragen', 'Open', 'Zusammengeführt', 'Termin vereinbart', 'Rückfrage: Termin vereinbaren']


def get_r1_filter_sets(typ):
    """R1 (Dringend): offene Fälle mit hoher Prio + Fälle mit ungelesener Korrespondenz (ehem. R9)."""
    return [
        {'status': ['in', ['Open', 'In Arbeit']], 'beratung_prio': 'Hoch', 'typ': typ},
        {'status': ['not in', KORRESPONDENZ_STATUS_EXCLUDE], 'ungelesen': 1, 'kontaktperson': ['is', 'set'], 'beratung_prio': 'Hoch', 'typ': typ}
    ]


def get_r2_filter_sets(typ):
    """R2 (Im Pool / weitere Korrespondenz): Pool-Fälle + übrige Fälle mit ungelesener Korrespondenz (ehem. R9)."""
    return [
        {'status': ['in', ['Open', 'In Arbeit']], 'beratung_prio': ['not in', ['Hoch']], 'kontaktperson': ['like', 'Rechtsberatung Pool%'], 'typ': typ},
        {'status': ['not in', KORRESPONDENZ_STATUS_EXCLUDE], 'ungelesen': 1, 'kontaktperson': ['is', 'set'], 'beratung_prio': ['not in', ['Hoch']], 'typ': typ}
    ]


def get_beratung_namen(filter_sets):
    """Vereinigungsmenge mehrerer Filter (ODER lässt sich in einem get_list-Filter nicht abbilden).

    Bewusst get_list statt SQL: nur so greifen die User Permissions auf die Sektion.
    """
    namen = set()
    for filters in filter_sets:
        for beratung in frappe.get_list('Beratung', fields=['name'], filters=filters, limit=100, distinct=True):
            namen.add(beratung['name'])
    return namen


@frappe.whitelist()
def get_beratungen_der_zeile(zeile, typ):
    """Namen der Beratungen einer Zeile – für den Klick auf R1/R2, deren Menge sich
    nicht als einzelner Listen-Filter ausdrücken lässt."""
    if zeile == 'r1':
        filter_sets = get_r1_filter_sets(typ)
    elif zeile == 'r2':
        filter_sets = get_r2_filter_sets(typ)
    else:
        frappe.throw("Unbekannte Zeile: {0}".format(zeile))
        return []

    return sorted(get_beratung_namen(filter_sets))


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
            # R1/R2 enthalten seit #2021 zusätzlich die Fälle der früheren Zeile R9
            # (ungelesene Korrespondenz auf zugewiesenen Beratungen), aufgeteilt nach Prio.
            'r1_wohnen': len(get_beratung_namen(get_r1_filter_sets('Wohnen'))),
            'r1_business': len(get_beratung_namen(get_r1_filter_sets('Business'))),
            'r2_wohnen': len(get_beratung_namen(get_r2_filter_sets('Wohnen'))),
            'r2_business': len(get_beratung_namen(get_r2_filter_sets('Business'))),
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