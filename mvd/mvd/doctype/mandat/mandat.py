# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Mandat(Document):
    pass

@frappe.whitelist()
def create_mandat(sektion, beratung, mitglied, berater_in, typ, bemerkung):
    mandat = frappe.new_doc("Mandat")

    mandat.mv_mitgliedschaft = mitglied
    mandat.sektion_id = sektion
    mandat.beratung = beratung
    mandat.kontaktperson = berater_in
    mandat.typ = typ
    mandat.bemerkung = bemerkung

    mandat.insert(ignore_permissions=True)

    return mandat.name
