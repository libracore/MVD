# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft import mvm_mitglieder, mvm_neue_mitglieder_nummer, mvm_kuendigung, mvm_sektionswechsel
import json

# for test
# ---------------------------------------------------
@frappe.whitelist()
def whoami(type='light'):
    user = frappe.session.user
    if type == 'full':
        user = frappe.get_doc("User", user)
        return user
    else:
        return user

# live functions
# ---------------------------------------------------
def neue_mitglieder_nummer(sektion_code):
    return mvm_neue_mitglieder_nummer(sektion_code)

# create/update existing MV Mitgliedschaft
@frappe.whitelist()
def mitglieder(mitgliedschaft):
    frappe.log_error("{0}".format(mitgliedschaft), 'eingang api call')
    if isinstance(mitgliedschaft, str):
      mitgliedschaft = json.loads(mitgliedschaft)
    return mvm_mitglieder(**mitgliedschaft)

# @frappe.whitelist()
# def kuendigung(**mitgliedschaft):
    # return mvm_kuendigung(**mitgliedschaft)

# @frappe.whitelist()
# def sektionswechsel(sektion_code):
    # return mvm_sektionswechsel(sektion_code)
