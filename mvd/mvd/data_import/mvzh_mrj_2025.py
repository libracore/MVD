# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd
from tqdm import tqdm

def read_csv(file_name, site_name='libracore.mieterverband.ch', limit=False, bench='frappe'):
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench), sep=";")
    
    mvzh_rgs = frappe.db.sql("""
        SELECT
            `sinvtbl`.`name` AS `sinv`,
            `fak`.`name` AS `fakrg`,
            `sinvtbl`.`mv_mitgliedschaft` AS `mitgliedschaft`,
            `mitgl`.`mitglied_nr`
        FROM `tabSales Invoice` AS `sinvtbl`
        JOIN `tabMitgliedschaft` AS `mitgl` ON `mitgl`.`name` = `sinvtbl`.`mv_mitgliedschaft`
        LEFT JOIN `tabFakultative Rechnung` AS `fak` ON `fak`.`sales_invoice` = `sinvtbl`.`name`
        WHERE `sinvtbl`.`mrj_sektions_selektion` IN ('MRJ-MVZH--655192', 'MRJ-MVZH--655195')
    """, as_dict=True)

    for mvzh_rg in tqdm(mvzh_rgs, desc="MVZH MRJ 2025", unit=" Corrections", total=len(mvzh_rgs)):
    # for mvzh_rg in mvzh_rgs:
        filtered = df[df["projektcode"] == int(mvzh_rg.mitglied_nr.replace("MV0", ""))]
        for index, row in filtered.iterrows():
            frappe.db.sql("""UPDATE `tabSales Invoice` SET `docstatus` = 0 WHERE `name` = '{sinv}'""".format(sinv=mvzh_rg.sinv), as_list=True)
            frappe.db.sql("""SET SQL_SAFE_UPDATES = 0;""")
            frappe.db.sql("""DELETE FROM `tabGL Entry` WHERE `voucher_no` = '{0}'""".format(mvzh_rg.sinv))
            frappe.db.sql("""SET SQL_SAFE_UPDATES = 1;""")
            frappe.db.commit()

            sinv = frappe.get_doc("Sales Invoice", mvzh_rg.sinv)
            sinv.esr_reference = row["vESRReferenzNr_MG"]
            sinv.mvzh_sinv_nr = row["faktnr_MG"]
            sinv.mvzh_sinv_iban = row["iban_MG"]

            if sinv.total != str(row["betrag_mg"]).replace(" 00", ""):
                for item in sinv.items:
                    if item.rate > 0:
                        item.rate = int(str(row["betrag_mg"]).replace(" 00", ""))
            
            sinv.outstanding_amount = 0
            
            sinv.save()
            sinv.reload()
            sinv.submit()
            frappe.db.commit()

            if mvzh_rg.fakrg:
                frappe.db.sql("""UPDATE `tabFakultative Rechnung` SET `qrr_referenz` = '{0}', `mvzh_sinv_nr` = '{1}', `mvzh_sinv_iban` = '{2}' WHERE `name` = '{3}'""".format(
                    row["vESRReferenzNr_HP"],
                    row["faktnr_HP"],
                    row["iban_HP"],
                    mvzh_rg.fakrg
                ))
                frappe.db.commit()