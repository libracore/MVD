# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import re

@frappe.whitelist()
def get_qrr_reference(sales_invoice=None, fr=None, reference_raw='00 00000 00000 00000 00000 0000', fake_sinv=False):
    if sales_invoice or fake_sinv:
        if sales_invoice:
            sinv = frappe.get_doc("Sales Invoice", sales_invoice)
        if fake_sinv:
            sinv = fake_sinv
        reference_raw = '00 00000 '
        if sinv.mv_mitgliedschaft:
            mvm = frappe.get_doc("Mitgliedschaft", sinv.mv_mitgliedschaft)
            if mvm.status_c != 'Interessent*in':
                reference_raw += "{0} {1}".format(mvm.mitglied_nr.replace('MV', '')[:5], mvm.mitglied_nr.replace('MV', '')[5:8])
            else:
                new_customer = sinv.customer.replace("K-", "").rjust(8, "0")
                reference_raw += "{0} {1}".format(new_customer[:5], new_customer[5:8])
        else:
            new_customer = sinv.customer.replace("K-", "").rjust(8, "0")
            reference_raw += "{0} {1}".format(new_customer[:5], new_customer[5:8])
        if fake_sinv:
            new_invoice_nr = re.sub("-[0-9]+", "", fake_sinv.rechnungs_jahresversand.replace("Jahresversand-", "")).rjust(10, "0")
            reference_raw += "0{0} {1} {2}".format(new_invoice_nr[:1], new_invoice_nr[1:6], new_invoice_nr[6:10])
        else:
            new_invoice_nr = re.sub("-[0-9]+", "", sales_invoice.replace("R-", "")).rjust(10, "0")
            reference_raw += "0{0} {1} {2}".format(new_invoice_nr[:1], new_invoice_nr[1:6], new_invoice_nr[6:10])
    
    if fr:
        fr_sinv = frappe.get_doc("Fakultative Rechnung", fr)
        mvm = frappe.get_doc("Mitgliedschaft", fr_sinv.mv_mitgliedschaft)
        if fr_sinv.typ == 'HV':
            reference_raw = '11 00000 '
        elif fr_sinv.typ == 'Spende':
            reference_raw = '12 00000 '
        else:
            reference_raw = '13 00000 '
        if mvm.status_c != 'Interessent*in':
            reference_raw += "{0} {1}".format(mvm.mitglied_nr.replace('MV', '')[:5], mvm.mitglied_nr.replace('MV', '')[5:8])
        else:
            if int(mvm.abweichende_rechnungsadresse) == 1 and int(mvm.unabhaengiger_debitor) == 1:
                customer = mvm.rg_kunde
            else:
                customer = mvm.kunde_mitglied
            new_customer = customer.replace("K-", "").rjust(8, "0")
            reference_raw += "{0} {1}".format(new_customer[:5], new_customer[5:8])
        new_invoice_nr = re.sub("-[0-9]+", "", fr.replace("FR-", "")).rjust(10, "0")
        reference_raw += "0{0} {1} {2}".format(new_invoice_nr[:1], new_invoice_nr[1:6], new_invoice_nr[6:10])
    
    check_digit_matrix = {
        '0': [0, 9, 4, 6, 8, 2, 7, 1, 3, 5, 0],
        '1': [9, 4, 6, 8, 2, 7, 1, 3, 5, 0, 9],
        '2': [4, 6, 8, 2, 7, 1, 3, 5, 0, 9, 8],
        '3': [6, 8, 2, 7, 1, 3, 5, 0, 9, 4, 7],
        '4': [8, 2, 7, 1, 3, 5, 0, 9, 4, 6, 6],
        '5': [2, 7, 1, 3, 5, 0, 9, 4, 6, 8, 5],
        '6': [7, 1, 3, 5, 0, 9, 4, 6, 8, 2, 4],
        '7': [1, 3, 5, 0, 9, 4, 6, 8, 2, 7, 3],
        '8': [3, 5, 0, 9, 4, 6, 8, 2, 7, 1, 2],
        '9': [5, 0, 9, 4, 6, 8, 2, 7, 1, 3, 1]
    }
    
    transfer = 0
    check_digit = 0
    reference_raw = reference_raw.replace(" ", "")
    for digit in reference_raw:
        digit = int(digit)
        transfer = int(check_digit_matrix[str(transfer)][digit])
    
    check_digit = int(check_digit_matrix[str(transfer)][10])
    
    qrr_reference_raw = reference_raw + str(check_digit)
    qrr_reference = qrr_reference_raw[:2] + " " + qrr_reference_raw[2:7] + " " + qrr_reference_raw[7:12] + " " + qrr_reference_raw[12:17] + " " + qrr_reference_raw[17:22] + " " + qrr_reference_raw[22:27]
    return qrr_reference

# hotfix cleanup importierte ESR Referenzen
def cleanup_esr_ref():
    sinvs = frappe.db.sql("""SELECT `name`, `esr_reference` FROM `tabSales Invoice` WHERE `docstatus` = 1 AND `status` = 'Overdue'""", as_dict=True)
    total = len(sinvs)
    count = 1
    for sinv in sinvs:
        old_esr = sinv.esr_reference
        new_esr = old_esr[11:27]
        new_esr = '00000000000' + new_esr
        frappe.db.sql("""UPDATE `tabSales Invoice` SET `esr_reference` = '{new_esr}' WHERE `name` = '{name}'""".format(new_esr=new_esr, name=sinv.name), as_list=True)
        frappe.db.commit()
        print("{count} of {total}".format(count=count, total=total))
        count += 1
