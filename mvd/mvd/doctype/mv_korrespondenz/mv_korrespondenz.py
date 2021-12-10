# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from six import BytesIO
import openpyxl
from openpyxl.styles import Font
from frappe.utils.data import now
from frappe.utils.csvutils import to_csv as make_csv

class MVKorrespondenz(Document):
    pass

@frappe.whitelist()
def check_if_vorlage_exist(vorlage, titel, override=False):
    if isinstance(vorlage, str):
        vorlage = json.loads(vorlage)
    if not override:
        if not frappe.db.exists('MV Korrespondenz Vorlage', titel):
            return create_vorlage(vorlage, titel)
        else:
            return 'alreadyExist'
    else:
        return update_vorlage(vorlage, titel)

def create_vorlage(vorlage, titel):
    new_vorlage = frappe.get_doc({
        "doctype": "MV Korrespondenz Vorlage",
        "vorlagen_titel": titel,
        "sektion_id": vorlage['sektion_id'],
        "check_ansprechperson": vorlage['check_ansprechperson'],
        "mit_ausweis": vorlage['mit_ausweis'],
        "ort": vorlage['ort'],
        "brieftitel": vorlage['brieftitel'],
        "check_anrede": vorlage['check_anrede'],
        "anrede": vorlage['anrede'],
        "inhalt": vorlage['inhalt'],
        "inhalt_2": vorlage['inhalt_2']
    })
    new_vorlage.insert()
    return 'done'

def update_vorlage(vorlage, titel):
    old_vorlage = frappe.get_doc("MV Korrespondenz Vorlage", titel)
    old_vorlage.sektion_id = vorlage['sektion_id']
    old_vorlage.check_ansprechperson = vorlage['check_ansprechperson']
    old_vorlage.mit_ausweis = vorlage['mit_ausweis']
    old_vorlage.ort = vorlage['ort']
    old_vorlage.brieftitel = vorlage['brieftitel']
    old_vorlage.check_anrede = vorlage['check_anrede']
    old_vorlage.anrede = vorlage['anrede']
    old_vorlage.inhalt = vorlage['inhalt']
    old_vorlage.inhalt_2 = vorlage['inhalt_2']
    old_vorlage.save()
    return 'done'


@frappe.whitelist()
def create_sammel_pdf(korrespondenzen):
    exist_korrespondenz_folder()
    
    if isinstance(korrespondenzen, str):
        korrespondenzen = json.loads(korrespondenzen)
    
    return

@frappe.whitelist()
def create_sammel_xlsx(korrespondenzen):
    exist_korrespondenz_folder()
    
    if isinstance(korrespondenzen, str):
        korrespondenzen = json.loads(korrespondenzen)
    korrespondenz_data = get_korrespondenz_data(korrespondenzen)
    
    xlsx_file = make_korrespondenz_xlsx(korrespondenz_data)
    
    file_data = xlsx_file.getvalue()
    
    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": "korrespondenz_export_{datetime}.xlsx".format(datetime=now().replace(" ", "_")),
        "folder": "Home/Korrespondenz",
        "is_private": 1,
        "content": file_data
    })
    _file.save()
    
    return

@frappe.whitelist()
def create_sammel_csv(korrespondenzen):
    exist_korrespondenz_folder()
    
    if isinstance(korrespondenzen, str):
        korrespondenzen = json.loads(korrespondenzen)
    korrespondenz_data = get_korrespondenz_data(korrespondenzen)
    
    csv_file = make_csv(korrespondenz_data)
    
    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": "korrespondenz_export_{datetime}.csv".format(datetime=now().replace(" ", "_")),
        "folder": "Home/Korrespondenz",
        "is_private": 1,
        "content": csv_file
    })
    _file.save()
    
    return

def get_korrespondenz_data(korrespondenzen):
    data = []
    titel = ['Mitglieder Nr.', 'Sektion', 'Ansprechperson', 'Tel. Mitarbeiter:inn', 'E-Mail Mitarbeiter:inn', 'Adressblock', 'Ort', 'Datum', 'Brieftitel', 'Anrede', 'Inhalt 1. Seite', 'Inhalt 2. Seite']
    data.append(titel)
    
    for _korrespondenz in korrespondenzen:
        korrespondenz = frappe.get_doc("MV Korrespondenz", _korrespondenz)
        mitgliedschaft = frappe.get_doc("MV Mitgliedschaft", korrespondenz.mv_mitgliedschaft)
        _data = [
            mitgliedschaft.mitglied_nr,
            mitgliedschaft.sektion_id,
            korrespondenz.ansprechperson or '',
            korrespondenz.tel_ma or '',
            korrespondenz.email_ma or '',
            mitgliedschaft.adressblock,
            korrespondenz.ort,
            korrespondenz.datum,
            korrespondenz.brieftitel,
            korrespondenz.anrede if korrespondenz.check_anrede else mitgliedschaft.briefanrede,
            korrespondenz.inhalt,
            korrespondenz.inhalt_2 or ''
        ]
        data.append(_data)
    
    return data

def make_korrespondenz_xlsx(korrespondenz_data):
    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet('KorrespondenzExport', 0)
    
    row1 = ws.row_dimensions[1]
    row1.font = Font(name='Calibri',bold=False)
    
    for row in korrespondenz_data:
        clean_row = []
        for item in row:
            clean_row.append(item)

        ws.append(clean_row)

    xlsx_file = BytesIO()
    wb.save(xlsx_file)
    
    return xlsx_file

def exist_korrespondenz_folder():
    exist = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabFile` WHERE `name` = 'Home/Korrespondenz' AND `is_folder` = 1""", as_dict=True)
    if exist[0].qty != 1:
        new_folder = frappe.get_doc({
            "doctype": "File",
            "file_name": "Korrespondenz",
            "folder": "Home",
            "is_folder": 1
        })
        new_folder.insert()
        frappe.db.commit()
    return True
