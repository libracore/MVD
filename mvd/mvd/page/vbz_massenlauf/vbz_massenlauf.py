# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from PyPDF2 import PdfFileWriter
from frappe.utils.data import add_days, getdate, now, today, now_datetime
from frappe.utils.pdf import get_file_data_from_writer
from frappe.utils import nowdate

@frappe.whitelist()
def get_open_data():
    
    kuendigung_qty = len(frappe.get_list('Mitgliedschaft', fields='name', filters={'kuendigung_verarbeiten': 1}, limit=100, distinct=True, ignore_ifnull=True))
    korrespondenz_qty = len(frappe.get_list('Korrespondenz', fields='name', filters={'massenlauf': 1}, limit=100, distinct=True, ignore_ifnull=True))
    zuzug_qty = len(frappe.get_list('Mitgliedschaft', fields='name', filters={'zuzug_massendruck': 1}, limit=100, distinct=True, ignore_ifnull=True))
    rg_massendruck_qty = len(frappe.get_list('Mitgliedschaft', fields='name', filters={'rg_massendruck_vormerkung': 1}, limit=100, distinct=True, ignore_ifnull=True))
    begruessung_online_qty = len(frappe.get_list('Mitgliedschaft', fields='name', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 0}, limit=100, distinct=True, ignore_ifnull=True))
    begruessung_bezahlt_qty = len(frappe.get_list('Mitgliedschaft', fields='name', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 1}, limit=100, distinct=True, ignore_ifnull=True))
    mahnung_qty = len(frappe.get_list('Mahnung', fields='name', filters={'massenlauf': 1, 'docstatus': 1}, limit=100, distinct=True, ignore_ifnull=True))
    beratungstermine_qty = get_anzahl_mvzh_beratungen_heute('ganzer Tag')
    beratungstermine_morgen_qty = get_anzahl_mvzh_beratungen_heute('Morgen')
    beratungstermine_nachmittag_qty = get_anzahl_mvzh_beratungen_heute('Nachmittag')
    
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
        },
        'beratungstermine_massenlauf': {
            'qty': beratungstermine_qty
        },
        'beratungstermine_massenlauf_morgen': {
            'qty': beratungstermine_morgen_qty
        },
        'beratungstermine_massenlauf_nachmittag': {
            'qty': beratungstermine_nachmittag_qty
        }
    }
    
    return open_data

@frappe.whitelist()
def korrespondenz_massenlauf(sektion=False):
    if sektion:
        korrespondenzen = frappe.get_list('Korrespondenz', filters={'massenlauf': 1, 'sektion_id': sektion}, fields=['name'])
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
    else:
        frappe.throw("Fehlende Sektionsinformationen")

@frappe.whitelist()
def kuendigung_massenlauf(sektion=False):
    if sektion:
        mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'kuendigung_verarbeiten': 1, 'sektion_id': sektion}, fields=['name'])
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
    else:
        frappe.throw("Fehlende Sektionsinformationen")

@frappe.whitelist()
def zuzug_massenlauf(sektion=False):
    if sektion:
        mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'zuzug_massendruck': 1, 'sektion_id': sektion}, fields=['name'])
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
    else:
        frappe.throw("Fehlende Sektionsinformationen")

@frappe.whitelist()
def rg_massenlauf(sektion=False):
    if sektion:
        mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'rg_massendruck_vormerkung': 1, 'sektion_id': sektion}, fields=['name'])
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
    else:
        frappe.throw("Fehlende Sektionsinformationen")

@frappe.whitelist()
def begruessung_online_massenlauf(sektion=False):
    if sektion:
        mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 0, 'sektion_id': sektion}, fields=['name'])
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
    else:
        frappe.throw("Fehlende Sektionsinformationen")

@frappe.whitelist()
def begruessung_via_zahlung_massenlauf(sektion=False):
    if sektion:
        mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 1, 'sektion_id': sektion}, fields=['name'])
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
    else:
        frappe.throw("Fehlende Sektionsinformationen")

@frappe.whitelist()
def mahnung_massenlauf(sektion=False):
    if sektion:
        mahnungen = frappe.get_list('Mahnung', filters={'massenlauf': 1, 'docstatus': 1, 'sektion_id': sektion}, fields=['name'])
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
    else:
        frappe.throw("Fehlende Sektionsinformationen")

def get_anzahl_mvzh_beratungen_heute(halbtag):
    heute = nowdate()
    zeit_filter = ""
    if halbtag == "Morgen":
        zeit_filter = " AND TIME(termin.von) < '12:00:00'"
    elif halbtag == "Nachmittag":
        zeit_filter = " AND TIME(termin.von) >= '12:00:00'"
    ergebnis = frappe.db.sql("""
        SELECT COUNT(DISTINCT termin.parent) 
        FROM `tabBeratung Termin` as termin
        INNER JOIN `tabBeratung` as beratung ON termin.parent = beratung.name
        INNER JOIN `tabBeratungsort` as ort ON termin.ort = ort.name
        WHERE DATE(termin.von) = '{heute}' 
          AND beratung.sektion_id = 'MVZH'
          AND ort.kommt_auf_deckblatt = 1
        {zeit_filter}
    """.format(heute=heute, zeit_filter=zeit_filter))
    
    if ergebnis:
        return ergebnis[0][0]
    
    return 0

@frappe.whitelist()
def beratungstermine_massenlauf(halbtag):
    anzahl_beratungen = get_anzahl_mvzh_beratungen_heute(halbtag)
    if anzahl_beratungen > 0:
        massenlauf_typ = "Beratungstermine"
        if halbtag in ["Morgen", "Nachmittag"]:
            massenlauf_typ = "Beratungstermine {0}".format(halbtag)

        massenlauf = frappe.get_doc({
            "doctype": "Massenlauf",
            "sektion_id": "MVZH",
            "status": "Offen",
            "typ": massenlauf_typ
        })
        massenlauf.insert(ignore_permissions=True)
        return massenlauf.name
    else:
        frappe.throw("Es gibt keine Beratungen die für einen Massenlauf vorgemerkt sind.<br>Bitte aktualisieren Sie die Verarbeitungszentrale.")