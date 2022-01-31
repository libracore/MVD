# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_open_data(sektion=None):
    sektion_filter = ''
    if sektion:
        sektion_filter = " AND `sektion_id` = '{sektion}'".format(sektion=sektion)
    
    # arbeits backlog
    abl_qty = frappe.db.sql("""SELECT
                                    COUNT(`name`) AS `qty`
                                FROM `tabArbeits Backlog`
                                WHERE `status` = 'Open'
                                {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    
    # Validierung
    validierung_total = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabArbeits Backlog`
                                        WHERE `status` = 'Open'
                                        AND `typ` IN ('Daten Validieren', 'Beitritts Validierung')
                                        {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    validierung_allgemein = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabArbeits Backlog`
                                        WHERE `status` = 'Open'
                                        AND `typ` = 'Daten Validieren'
                                        {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    validierung_beitritt = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabArbeits Backlog`
                                        WHERE `status` = 'Open'
                                        AND `typ` = 'Beitritts Validierung'
                                        {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    
    # Kündigungen
    kuendigung_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabArbeits Backlog` WHERE `status` = 'Open' AND `typ` = 'Kündigung verarbeiten'{sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    
    return {
        'arbeits_backlog': {
            'qty': abl_qty
        },
        'validierung': {
            'qty': validierung_total,
            'allgemein': validierung_allgemein,
            'beitritt': validierung_beitritt
        },
        'kuendigung': {
            'qty': kuendigung_qty
        }
    }
