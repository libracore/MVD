# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from mvd.mvd.service_plattform.api import send_postnotiz_to_sp
from mvd.mvd.doctype.mitgliedschaft.utils import prepare_mvm_for_sp

class Postnotiz(Document):
    def send_to_sp(self):
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", self.mitgliedid)
        json_to_send = {
            "kategorie": self.kategorie,
            "notiz": self.notiz,
            "mitglied": prepare_mvm_for_sp(mitgliedschaft)
        }
        send_postnotiz_to_sp(json_to_send)
        return

def create_postnotiz(postnotiz, postretour, postretouren_log):
    try:
        new_postnotiz = frappe.get_doc({
            'doctype': 'Postnotiz',
            'postretouren_log': postretouren_log,
            'postnotiz': json.dumps(postnotiz.__dict__, ensure_ascii=False),
            'mitgliedid': postretour.mitgliedId,
            'mitgliednummer': postnotiz.mitgliedNummer,
            'kategorie': postnotiz.kategorie,
            'notiz': postnotiz.notiz
        })
        
        new_postnotiz.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return 1
        
    except Exception as err:
        return err
