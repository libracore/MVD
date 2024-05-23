# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json

class Postnotiz(Document):
    pass

def create_postnotiz(postnotiz, postretouren_log):
    try:
        new_postnotiz = frappe.get_doc({
            'doctype': 'Postnotiz',
            'postretouren_log': postretouren_log,
            'postnotiz': json.dumps(postnotiz.__dict__, ensure_ascii=False)
        })
        
        new_postnotiz.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return 1
        
    except Exception as err:
        return err
