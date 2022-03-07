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
        # ~ 'validierung': {
            # ~ 'qty': len(frappe.get_list('Mitgliedschaft', fields='name', filters={'validierung_notwendig': 1}, limit=100, distinct=True, ignore_ifnull=True)),
            # ~ 'online_beitritt': {
                # ~ 'qty': len(frappe.get_list('Mitgliedschaft', fields='name', filters={'validierung_notwendig': 1, 'status_c': 'Online-Beitritt'}, limit=100, distinct=True, ignore_ifnull=True))
            # ~ },
            # ~ 'online_anmeldung': {
                # ~ 'qty': len(frappe.get_list('Mitgliedschaft', fields='name', filters={'validierung_notwendig': 1, 'status_c': 'Online-Anmeldung'}, limit=100, distinct=True, ignore_ifnull=True))
            # ~ },
            # ~ 'online_kuendigung': {
                # ~ 'qty': len(frappe.get_list('Mitgliedschaft', fields='name', filters={'validierung_notwendig': 1, 'status_c': 'Online-Kündigung'}, limit=100, distinct=True, ignore_ifnull=True))
            # ~ },
            # ~ 'online_mutation': {
                # ~ 'qty': len(frappe.get_list('Mitgliedschaft', fields='name', filters={'validierung_notwendig': 1, 'status_c': 'Online-Mutation'}, limit=100, distinct=True, ignore_ifnull=True))
            # ~ },
            # ~ 'zuzug': {
                # ~ 'qty': len(frappe.get_list('Mitgliedschaft', fields='name', filters={'validierung_notwendig': 1, 'status_c': 'Zuzug'}, limit=100, distinct=True, ignore_ifnull=True))
            # ~ }
        # ~ },
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
        output = PdfFileWriter()
        for korrespondenz in korrespondenzen:
            output = frappe.get_print("Korrespondenz", korrespondenz['name'], 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
            
        file_name = "Korrespondenz_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
        file_name = file_name.split(".")[0]
        file_name = file_name.replace(":", "-")
        file_name = file_name + ".pdf"
        
        filedata = get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home",
            "is_private": 1,
            "content": filedata
        })
        
        _file.save(ignore_permissions=True)
        
        for korrespondenz in korrespondenzen:
            k = frappe.get_doc("Korrespondenz", korrespondenz['name'])
            k.massenlauf = '0'
            k.save(ignore_permissions=True)
        
        return _file.name
    else:
        frappe.throw("Es gibt keine Korrespondenzen die für einen Massenlauf vorgemerkt sind.")

@frappe.whitelist()
def kuendigung_massenlauf():
    mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'kuendigung_verarbeiten': 1}, fields=['name'])
    if len(mitgliedschaften) > 0:
        output = PdfFileWriter()
        for mitgliedschaft in mitgliedschaften:
            output = frappe.get_print("Mitgliedschaft", mitgliedschaft['name'], 'Kündigungsbestätigung', as_pdf = True, output = output, ignore_zugferd=True)
            
        file_name = "Kündigungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
        file_name = file_name.split(".")[0]
        file_name = file_name.replace(":", "-")
        file_name = file_name + ".pdf"
        
        filedata = get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home",
            "is_private": 1,
            "content": filedata
        })
        
        _file.save(ignore_permissions=True)
        
        for mitgliedschaft in mitgliedschaften:
            m = frappe.get_doc("Mitgliedschaft", mitgliedschaft['name'])
            m.kuendigung_verarbeiten = '0'
            m.save(ignore_permissions=True)
        
        return _file.name
    else:
        frappe.throw("Es gibt keine Mitgliedschaften die für einen Kündigungs-Massenlauf vorgemerkt sind.")

@frappe.whitelist()
def zuzug_massenlauf():
    mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'zuzug_massendruck': 1}, fields=['name', 'zuzugs_rechnung', 'zuzug_korrespondenz'])
    if len(mitgliedschaften) > 0:
        output = PdfFileWriter()
        for mitgliedschaft in mitgliedschaften:
            if mitgliedschaft['zuzugs_rechnung']:
                output = frappe.get_print("Sales Invoice", mitgliedschaft['zuzugs_rechnung'], 'Automatisierte Mitgliedschaftsrechnung', as_pdf = True, output = output, ignore_zugferd=True)
            else:
                output = frappe.get_print("Korrespondenz", mitgliedschaft['zuzug_korrespondenz'], 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
            
        file_name = "Zuzugs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
        file_name = file_name.split(".")[0]
        file_name = file_name.replace(":", "-")
        file_name = file_name + ".pdf"
        
        filedata = get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home",
            "is_private": 1,
            "content": filedata
        })
        
        _file.save(ignore_permissions=True)
        
        for mitgliedschaft in mitgliedschaften:
            m = frappe.get_doc("Mitgliedschaft", mitgliedschaft['name'])
            m.zuzug_massendruck = '0'
            m.save(ignore_permissions=True)
        
        return _file.name
    else:
        frappe.throw("Es gibt keine Mitgliedschaften die für einen Zuzugs-Massenlauf vorgemerkt sind.")

@frappe.whitelist()
def rg_massenlauf():
    sinvs = frappe.get_list('Mitgliedschaft', filters={'rg_massendruck_vormerkung': 1}, fields=['rg_massendruck', 'name'])
    if len(sinvs) > 0:
        output = PdfFileWriter()
        for sinv in sinvs:
            if sinv['rg_massendruck']:
                output = frappe.get_print("Sales Invoice", sinv['rg_massendruck'], 'Automatisierte Mitgliedschaftsrechnung', as_pdf = True, output = output, ignore_zugferd=True)
            
        file_name = "Mitgliedschaftsrechnungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
        file_name = file_name.split(".")[0]
        file_name = file_name.replace(":", "-")
        file_name = file_name + ".pdf"
        
        filedata = get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home",
            "is_private": 1,
            "content": filedata
        })
        
        _file.save(ignore_permissions=True)
        
        for sinv in sinvs:
            m = frappe.get_doc("Mitgliedschaft", sinv['name'])
            m.rg_massendruck_vormerkung = '0'
            m.rg_massendruck = ''
            m.save(ignore_permissions=True)
        
        return _file.name
    else:
        frappe.throw("Es gibt keine Mitgliedschaften die für einen Rechnungs-Massenlauf vorgemerkt sind.")

@frappe.whitelist()
def begruessung_online_massenlauf():
    mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 0}, fields=['name', 'begruessung_massendruck_dokument'])
    if len(mitgliedschaften) > 0:
        output = PdfFileWriter()
        for mitgliedschaft in mitgliedschaften:
            if mitgliedschaft['begruessung_massendruck_dokument']:
                output = frappe.get_print("Korrespondenz", mitgliedschaft['begruessung_massendruck_dokument'], 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
            
        file_name = "Begüssungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
        file_name = file_name.split(".")[0]
        file_name = file_name.replace(":", "-")
        file_name = file_name + ".pdf"
        
        filedata = get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home",
            "is_private": 1,
            "content": filedata
        })
        
        _file.save(ignore_permissions=True)
        
        for mitgliedschaft in mitgliedschaften:
            m = frappe.get_doc("Mitgliedschaft", mitgliedschaft['name'])
            m.begruessung_massendruck = '0'
            m.begruessung_massendruck_dokument = ''
            m.save(ignore_permissions=True)
        
        return _file.name
    else:
        frappe.throw("Es gibt keine Mitgliedschaften die für einen Begrüssungs-Massenlauf vorgemerkt sind.")

@frappe.whitelist()
def begruessung_via_zahlung_massenlauf():
    mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 1}, fields=['name', 'begruessung_massendruck_dokument'])
    if len(mitgliedschaften) > 0:
        output = PdfFileWriter()
        for mitgliedschaft in mitgliedschaften:
            if mitgliedschaft['begruessung_massendruck_dokument']:
                output = frappe.get_print("Korrespondenz", mitgliedschaft['begruessung_massendruck_dokument'], 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
            
        file_name = "Begüssungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
        file_name = file_name.split(".")[0]
        file_name = file_name.replace(":", "-")
        file_name = file_name + ".pdf"
        
        filedata = get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home",
            "is_private": 1,
            "content": filedata
        })
        
        _file.save(ignore_permissions=True)
        
        for mitgliedschaft in mitgliedschaften:
            m = frappe.get_doc("Mitgliedschaft", mitgliedschaft['name'])
            m.begruessung_massendruck = '0'
            m.begruessung_via_zahlung = '0'
            m.begruessung_massendruck_dokument = ''
            m.save(ignore_permissions=True)
        
        return _file.name
    else:
        frappe.throw("Es gibt keine Mitgliedschaften die für einen Begrüssungs-Massenlauf vorgemerkt sind.")

@frappe.whitelist()
def mahnung_massenlauf():
    mahnungen = frappe.get_list('Mahnung', filters={'massenlauf': 1, 'docstatus': 1}, fields=['name'])
    if len(mahnungen) > 0:
        massenlauf = frappe.get_doc({
            "doctype": "Massenlauf",
            "sektion_id": frappe.get_value("Mahnung", mahnungen[0]['name'], "sektion_id"),
            "status": "Offen"
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
