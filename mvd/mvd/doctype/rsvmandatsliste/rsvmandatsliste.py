# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint

class RSVMandatsliste(Document):
    pass

def reset_status(rsvmandatsliste):
    rsvml = frappe.get_doc("RSVMandatsliste", rsvmandatsliste)
    refs = frappe.db.count("RSVMandat", {'rsvmandatsliste': rsvml.name}, ['name'])
    if cint(refs) < 2 and rsvml.typ != 'EM':
        frappe.db.set_value("RSVMandatsliste", rsvml.name, "typ", "EM")
    elif cint(refs) >= 2 and cint(refs) <= 9 and rsvml.typ != 'KGM':
        frappe.db.set_value("RSVMandatsliste", rsvml.name, "typ", "KGM")
    elif cint(refs) > 9 and rsvml.typ != 'GGM':
        frappe.db.set_value("RSVMandatsliste", rsvml.name, "typ", "GGM")
