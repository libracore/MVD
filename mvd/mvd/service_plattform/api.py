# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft import mvm_mitglieder, mvm_kuendigung, mvm_sektionswechsel
import json
import requests

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
# ausgehend
# ---------------------------------------------------
def neue_mitglieder_nummer(sektion_code):
    url = frappe.db.get_single_value('Service Plattform API', 'api_url')
    secret = frappe.db.get_single_value('Service Plattform API', 'api_secret')
    mitglied_id = requests.post(url, json = {"sektionCode": sektion_code})
    return mitglied_id

def update_mvm(mvm):
    # DoSomeMagic
    url = frappe.db.get_single_value('Service Plattform API', 'api_url')
    secret = frappe.db.get_single_value('Service Plattform API', 'api_secret')
    sp_connection = requests.post(url, json = mvm)
    return sp_connection

# eingehend
# ---------------------------------------------------
# create/update existing MV Mitgliedschaft
@frappe.whitelist()
def mitglieder(**mitgliedschaft):
    frappe.log_error("{0}".format(mitgliedschaft), 'Eingang API: mitglieder')
    return mvm_mitglieder(mitgliedschaft)

# @frappe.whitelist()
# def kuendigung(**mitgliedschaft):
    # return mvm_kuendigung(**mitgliedschaft)

# @frappe.whitelist()
# def sektionswechsel(sektion_code):
    # return mvm_sektionswechsel(sektion_code)
