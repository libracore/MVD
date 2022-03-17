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
    
    kuendigung_qty = len(frappe.get_list('Mitgliedschaft', fields='name', filters={'kuendigung_verarbeiten': 1}, limit=100, distinct=True, ignore_ifnull=True))
    korrespondenz_qty = len(frappe.get_list('Korrespondenz', fields='name', filters={'massenlauf': 1}, limit=100, distinct=True, ignore_ifnull=True))
    zuzug_qty = len(frappe.get_list('Mitgliedschaft', fields='name', filters={'zuzug_massendruck': 1}, limit=100, distinct=True, ignore_ifnull=True))
    rg_massendruck_qty = len(frappe.get_list('Mitgliedschaft', fields='name', filters={'rg_massendruck_vormerkung': 1}, limit=100, distinct=True, ignore_ifnull=True))
    begruessung_online_qty = len(frappe.get_list('Mitgliedschaft', fields='name', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 0}, limit=100, distinct=True, ignore_ifnull=True))
    begruessung_bezahlt_qty = len(frappe.get_list('Mitgliedschaft', fields='name', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 1}, limit=100, distinct=True, ignore_ifnull=True))
    mahnung_qty = len(frappe.get_list('Mahnung', fields='name', filters={'massenlauf': 1, 'docstatus': 1}, limit=100, distinct=True, ignore_ifnull=True))
    
    # massenlauf total
    massenlauf_total = kuendigung_qty + korrespondenz_qty + zuzug_qty + rg_massendruck_qty + begruessung_online_qty + begruessung_bezahlt_qty + mahnung_qty
    
    open_data = {
        'massenlauf_total': massenlauf_total,
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
        }
    }
    
    return open_data

@frappe.whitelist()
def korrespondenz_massenlauf():
    korrespondenzen = frappe.get_list('Korrespondenz', filters={'massenlauf': 1}, fields=['name'])
    if len(korrespondenzen) > 0:
        massenlauf = frappe.get_doc({
            "doctype": "Massenlauf",
            "sektion_id": frappe.get_value("Korrespondenz", korrespondenzen[0]['name'], "sektion_id"),
            "status": "Offen",
            "typ": "Korrespondenz"
        })
        massenlauf.insert(ignore_permissions=True)
        
        return massenlauf.name
    else:
        frappe.throw("Es gibt keine Korrespondenzen die für einen Massenlauf vorgemerkt sind.<br>Bitte aktualisieren Sie die Verarbeitungszentrale.")

@frappe.whitelist()
def kuendigung_massenlauf():
    mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'kuendigung_verarbeiten': 1}, fields=['name'])
    if len(mitgliedschaften) > 0:
        massenlauf = frappe.get_doc({
            "doctype": "Massenlauf",
            "sektion_id": frappe.get_value("Mitgliedschaft", mitgliedschaften[0]['name'], "sektion_id"),
            "status": "Offen",
            "typ": "Kündigung"
        })
        massenlauf.insert(ignore_permissions=True)
        
        return massenlauf.name
    else:
        frappe.throw("Es gibt keine Kündigungen die für einen Massenlauf vorgemerkt sind.<br>Bitte aktualisieren Sie die Verarbeitungszentrale.")

@frappe.whitelist()
def zuzug_massenlauf():
    mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'zuzug_massendruck': 1}, fields=['name'])
    if len(mitgliedschaften) > 0:
        massenlauf = frappe.get_doc({
            "doctype": "Massenlauf",
            "sektion_id": frappe.get_value("Mitgliedschaft", mitgliedschaften[0]['name'], "sektion_id"),
            "status": "Offen",
            "typ": "Zuzug"
        })
        massenlauf.insert(ignore_permissions=True)
        
        return massenlauf.name
    else:
        frappe.throw("Es gibt keine Zuzüge die für einen Massenlauf vorgemerkt sind.<br>Bitte aktualisieren Sie die Verarbeitungszentrale.")

@frappe.whitelist()
def rg_massenlauf():
    mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'rg_massendruck_vormerkung': 1}, fields=['name'])
    if len(mitgliedschaften) > 0:
        massenlauf = frappe.get_doc({
            "doctype": "Massenlauf",
            "sektion_id": frappe.get_value("Mitgliedschaft", mitgliedschaften[0]['name'], "sektion_id"),
            "status": "Offen",
            "typ": "Rechnung"
        })
        massenlauf.insert(ignore_permissions=True)
        
        return massenlauf.name
    else:
        frappe.throw("Es gibt keine Mitgliedschaften die für einen Rechnungs-Massenlauf vorgemerkt sind.<br>Bitte aktualisieren Sie die Verarbeitungszentrale.")

@frappe.whitelist()
def begruessung_online_massenlauf():
    mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 0}, fields=['name'])
    if len(mitgliedschaften) > 0:
        massenlauf = frappe.get_doc({
            "doctype": "Massenlauf",
            "sektion_id": frappe.get_value("Mitgliedschaft", mitgliedschaften[0]['name'], "sektion_id"),
            "status": "Offen",
            "typ": "Begrüssung Online"
        })
        massenlauf.insert(ignore_permissions=True)
        
        return massenlauf.name
    else:
        frappe.throw("Es gibt keine Mitgliedschaften die für einen Begrüssungs-Massenlauf vorgemerkt sind.<br>Bitte aktualisieren Sie die Verarbeitungszentrale.")

@frappe.whitelist()
def begruessung_via_zahlung_massenlauf():
    mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 1}, fields=['name'])
    if len(mitgliedschaften) > 0:
        massenlauf = frappe.get_doc({
            "doctype": "Massenlauf",
            "sektion_id": frappe.get_value("Mitgliedschaft", mitgliedschaften[0]['name'], "sektion_id"),
            "status": "Offen",
            "typ": "Begrüssung durch Bezahlung"
        })
        massenlauf.insert(ignore_permissions=True)
        
        return massenlauf.name
    else:
        frappe.throw("Es gibt keine Mitgliedschaften die für einen Begrüssungs-Massenlauf vorgemerkt sind.<br>Bitte aktualisieren Sie die Verarbeitungszentrale.")

@frappe.whitelist()
def mahnung_massenlauf():
    mahnungen = frappe.get_list('Mahnung', filters={'massenlauf': 1, 'docstatus': 1}, fields=['name'])
    if len(mahnungen) > 0:
        massenlauf = frappe.get_doc({
            "doctype": "Massenlauf",
            "sektion_id": frappe.get_value("Mahnung", mahnungen[0]['name'], "sektion_id"),
            "status": "Offen",
            "typ": "Mahnung"
        })
        massenlauf.insert(ignore_permissions=True)
        
        for mahnung in mahnungen:
            m = frappe.get_doc("Mahnung", mahnung['name'])
            m.massenlauf = '0'
            m.massenlauf_referenz = massenlauf.name
            m.save(ignore_permissions=True)
        
        return massenlauf.name
    else:
        frappe.throw("Es gibt keine Mahnungen die für einen Massenlauf vorgemerkt sind.<br>Bitte aktualisieren Sie die Verarbeitungszentrale.")
