# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

# for test
@frappe.whitelist()
def whoami(type='light'):
    user = frappe.session.user
    if type == 'full':
        user = frappe.get_doc("User", user)
        return user
    else:
        return user

# live functions
def neue_mitglieder_nummer(sektion_code):
    return "Methode in Arbeit"

@frappe.whitelist()
def mitglieder():
    return "Methode in Arbeit"

@frappe.whitelist()
def kuendigung():
    return "Methode in Arbeit"

@frappe.whitelist()
def sektionswechsel(sektion_code):
    return "Methode in Arbeit"
