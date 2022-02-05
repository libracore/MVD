# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from mvd.mvd.utils.qrr_reference import get_qrr_reference
from frappe.utils.data import add_days, today, getdate, now
from PyPDF2 import PdfFileWriter
from frappe.utils.pdf import get_file_data_from_writer

class FakultativeRechnung(Document):
    def before_submit(self):
        self.qrr_referenz = get_qrr_reference(fr=self.name)

@frappe.whitelist()
def create_hv_fr(mitgliedschaft, sales_invoice=None, bezahlt=False, betrag_spende=False, druckvorlage='', asap_print=False):
    if not betrag_spende:
        cancel_old_hv_fr(mitgliedschaft)
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    sektion = frappe.get_doc("Sektion", mitgliedschaft.sektion_id)
    fr = frappe.get_doc({
        "doctype": "Fakultative Rechnung",
        "mv_mitgliedschaft": mitgliedschaft.name,
        'due_date': add_days(today(), 30),
        'sektion_id': str(sektion.name),
        'sektions_code': str(sektion.sektion_id) or '00',
        'sales_invoice': sales_invoice,
        'typ': 'HV' if not betrag_spende else 'Spende',
        'betrag': betrag_spende or sektion.betrag_hv,
        'posting_date': today(),
        'company': sektion.company,
        'druckvorlage': druckvorlage
    })
    fr.insert(ignore_permissions=True)
    
    if bezahlt:
        fr.status = 'Paid'
        fr.bezahlt_via = create_paid_sinv(fr, mitgliedschaft, sektion)
        fr.save(ignore_permissions=True)
    
    fr.submit()
    
    if betrag_spende or asap_print:
        # erstellung Rechnungs PDF auf Basis FR
        output = PdfFileWriter()
        output = frappe.get_print("Fakultative Rechnung", fr.name, "Fakultative Rechnung", as_pdf = True, output = output, ignore_zugferd=True)
        
        file_name = "{sinv}_{datetime}".format(sinv=fr.name, datetime=now().replace(" ", "_"))
        file_name = file_name.split(".")[0]
        file_name = file_name.replace(":", "-")
        file_name = file_name + ".pdf"
        
        filedata = get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home/Attachments",
            "is_private": 1,
            "content": filedata,
            "attached_to_doctype": 'Mitgliedschaft',
            "attached_to_name": mitgliedschaft.name
        })
        
        _file.save(ignore_permissions=True)
        
    return fr.name

def cancel_old_hv_fr(mitgliedschaft):
    old_hvs = frappe.db.sql("""SELECT `name` FROM `tabFakultative Rechnung` WHERE
                                `docstatus` = 1
                                AND `mv_mitgliedschaft` = '{mitgliedschaft}'
                                AND `typ` = 'HV'
                                AND `status` = 'Unpaid'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)
    for old_hv in old_hvs:
        old_hv = frappe.get_doc("Fakultative Rechnung", old_hv.name)
        old_hv.cancel()
        return

def create_paid_sinv(fr, mitgliedschaft, sektion):
    company = frappe.get_doc("Company", sektion.company)
    if not mitgliedschaft.rg_kunde:
        customer = mitgliedschaft.kunde_mitglied
        contact = mitgliedschaft.kontakt_mitglied
        if not mitgliedschaft.rg_adresse:
            address = mitgliedschaft.adresse_mitglied
        else:
            address = mitgliedschaft.rg_adresse
    else:
        customer = mitgliedschaft.rg_kunde_mitglied
        address = mitgliedschaft.rg_adresse_mitglied
        contact = mitgliedschaft.rg_kontakt_mitglied
    if fr.typ == 'HV':
        item = [{"item_code": sektion.hv_artikel, "qty": 1, "rate": sektion.betrag_hv}]
    else:
        # TBD!!!!!!
        item = [{"item_code": sektion.spenden_artikel, "qty": 1, "rate": fr.betrag}]
    sinv = frappe.get_doc({
        "doctype": "Sales Invoice",
        "ist_mitgliedschaftsrechnung": 0,
        "ist_hv_rechnung": 1 if fr.typ == 'HV' else 0,
        "ist_spenden_rechnung": 0 if fr.typ == 'HV' else 1,
        "mv_mitgliedschaft": fr.mv_mitgliedschaft,
        "company": sektion.company,
        "cost_center": company.cost_center,
        "customer": customer,
        "customer_address": address,
        "contact_person": contact,
        'mitgliedschafts_jahr': int(getdate(today()).strftime("%Y")),
        'due_date': add_days(today(), 30),
        'debit_to': company.default_receivable_account,
        'sektions_code': str(sektion.sektion_id) or '00',
        "items": item,
        "inkl_hv": 0,
        "esr_reference": fr.qrr_referenz or get_qrr_reference(fr=fr.name)
    })
    sinv.insert(ignore_permissions=True)
    
    pos_profile = frappe.get_doc("POS Profile", sektion.pos_barzahlung)
    sinv.is_pos = 1
    sinv.pos_profile = pos_profile.name
    row = sinv.append('payments', {})
    row.mode_of_payment = pos_profile.payments[0].mode_of_payment
    row.account = pos_profile.payments[0].account
    row.type = pos_profile.payments[0].type
    row.amount = sinv.grand_total
    sinv.save(ignore_permissions=True)
    
    sinv.submit()
    return sinv.name

def create_unpaid_sinv(fr, betrag=False):
    fr = frappe.get_doc("Fakultative Rechnung", fr)
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", fr.mv_mitgliedschaft)
    sektion = frappe.get_doc("Sektion", mitgliedschaft.sektion_id)
    company = frappe.get_doc("Company", sektion.company)
    if not mitgliedschaft.rg_kunde:
        customer = mitgliedschaft.kunde_mitglied
        contact = mitgliedschaft.kontakt_mitglied
        if not mitgliedschaft.rg_adresse:
            address = mitgliedschaft.adresse_mitglied
        else:
            address = mitgliedschaft.rg_adresse
    else:
        customer = mitgliedschaft.rg_kunde_mitglied
        address = mitgliedschaft.rg_adresse_mitglied
        contact = mitgliedschaft.rg_kontakt_mitglied
    
    if fr.typ == 'HV':
        betrag = sektion.betrag_hv
        item = [{"item_code": sektion.hv_artikel, "qty": 1, "rate": betrag}]
    else:
        if not betrag:
            # tbd!!!
            betrag = sektion.betrag_hv
        item = [{"item_code": sektion.spenden_artikel, "qty": 1, "rate": betrag}]
    sinv = frappe.get_doc({
        "doctype": "Sales Invoice",
        "ist_mitgliedschaftsrechnung": 0,
        "ist_hv_rechnung": 1 if fr.typ == 'HV' else 0,
        "ist_spenden_rechnung": 0 if fr.typ == 'HV' else 1,
        "mv_mitgliedschaft": fr.mv_mitgliedschaft,
        "company": sektion.company,
        "cost_center": company.cost_center,
        "customer": customer,
        "customer_address": address,
        "contact_person": contact,
        'mitgliedschafts_jahr': int(getdate(today()).strftime("%Y")),
        'due_date': add_days(today(), 30),
        'debit_to': company.default_receivable_account,
        'sektions_code': str(sektion.sektion_id) or '00',
        "items": item,
        "inkl_hv": 0,
        "esr_reference": fr.qrr_referenz or get_qrr_reference(fr=fr.name)
    })
    sinv.insert(ignore_permissions=True)
    
    sinv.submit()
    
    fr.status = 'Paid'
    fr.bezahlt_via = sinv.name
    fr.save(ignore_permissions=True)
    return sinv.name
