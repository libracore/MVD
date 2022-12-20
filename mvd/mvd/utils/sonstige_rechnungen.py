# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from mvd.mvd.utils.qrr_reference import get_qrr_reference
from frappe.utils.data import add_days, getdate, now, today
from PyPDF2 import PdfFileWriter
from frappe.utils.pdf import get_file_data_from_writer
from erpnext.controllers.accounts_controller import get_default_taxes_and_charges

@frappe.whitelist()
def create_rechnung_sonstiges(sektion, rechnungs_artikel, mitgliedschaft=False, kunde=False, druckvorlage=False, bezahlt=False, submit=False, attach_as_pdf=False, mv_mitgliedschaft=None, ohne_betrag=False, ignore_pricing_rule=False):
    if druckvorlage:
        sektion = frappe.get_doc("Druckvorlage", druckvorlage).sektion_id
    sektion = frappe.get_doc("Sektion", sektion)
    company = frappe.get_doc("Company", sektion.company)
    
    if mitgliedschaft:
        # mitgliedschafts basierend
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
        if not mitgliedschaft.rg_kunde:
            customer = mitgliedschaft.kunde_mitglied
            contact = mitgliedschaft.kontakt_mitglied
            if not mitgliedschaft.rg_adresse:
                address = mitgliedschaft.adresse_mitglied
            else:
                address = mitgliedschaft.rg_adresse
        else:
            customer = mitgliedschaft.rg_kunde
            address = mitgliedschaft.rg_adresse
            contact = mitgliedschaft.rg_kontakt
    elif kunde:
        # kunden basierend
        kunde = frappe.get_doc("Kunden", kunde)
        if not kunde.rg_kunde:
            customer = kunde.kunde_kunde
            contact = kunde.kontakt_kunde
            if not kunde.rg_adresse:
                address = kunde.adresse_kunde
            else:
                address = kunde.rg_adresse
        else:
            customer = kunde.rg_kunde
            address = kunde.rg_adresse
            contact = kunde.rg_kontakt
    else:
        frappe.throw("Mitgliedschaft oder Kunde fehlt!")
    
    rechnungs_artikel = json.loads(rechnungs_artikel)
    for item in rechnungs_artikel:
        del item['__islocal']
        #item['qty'] = 1
        item['cost_center'] = company.cost_center
    item = rechnungs_artikel
    
    sinv = frappe.get_doc({
        "doctype": "Sales Invoice",
        "ist_sonstige_rechnung": 1,
        "mv_mitgliedschaft": mitgliedschaft.name if mitgliedschaft else mv_mitgliedschaft if mv_mitgliedschaft else None,
        "mv_kunde": kunde.name if kunde else None,
        "company": sektion.company,
        "cost_center": company.cost_center,
        "customer": customer,
        "customer_address": address,
        "contact_person": contact,
        'due_date': add_days(today(), 30),
        'debit_to': company.default_receivable_account,
        'sektions_code': str(sektion.sektion_id) or '00',
        'sektion_id': sektion.name,
        "items": item,
        "druckvorlage": druckvorlage if druckvorlage else '',
        "ohne_betrag": 1 if ohne_betrag else 0,
        'ignore_pricing_rule': 0 if not ignore_pricing_rule else 1
    })
    sinv.insert(ignore_permissions=True)
    sinv.esr_reference = get_qrr_reference(sales_invoice=sinv.name)
    sales_taxes_and_charges = get_sales_taxes_and_charges_template(sektion.company)
    sinv.taxes_and_charges = sales_taxes_and_charges['taxes_and_charges']
    for tax in sales_taxes_and_charges['taxes']:
        row = sinv.append('taxes', tax)
    
    sinv.save(ignore_permissions=True)
    
    if bezahlt:
        pos_profile = frappe.get_doc("POS Profile", sektion.pos_barzahlung)
        sinv.is_pos = 1
        sinv.pos_profile = pos_profile.name
        row = sinv.append('payments', {})
        row.mode_of_payment = pos_profile.payments[0].mode_of_payment
        row.account = pos_profile.payments[0].account
        row.type = pos_profile.payments[0].type
        row.amount = sinv.grand_total
        sinv.save(ignore_permissions=True)
    
    if submit:
        # submit workaround weil submit ignore_permissions=True nicht kennt
        sinv.docstatus = 1
        sinv.save(ignore_permissions=True)
    
    if attach_as_pdf:
        # add doc signature to allow print
        frappe.form_dict.key = sinv.get_signature()
        
        # erstellung Rechnungs PDF
        output = PdfFileWriter()
        output = frappe.get_print("Sales Invoice", sinv.name, 'Automatisierte Mitgliedschaftsrechnung', as_pdf = True, output = output, ignore_zugferd=True)
        
        file_name = "{sinv}_{datetime}".format(sinv=sinv.name, datetime=now().replace(" ", "_"))
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
            "attached_to_doctype": 'Mitgliedschaft' if mitgliedschaft else 'Kunden',
            "attached_to_name": mitgliedschaft.name if mitgliedschaft else kunde.name
        })
        
        _file.save(ignore_permissions=True)
    
    return sinv.name

def get_sales_taxes_and_charges_template(company):
    sales_taxes_and_charges = get_default_taxes_and_charges(master_doctype='Sales Taxes and Charges Template', company=company)
    return sales_taxes_and_charges
