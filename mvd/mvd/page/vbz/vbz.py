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
                                        AND `typ` = 'Daten Validieren'
                                        {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    v_online_beitritt_qty = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabMitgliedschaft`
                                        WHERE `validierung_notwendig` = 1
                                        AND `status_c` = 'Online-Beitritt'
                                        {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    _v_online_beitritt = frappe.db.sql("""SELECT
                                            `name`
                                        FROM `tabMitgliedschaft`
                                        WHERE `validierung_notwendig` = 1
                                        AND `status_c` = 'Online-Beitritt'
                                        {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)
    v_online_beitritt = 'x'
    for online_beitritt in _v_online_beitritt:
        v_online_beitritt += ',' + online_beitritt.name
    if len(_v_online_beitritt) > 0:
        v_online_beitritt = v_online_beitritt.replace("x,", "")
    else:
        v_online_beitritt = ''
    
    v_online_anmeldung_qty = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabMitgliedschaft`
                                        WHERE `validierung_notwendig` = 1
                                        AND `status_c` = 'Online-Anmeldung'
                                        {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    _v_online_anmeldung = frappe.db.sql("""SELECT
                                            `name`
                                        FROM `tabMitgliedschaft`
                                        WHERE `validierung_notwendig` = 1
                                        AND `status_c` = 'Online-Anmeldung'
                                        {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)
    v_online_anmeldung = 'x'
    for online_anmeldung in _v_online_anmeldung:
        v_online_anmeldung += ',' + online_anmeldung.name
    if len(_v_online_beitritt) > 0:
        v_online_anmeldung = v_online_anmeldung.replace("x,", "")
    else:
        v_online_anmeldung = ''
    
    v_online_kuendigung_qty = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabMitgliedschaft`
                                        WHERE `validierung_notwendig` = 1
                                        AND `status_c` = 'Online-Kündigung'
                                        {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    _v_online_kuendigung = frappe.db.sql("""SELECT
                                            `name`
                                        FROM `tabMitgliedschaft`
                                        WHERE `validierung_notwendig` = 1
                                        AND `status_c` = 'Online-Kündigung'
                                        {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)
    v_online_kuendigung = 'x'
    for online_kuendigung in _v_online_kuendigung:
        v_online_kuendigung += ',' + online_kuendigung.name
    if len(_v_online_kuendigung) > 0:
        v_online_kuendigung = v_online_kuendigung.replace("x,", "")
    else:
        v_online_kuendigung = ''
    
    v_zuzug_qty = frappe.db.sql("""SELECT
                                        COUNT(`name`) AS `qty`
                                    FROM `tabMitgliedschaft`
                                    WHERE `validierung_notwendig` = 1
                                    AND `status_c` = 'Zuzug'
                                    {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    _v_zuzug = frappe.db.sql("""SELECT
                                        `name`
                                    FROM `tabMitgliedschaft`
                                    WHERE `validierung_notwendig` = 1
                                    AND `status_c` = 'Zuzug'
                                    {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)
    v_zuzug = 'x'
    for zuzug in _v_zuzug:
        v_zuzug += ',' + zuzug.name
    if len(_v_zuzug) > 0:
        v_zuzug = v_zuzug.replace("x,", "")
    else:
        v_zuzug = ''
    
    # kündigung massenlauf
    kuendigung_qty = frappe.db.sql("""SELECT
                                        COUNT(`name`) AS `qty`
                                    FROM `tabMitgliedschaft`
                                    WHERE `kuendigung_verarbeiten` = 1
                                    {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    _kuendigung = frappe.db.sql("""SELECT
                                        `name`
                                    FROM `tabMitgliedschaft`
                                    WHERE `kuendigung_verarbeiten` = 1
                                    {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)
    kuendigung = 'x'
    for k in _kuendigung:
        kuendigung += ',' + k.name
    if len(_kuendigung) > 0:
        kuendigung = kuendigung.replace("x,", "")
    else:
        kuendigung = ''
    
    # massenlauf total
    massenlauf_total = kuendigung_qty
    
    return {
        'arbeits_backlog': {
            'qty': abl_qty
        },
        'massenlauf_total': massenlauf_total,
        'validierung': {
            'qty': validierung_total,
            'online_beitritt': {
                'qty': v_online_beitritt_qty,
                'names': v_online_beitritt
            },
            'online_anmeldung': {
                'qty': v_online_anmeldung_qty,
                'names': v_online_anmeldung
            },
            'online_kuendigung': {
                'qty': v_online_kuendigung_qty,
                'names': v_online_kuendigung
            },
            'zuzug': {
                'qty': v_zuzug_qty,
                'names': v_zuzug
            }
        },
        'kuendigung_massenlauf': {
            'qty': kuendigung_qty,
            'names': kuendigung
        }
    }
