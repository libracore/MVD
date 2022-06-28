# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from PyPDF2 import PdfFileWriter
from frappe.utils.pdf import get_file_data_from_writer
from frappe.utils.data import now

class Massenlauf(Document):
    pass

@frappe.whitelist()
def verarbeitung_massenlauf(massenlauf):
    massenlauf = frappe.get_doc("Massenlauf", massenlauf)
    if massenlauf.typ == 'Mahnung':
        args = {
            'massenlauf': massenlauf.name,
            'sektion': massenlauf.sektion_id
        }
        enqueue("mvd.mvd.doctype.massenlauf.massenlauf.mahnung", queue='long', job_name='Verarbeite Massenlauf {0}'.format(massenlauf.name), timeout=5000, **args)
        return 1
    
    if massenlauf.typ == 'Kündigung':
        args = {
            'massenlauf': massenlauf.name,
            'sektion': massenlauf.sektion_id
        }
        enqueue("mvd.mvd.doctype.massenlauf.massenlauf.kuendigung", queue='long', job_name='Verarbeite Massenlauf {0}'.format(massenlauf.name), timeout=5000, **args)
        return 1
    
    if massenlauf.typ == 'Zuzug':
        args = {
            'massenlauf': massenlauf.name,
            'sektion': massenlauf.sektion_id
        }
        enqueue("mvd.mvd.doctype.massenlauf.massenlauf.zuzug", queue='long', job_name='Verarbeite Massenlauf {0}'.format(massenlauf.name), timeout=5000, **args)
        return 1
    
    if massenlauf.typ == 'Begrüssung durch Bezahlung':
        args = {
            'massenlauf': massenlauf.name,
            'sektion': massenlauf.sektion_id
        }
        enqueue("mvd.mvd.doctype.massenlauf.massenlauf.begruessung_bezahlung", queue='long', job_name='Verarbeite Massenlauf {0}'.format(massenlauf.name), timeout=5000, **args)
        return 1
    
    if massenlauf.typ == 'Begrüssung Online':
        args = {
            'massenlauf': massenlauf.name,
            'sektion': massenlauf.sektion_id
        }
        enqueue("mvd.mvd.doctype.massenlauf.massenlauf.begruessung_online", queue='long', job_name='Verarbeite Massenlauf {0}'.format(massenlauf.name), timeout=5000, **args)
        return 1
    
    if massenlauf.typ == 'Korrespondenz':
        args = {
            'massenlauf': massenlauf.name,
            'sektion': massenlauf.sektion_id
        }
        enqueue("mvd.mvd.doctype.massenlauf.massenlauf.korrespondenz", queue='long', job_name='Verarbeite Massenlauf {0}'.format(massenlauf.name), timeout=5000, **args)
        return 1
    
    if massenlauf.typ == 'Rechnung':
        args = {
            'massenlauf': massenlauf.name,
            'sektion': massenlauf.sektion_id
        }
        enqueue("mvd.mvd.doctype.massenlauf.massenlauf.rechnung", queue='long', job_name='Verarbeite Massenlauf {0}'.format(massenlauf.name), timeout=5000, **args)
        return 1

def mahnung(massenlauf, sektion):
    try:
        mahnungen = frappe.get_list('Mahnung', filters={'massenlauf_referenz': massenlauf, 'docstatus': 1, 'sektion_id': sektion}, fields=['name'])
        counter = 1
        output = PdfFileWriter()
        for mahnung in mahnungen:
            output = frappe.get_print("Mahnung", mahnung['name'], 'Mahnung', as_pdf = True, output = output, ignore_zugferd=True)
            if counter == 500:
                file_name = "Mahnungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
                file_name = file_name.split(".")[0]
                file_name = file_name.replace(":", "-")
                file_name = file_name + ".pdf"
                
                filedata = get_file_data_from_writer(output)
                
                _file = frappe.get_doc({
                    "doctype": "File",
                    "file_name": file_name,
                    "folder": "Home/Attachments",
                    "is_private": 1,
                    "content": filedata,
                    "attached_to_doctype": 'Massenlauf',
                    "attached_to_name": massenlauf
                })
                
                _file.save(ignore_permissions=True)
                output = PdfFileWriter()
                counter = 1
            else:
                counter += 1
            
        file_name = "Mahnungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
        file_name = file_name.split(".")[0]
        file_name = file_name.replace(":", "-")
        file_name = file_name + ".pdf"
        
        filedata = get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home/Attachments",
            "is_private": 1,
            "content": filedata,
            "attached_to_doctype": 'Massenlauf',
            "attached_to_name": massenlauf
        })
        
        _file.save(ignore_permissions=True)
        
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Abgeschlossen'
        massenlauf.error = ''
        massenlauf.save(ignore_permissions=True)
    except Exception as err:
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Fehlgeschlagen'
        massenlauf.error = str(err)
        massenlauf.save(ignore_permissions=True)

def kuendigung(massenlauf, sektion):
    try:
        mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'kuendigung_verarbeiten': 1, 'sektion_id': sektion}, fields=['name'])
        if len(mitgliedschaften) > 0:
            counter = 1
            output = PdfFileWriter()
            for mitgliedschaft in mitgliedschaften:
                output = frappe.get_print("Mitgliedschaft", mitgliedschaft['name'], 'Kündigungsbestätigung', as_pdf = True, output = output, ignore_zugferd=True)
                if counter == 500:
                    file_name = "Kündigungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
                    file_name = file_name.split(".")[0]
                    file_name = file_name.replace(":", "-")
                    file_name = file_name + ".pdf"
                    
                    filedata = get_file_data_from_writer(output)
                    
                    _file = frappe.get_doc({
                        "doctype": "File",
                        "file_name": file_name,
                        "folder": "Home/Attachments",
                        "is_private": 1,
                        "content": filedata,
                        "attached_to_doctype": 'Massenlauf',
                        "attached_to_name": massenlauf
                    })
                    
                    _file.save(ignore_permissions=True)
                    output = PdfFileWriter()
                    counter = 1
                else:
                    counter += 1
            
            file_name = "Kündigungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
            file_name = file_name.split(".")[0]
            file_name = file_name.replace(":", "-")
            file_name = file_name + ".pdf"
            
            filedata = get_file_data_from_writer(output)
            
            _file = frappe.get_doc({
                "doctype": "File",
                "file_name": file_name,
                "folder": "Home/Attachments",
                "is_private": 1,
                "content": filedata,
                "attached_to_doctype": 'Massenlauf',
                "attached_to_name": massenlauf
            })
            
            _file.save(ignore_permissions=True)
            
            for mitgliedschaft in mitgliedschaften:
                m = frappe.get_doc("Mitgliedschaft", mitgliedschaft['name'])
                m.kuendigung_verarbeiten = '0'
                m.letzte_bearbeitung_von = 'SP'
                m.save(ignore_permissions=True)
        
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Abgeschlossen'
        massenlauf.error = ''
        massenlauf.save(ignore_permissions=True)
    except Exception as err:
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Fehlgeschlagen'
        massenlauf.error = str(err)
        massenlauf.save(ignore_permissions=True)

def zuzug(massenlauf, sektion):
    err_mitgl = ''
    try:
        ungedruckte = ''
        mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'zuzug_massendruck': 1, 'sektion_id': sektion}, fields=['name', 'zuzugs_rechnung', 'zuzug_korrespondenz'])
        if len(mitgliedschaften) > 0:
            counter = 1
            output = PdfFileWriter()
            for mitgliedschaft in mitgliedschaften:
                err_mitgl = mitgliedschaft['name']
                if mitgliedschaft['zuzugs_rechnung']:
                    output = frappe.get_print("Sales Invoice", mitgliedschaft['zuzugs_rechnung'], 'Automatisierte Mitgliedschaftsrechnung', as_pdf = True, output = output, ignore_zugferd=True)
                elif mitgliedschaft['zuzug_korrespondenz']:
                    output = frappe.get_print("Korrespondenz", mitgliedschaft['zuzug_korrespondenz'], 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
                else:
                    ungedruckte += mitgliedschaft['name'] + '\n'
                if counter == 500:
                    file_name = "Zuzugs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
                    file_name = file_name.split(".")[0]
                    file_name = file_name.replace(":", "-")
                    file_name = file_name + ".pdf"
                    
                    filedata = get_file_data_from_writer(output)
                    
                    _file = frappe.get_doc({
                        "doctype": "File",
                        "file_name": file_name,
                        "folder": "Home/Attachments",
                        "is_private": 1,
                        "content": filedata,
                        "attached_to_doctype": 'Massenlauf',
                        "attached_to_name": massenlauf
                    })
                    
                    _file.save(ignore_permissions=True)
                    output = PdfFileWriter()
                    counter = 1
                else:
                    counter += 1
            
            file_name = "Zuzugs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
            file_name = file_name.split(".")[0]
            file_name = file_name.replace(":", "-")
            file_name = file_name + ".pdf"
            
            filedata = get_file_data_from_writer(output)
            
            _file = frappe.get_doc({
                "doctype": "File",
                "file_name": file_name,
                "folder": "Home/Attachments",
                "is_private": 1,
                "content": filedata,
                "attached_to_doctype": 'Massenlauf',
                "attached_to_name": massenlauf
            })
            
            _file.save(ignore_permissions=True)
        
        for mitgliedschaft in mitgliedschaften:
            m = frappe.get_doc("Mitgliedschaft", mitgliedschaft['name'])
            m.zuzug_massendruck = '0'
            m.letzte_bearbeitung_von = 'SP'
            m.zuzugs_rechnung = ''
            m.zuzug_korrespondenz = ''
            m.save(ignore_permissions=True)
        
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Abgeschlossen'
        massenlauf.error = ungedruckte if ungedruckte != '' else ''
        massenlauf.save(ignore_permissions=True)
    except Exception as err:
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Fehlgeschlagen'
        massenlauf.error += "------------\n{0}: {1}\n\n{2}\n------------".format(str(err), err_mitgl, frappe.utils.get_traceback())
        massenlauf.save(ignore_permissions=True)

def begruessung_bezahlung(massenlauf, sektion):
    try:
        mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 1, 'sektion_id': sektion}, fields=['name', 'begruessung_massendruck_dokument'])
        if len(mitgliedschaften) > 0:
            counter = 1
            output = PdfFileWriter()
            for mitgliedschaft in mitgliedschaften:
                if mitgliedschaft['begruessung_massendruck_dokument']:
                    output = frappe.get_print("Korrespondenz", mitgliedschaft['begruessung_massendruck_dokument'], 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
                if counter == 500:
                    file_name = "Begüssungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
                    file_name = file_name.split(".")[0]
                    file_name = file_name.replace(":", "-")
                    file_name = file_name + ".pdf"
                    
                    filedata = get_file_data_from_writer(output)
                    
                    _file = frappe.get_doc({
                        "doctype": "File",
                        "file_name": file_name,
                        "folder": "Home/Attachments",
                        "is_private": 1,
                        "content": filedata,
                        "attached_to_doctype": 'Massenlauf',
                        "attached_to_name": massenlauf
                    })
                    
                    _file.save(ignore_permissions=True)
                    output = PdfFileWriter()
                    counter = 1
                else:
                    counter += 1
            
            file_name = "Begüssungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
            file_name = file_name.split(".")[0]
            file_name = file_name.replace(":", "-")
            file_name = file_name + ".pdf"
            
            filedata = get_file_data_from_writer(output)
            
            _file = frappe.get_doc({
                "doctype": "File",
                "file_name": file_name,
                "folder": "Home/Attachments",
                "is_private": 1,
                "content": filedata,
                "attached_to_doctype": 'Massenlauf',
                "attached_to_name": massenlauf
            })
            
            _file.save(ignore_permissions=True)
        
        for mitgliedschaft in mitgliedschaften:
            m = frappe.get_doc("Mitgliedschaft", mitgliedschaft['name'])
            m.begruessung_massendruck = '0'
            m.begruessung_via_zahlung = '0'
            m.letzte_bearbeitung_von = 'SP'
            m.save(ignore_permissions=True)
        
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Abgeschlossen'
        massenlauf.error = ''
        massenlauf.save(ignore_permissions=True)
    except Exception as err:
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Fehlgeschlagen'
        massenlauf.error = str(err)
        massenlauf.save(ignore_permissions=True)

def begruessung_online(massenlauf, sektion):
    try:
        mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'begruessung_massendruck': 1, 'begruessung_via_zahlung': 0, 'sektion_id': sektion}, fields=['name', 'begruessung_massendruck_dokument'])
        if len(mitgliedschaften) > 0:
            counter = 1
            output = PdfFileWriter()
            for mitgliedschaft in mitgliedschaften:
                if mitgliedschaft['begruessung_massendruck_dokument']:
                    output = frappe.get_print("Korrespondenz", mitgliedschaft['begruessung_massendruck_dokument'], 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
                if counter == 500:
                    file_name = "Begüssungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
                    file_name = file_name.split(".")[0]
                    file_name = file_name.replace(":", "-")
                    file_name = file_name + ".pdf"
                    
                    filedata = get_file_data_from_writer(output)
                    
                    _file = frappe.get_doc({
                        "doctype": "File",
                        "file_name": file_name,
                        "folder": "Home/Attachments",
                        "is_private": 1,
                        "content": filedata,
                        "attached_to_doctype": 'Massenlauf',
                        "attached_to_name": massenlauf
                    })
                    
                    _file.save(ignore_permissions=True)
                    output = PdfFileWriter()
                    counter = 1
                else:
                    counter += 1
            
            file_name = "Begüssungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
            file_name = file_name.split(".")[0]
            file_name = file_name.replace(":", "-")
            file_name = file_name + ".pdf"
            
            filedata = get_file_data_from_writer(output)
            
            _file = frappe.get_doc({
                "doctype": "File",
                "file_name": file_name,
                "folder": "Home/Attachments",
                "is_private": 1,
                "content": filedata,
                "attached_to_doctype": 'Massenlauf',
                "attached_to_name": massenlauf
            })
            
            _file.save(ignore_permissions=True)
        
        for mitgliedschaft in mitgliedschaften:
            m = frappe.get_doc("Mitgliedschaft", mitgliedschaft['name'])
            m.begruessung_massendruck = '0'
            m.letzte_bearbeitung_von = 'SP'
            m.save(ignore_permissions=True)
        
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Abgeschlossen'
        massenlauf.error = ''
        massenlauf.save(ignore_permissions=True)
    except Exception as err:
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Fehlgeschlagen'
        massenlauf.error = str(err)
        massenlauf.save(ignore_permissions=True)

def korrespondenz(massenlauf, sektion):
    try:
        korrespondenzen = frappe.get_list('Korrespondenz', filters={'massenlauf': 1, 'sektion_id': sektion}, fields=['name'])
        if len(korrespondenzen) > 0:
            counter = 1
            output = PdfFileWriter()
            for korrespondenz in korrespondenzen:
                output = frappe.get_print("Korrespondenz", korrespondenz['name'], 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
                if counter == 500:
                    file_name = "Korrespondenz_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
                    file_name = file_name.split(".")[0]
                    file_name = file_name.replace(":", "-")
                    file_name = file_name + ".pdf"
                    
                    filedata = get_file_data_from_writer(output)
                    
                    _file = frappe.get_doc({
                        "doctype": "File",
                        "file_name": file_name,
                        "folder": "Home/Attachments",
                        "is_private": 1,
                        "content": filedata,
                        "attached_to_doctype": 'Massenlauf',
                        "attached_to_name": massenlauf
                    })
                    
                    _file.save(ignore_permissions=True)
                    output = PdfFileWriter()
                    counter = 1
                else:
                    counter += 1
            
            file_name = "Korrespondenz_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
            file_name = file_name.split(".")[0]
            file_name = file_name.replace(":", "-")
            file_name = file_name + ".pdf"
            
            filedata = get_file_data_from_writer(output)
            
            _file = frappe.get_doc({
                "doctype": "File",
                "file_name": file_name,
                "folder": "Home/Attachments",
                "is_private": 1,
                "content": filedata,
                "attached_to_doctype": 'Massenlauf',
                "attached_to_name": massenlauf
            })
            
            _file.save(ignore_permissions=True)
        
        for korrespondenz in korrespondenzen:
            k = frappe.get_doc("Korrespondenz", korrespondenz['name'])
            k.massenlauf = '0'
            k.save(ignore_permissions=True)
        
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Abgeschlossen'
        massenlauf.error = ''
        massenlauf.save(ignore_permissions=True)
    except Exception as err:
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Fehlgeschlagen'
        massenlauf.error = str(err)
        massenlauf.save(ignore_permissions=True)

def rechnung(massenlauf, sektion):
    try:
        mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'rg_massendruck_vormerkung': 1, 'sektion_id': sektion}, fields=['rg_massendruck', 'name'])
        if len(mitgliedschaften) > 0:
            counter = 1
            output = PdfFileWriter()
            for mitgliedschaft in mitgliedschaften:
                if mitgliedschaft['rg_massendruck']:
                    output = frappe.get_print("Sales Invoice", mitgliedschaft['rg_massendruck'], 'Automatisierte Mitgliedschaftsrechnung', as_pdf = True, output = output, ignore_zugferd=True)
                if counter == 500:
                    file_name = "Mitgliedschaftsrechnungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
                    file_name = file_name.split(".")[0]
                    file_name = file_name.replace(":", "-")
                    file_name = file_name + ".pdf"
                    
                    filedata = get_file_data_from_writer(output)
                    
                    _file = frappe.get_doc({
                        "doctype": "File",
                        "file_name": file_name,
                        "folder": "Home/Attachments",
                        "is_private": 1,
                        "content": filedata,
                        "attached_to_doctype": 'Massenlauf',
                        "attached_to_name": massenlauf
                    })
                    
                    _file.save(ignore_permissions=True)
                    output = PdfFileWriter()
                    counter = 1
                else:
                    counter += 1
            
            file_name = "Mitgliedschaftsrechnungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
            file_name = file_name.split(".")[0]
            file_name = file_name.replace(":", "-")
            file_name = file_name + ".pdf"
            
            filedata = get_file_data_from_writer(output)
            
            _file = frappe.get_doc({
                "doctype": "File",
                "file_name": file_name,
                "folder": "Home/Attachments",
                "is_private": 1,
                "content": filedata,
                "attached_to_doctype": 'Massenlauf',
                "attached_to_name": massenlauf
            })
            
            _file.save(ignore_permissions=True)
        
        for m in mitgliedschaften:
            m = frappe.get_doc("Mitgliedschaft", m['name'])
            m.rg_massendruck_vormerkung = '0'
            m.rg_massendruck = ''
            m.save(ignore_permissions=True)
        
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Abgeschlossen'
        massenlauf.error = ''
        massenlauf.save(ignore_permissions=True)
    except Exception as err:
        massenlauf = frappe.get_doc("Massenlauf", massenlauf)
        massenlauf.status = 'Fehlgeschlagen'
        massenlauf.error = str(err)
        massenlauf.save(ignore_permissions=True)
