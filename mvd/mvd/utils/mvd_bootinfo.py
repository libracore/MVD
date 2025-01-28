# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def boot_session(bootinfo):
    bootinfo.default_sektion, bootinfo.multi_sektion = get_default_sektion()
    bootinfo.default_beratungs_sender = get_default_beratungs_sender(bootinfo.default_sektion)

def get_default_sektion():
    # ~ sektionen = frappe.db.sql("""SELECT `for_value` FROM `tabUser Permission` WHERE `allow` = 'Sektion' AND `is_default` = 1 AND `user` = '{user}'""".format(user=frappe.session.user), as_dict=True)
    sektionen = frappe.db.sql("""SELECT `for_value` FROM `tabUser Permission` WHERE `allow` = 'Sektion' AND `user` = '{user}' ORDER BY `is_default` DESC""".format(user=frappe.session.user), as_dict=True)
    if len(sektionen) > 1:
        return sektionen[0].for_value, True
    elif len(sektionen) > 0:
        return sektionen[0].for_value, False
    else:
        return '', False

def get_default_beratungs_sender(default_sektion=None):
    if default_sektion:
        default_beratungs_sender = frappe.db.get_value("Sektion", default_sektion, 'legacy_mail_absender_mail')
        return default_beratungs_sender
    else:
        return None

def login_check(login_manager):
    if not login_manager.oauth:
        frappe.log_error(str(login_manager.user), "Login ohne 2FA: {0}".format(str(login_manager.user)))