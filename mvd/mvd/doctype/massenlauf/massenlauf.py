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
            'massenlauf': massenlauf.name
        }
        enqueue("mvd.mvd.doctype.massenlauf.massenlauf.mahnung", queue='long', job_name='Verarbeite Massenlauf {0}'.format(massenlauf.name), timeout=5000, **args)
        return 1
    if massenlauf.typ == 'Kündigung':
        args = {
            'massenlauf': massenlauf.name
        }
        enqueue("mvd.mvd.doctype.massenlauf.massenlauf.kuendigung", queue='long', job_name='Verarbeite Massenlauf {0}'.format(massenlauf.name), timeout=5000, **args)
        return 1

def mahnung(massenlauf):
    try:
        mahnungen = frappe.get_list('Mahnung', filters={'massenlauf_referenz': massenlauf, 'docstatus': 1}, fields=['name'])
        output = PdfFileWriter()
        for mahnung in mahnungen:
            output = frappe.get_print("Mahnung", mahnung['name'], 'Mahnung', as_pdf = True, output = output, ignore_zugferd=True)
            
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

def kuendigung(massenlauf):
    try:
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
