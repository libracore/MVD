# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def boot_session(bootinfo):
    bootinfo.default_sektion = get_default_sektion()

def get_default_sektion():
    sektionen = frappe.db.sql("""SELECT `for_value` FROM `tabUser Permission` WHERE `allow` = 'Sektion' AND `is_default` = 1 AND `user` = '{user}'""".format(user=frappe.session.user), as_dict=True)
    if len(sektionen) > 0:
        return sektionen[0].for_value
    else:
        return ''
