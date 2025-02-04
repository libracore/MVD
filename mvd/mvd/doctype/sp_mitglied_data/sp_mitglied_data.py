# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr
from mvd.mvd.doctype.mitgliedschaft.utils import prepare_mvm_for_sp

class SPMitgliedData(Document):
    pass

def create_or_update_sp_mitglied_data(mitglied_nr, mitgliedschaft=None):
    if frappe.db.exists("SP Mitglied Data", mitglied_nr):
        update(mitglied_nr, mitgliedschaft)
    else:
        create(mitglied_nr, mitgliedschaft)

def create(mitglied_nr, mitgliedschaft):
    if not mitgliedschaft:
        mitglied_id = get_mitglied_id_from_nr(mitglied_nr=mitglied_nr, ignore_inaktiv=True)
        if frappe.db.exists("Mitgliedschaft", mitglied_id):
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitglied_id)
    if mitgliedschaft:
        data =  prepare_mvm_for_sp(mitgliedschaft)
        new_record = frappe.get_doc({
            'doctype': 'SP Mitglied Data',
            'mitglied_nr': mitglied_nr,
            'json': json.dumps(data, indent=2)
        })
        new_record.insert()
        frappe.db.commit()

def update(mitglied_nr, mitgliedschaft):
    if not mitgliedschaft:
        mitglied_id = get_mitglied_id_from_nr(mitglied_nr=mitglied_nr, ignore_inaktiv=True)
        if frappe.db.exists("Mitgliedschaft", mitglied_id):
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitglied_id)
    if mitgliedschaft:
        data =  prepare_mvm_for_sp(mitgliedschaft)
        existing_record = frappe.get_doc("SP Mitglied Data", mitglied_nr)
        existing_record.json = json.dumps(data, indent=2)
        existing_record.save()
        frappe.db.commit()

def initiale_daten_anlage():
    try:
        mitgliedschaften = frappe.db.sql("""SELECT DISTINCT `mitglied_nr` FROM `tabMitgliedschaft` WHERE `status_c` != 'Inaktiv' AND `mitglied_nr` LIKE 'MV0%' ORDER BY `creation` DESC""", as_dict=True)
        loop = 1
        total = len(mitgliedschaften)
        for mitgliedschaft in mitgliedschaften:
            print("{0} von {1}".format(loop, total))
            create_or_update_sp_mitglied_data(mitgliedschaft.mitglied_nr)
            loop += 1
        print("Done")
    except Exception as err:
        print("Patch initiale Datenanlage (SP Mitglied Data) failed")
        print(str(err))
        pass
    return