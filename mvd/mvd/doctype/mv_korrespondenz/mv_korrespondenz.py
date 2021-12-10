# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json

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
