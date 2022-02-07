# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from PyPDF2 import PdfFileWriter
from frappe.utils.data import add_days, getdate, now, today
from frappe.utils.pdf import get_file_data_from_writer

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
    
    # korrespondenz massenlauf
    korrespondenz_qty = frappe.db.sql("""SELECT
                                        COUNT(`name`) AS `qty`
                                    FROM `tabKorrespondenz`
                                    WHERE `massenlauf` = 1
                                    {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    _korrespondenz = frappe.db.sql("""SELECT
                                        `name`
                                    FROM `tabKorrespondenz`
                                    WHERE `massenlauf` = 1
                                    {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)
    korrespondenz = 'x'
    for k in _korrespondenz:
        korrespondenz += ',' + k.name
    if len(_korrespondenz) > 0:
        korrespondenz = korrespondenz.replace("x,", "")
    else:
        korrespondenz = ''
    
    # zuzugs massenlauf
    zuzug_qty = frappe.db.sql("""SELECT
                                        COUNT(`name`) AS `qty`
                                    FROM `tabMitgliedschaft`
                                    WHERE `zuzug_massendruck` = 1
                                    {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    _zuzug = frappe.db.sql("""SELECT
                                        `name`
                                    FROM `tabMitgliedschaft`
                                    WHERE `zuzug_massendruck` = 1
                                    {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)
    zuzug = 'x'
    for z in _zuzug:
        zuzug += ',' + z.name
    if len(_zuzug) > 0:
        zuzug = zuzug.replace("x,", "")
    else:
        zuzug = ''
    
    # mitgliedschaftsrechnung massenlauf
    rg_massendruck_qty = frappe.db.sql("""SELECT
                                        COUNT(`name`) AS `qty`
                                    FROM `tabMitgliedschaft`
                                    WHERE `rg_massendruck_vormerkung` = 1
                                    {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)[0].qty
    _rg_massendruck = frappe.db.sql("""SELECT
                                        `name`
                                    FROM `tabMitgliedschaft`
                                    WHERE `rg_massendruck_vormerkung` = 1
                                    {sektion_filter}""".format(sektion_filter=sektion_filter), as_dict=True)
    rg_massendruck = 'x'
    for rgm in _rg_massendruck:
        rg_massendruck += ',' + rgm.name
    if len(_rg_massendruck) > 0:
        rg_massendruck = rg_massendruck.replace("x,", "")
    else:
        rg_massendruck = ''
    
    # massenlauf total
    massenlauf_total = kuendigung_qty + korrespondenz_qty + zuzug_qty + rg_massendruck_qty
    
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
        },
        'korrespondenz_massenlauf': {
            'qty': korrespondenz_qty,
            'names': korrespondenz
        },
        'zuzug_massenlauf': {
            'qty': zuzug_qty,
            'names': zuzug
        },
        'rg_massenlauf': {
            'qty': rg_massendruck_qty,
            'names': rg_massendruck
        }
    }

@frappe.whitelist()
def korrespondenz_massenlauf():
    korrespondenzen = frappe.get_list('Korrespondenz', filters={'massenlauf': 1}, fields=['name'])
    if len(korrespondenzen) > 0:
        output = PdfFileWriter()
        for korrespondenz in korrespondenzen:
            output = frappe.get_print("Korrespondenz", korrespondenz['name'], 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
            
        file_name = "Korrespondenz_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
        file_name = file_name.split(".")[0]
        file_name = file_name.replace(":", "-")
        file_name = file_name + ".pdf"
        
        filedata = get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home",
            "is_private": 1,
            "content": filedata
        })
        
        _file.save(ignore_permissions=True)
        
        for korrespondenz in korrespondenzen:
            k = frappe.get_doc("Korrespondenz", korrespondenz['name'])
            k.massenlauf = '0'
            k.save(ignore_permissions=True)
        
        return _file.name
    else:
        frappe.throw("Es gibt keine Korrespondenzen die für einen Massenlauf vorgemerkt sind.")

@frappe.whitelist()
def kuendigung_massenlauf():
    mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'kuendigung_verarbeiten': 1}, fields=['name'])
    if len(mitgliedschaften) > 0:
        output = PdfFileWriter()
        for mitgliedschaft in mitgliedschaften:
            output = frappe.get_print("Mitgliedschaft", mitgliedschaft['name'], 'Kündigungsbestätigung', as_pdf = True, output = output, ignore_zugferd=True)
            
        file_name = "Kündigungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
        file_name = file_name.split(".")[0]
        file_name = file_name.replace(":", "-")
        file_name = file_name + ".pdf"
        
        filedata = get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home",
            "is_private": 1,
            "content": filedata
        })
        
        _file.save(ignore_permissions=True)
        
        for mitgliedschaft in mitgliedschaften:
            m = frappe.get_doc("Mitgliedschaft", mitgliedschaft['name'])
            m.kuendigung_verarbeiten = '0'
            m.save(ignore_permissions=True)
        
        return _file.name
    else:
        frappe.throw("Es gibt keine Mitgliedschaften die für einen Kündigungs-Massenlauf vorgemerkt sind.")

@frappe.whitelist()
def zuzug_massenlauf():
    mitgliedschaften = frappe.get_list('Mitgliedschaft', filters={'zuzug_massendruck': 1}, fields=['name', 'zuzugs_rechnung', 'zuzug_korrespondenz'])
    if len(mitgliedschaften) > 0:
        output = PdfFileWriter()
        for mitgliedschaft in mitgliedschaften:
            if mitgliedschaft['zuzugs_rechnung']:
                output = frappe.get_print("Sales Invoice", mitgliedschaft['zuzugs_rechnung'], 'Automatisierte Mitgliedschaftsrechnung', as_pdf = True, output = output, ignore_zugferd=True)
            else:
                output = frappe.get_print("Korrespondenz", mitgliedschaft['zuzug_korrespondenz'], 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
            
        file_name = "Zuzugs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
        file_name = file_name.split(".")[0]
        file_name = file_name.replace(":", "-")
        file_name = file_name + ".pdf"
        
        filedata = get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home",
            "is_private": 1,
            "content": filedata
        })
        
        _file.save(ignore_permissions=True)
        
        for mitgliedschaft in mitgliedschaften:
            m = frappe.get_doc("Mitgliedschaft", mitgliedschaft['name'])
            m.zuzug_massendruck = '0'
            m.save(ignore_permissions=True)
        
        return _file.name
    else:
        frappe.throw("Es gibt keine Mitgliedschaften die für einen Zuzugs-Massenlauf vorgemerkt sind.")

@frappe.whitelist()
def rg_massenlauf():
    sinvs = frappe.get_list('Mitgliedschaft', filters={'rg_massendruck_vormerkung': 1}, fields=['rg_massendruck', 'name'])
    if len(sinvs) > 0:
        output = PdfFileWriter()
        for sinv in sinvs:
            if sinv['rg_massendruck']:
                output = frappe.get_print("Sales Invoice", sinv['rg_massendruck'], 'Automatisierte Mitgliedschaftsrechnung', as_pdf = True, output = output, ignore_zugferd=True)
            
        file_name = "Mitgliedschaftsrechnungs_Sammel_PDF_{datetime}".format(datetime=now().replace(" ", "_"))
        file_name = file_name.split(".")[0]
        file_name = file_name.replace(":", "-")
        file_name = file_name + ".pdf"
        
        filedata = get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home",
            "is_private": 1,
            "content": filedata
        })
        
        _file.save(ignore_permissions=True)
        
        for sinv in sinvs:
            m = frappe.get_doc("Mitgliedschaft", sinv['name'])
            m.rg_massendruck_vormerkung = '0'
            m.rg_massendruck = ''
            m.save(ignore_permissions=True)
        
        return _file.name
    else:
        frappe.throw("Es gibt keine Mitgliedschaften die für einen Rechnungs-Massenlauf vorgemerkt sind.")
