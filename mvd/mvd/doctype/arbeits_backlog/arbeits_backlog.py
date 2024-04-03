# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from PyPDF2 import PdfFileWriter
from frappe.utils.data import now

class ArbeitsBacklog(Document):
    pass

def create_abl(typ, mitgliedschaft):
    new_abl = frappe.get_doc({
        "doctype": "Arbeits Backlog",
        "typ": typ,
        "mv_mitgliedschaft": mitgliedschaft.name,
        "sektion_id": mitgliedschaft.sektion_id
    })
    
    new_abl.insert(ignore_permissions=True)
    frappe.db.commit()

@frappe.whitelist()
def kuendigungs_massendruck():
    ausstehende_drucke = frappe.db.get_list('Arbeits Backlog',
        filters={
            'status': 'Open',
            'typ': 'Kündigung verarbeiten'
        },
        fields=['name', 'mv_mitgliedschaft']
    )
    
    if len(ausstehende_drucke) > 0:
        exist_kuendigungen_folder()
        output = PdfFileWriter()
        
        for ausstehender_druck in ausstehende_drucke:
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", ausstehender_druck.mv_mitgliedschaft)
            abl = frappe.get_doc("Arbeits Backlog", ausstehender_druck.name)
            output = frappe.get_print("Mitgliedschaft", mitgliedschaft.name, 'Kündigungsbestätigung', as_pdf = True, output = output)
            mitgliedschaft.kuendigung_verarbeiten = 0
            mitgliedschaft.save()
            abl.status = 'Completed'
            abl.save(ignore_permissions=True)
            
        pdf = frappe.utils.pdf.get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": "Kündigungen_Sammeldruck_{datetime}.pdf".format(datetime=now().replace(" ", "_")),
            "folder": "Home/Kündigungen",
            "is_private": 1,
            "content": pdf
        })
        _file.save(ignore_permissions=True)
        
        return 'done'
    else:
        return 'keine daten'

def exist_kuendigungen_folder():
    exist = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabFile` WHERE `name` = 'Home/Kündigungen' AND `is_folder` = 1""", as_dict=True)
    if exist[0].qty != 1:
        new_folder = frappe.get_doc({
            "doctype": "File",
            "file_name": "Kündigungen",
            "folder": "Home",
            "is_folder": 1
        })
        new_folder.insert(ignore_permissions=True)
        frappe.db.commit()
    return True

def close_open_validations(mitgliedschaft, typ):
    open_abl = frappe.db.sql("""SELECT `name` FROM `tabArbeits Backlog` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}' AND `status` = 'Open' AND `typ` = '{typ}'""".format(mitgliedschaft=mitgliedschaft, typ=typ), as_dict=True)
    
    for abl in open_abl:
        abl = frappe.get_doc("Arbeits Backlog", abl.name)
        abl.status = 'Completed'
        abl.save(ignore_permissions=True)
