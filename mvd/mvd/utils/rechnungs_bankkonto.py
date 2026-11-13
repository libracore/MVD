# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def get_rechnungs_bankkonto(company, bankkonto=None):
    """
        Prüft das übergebene Bankkonto oder lädt das Unternehmens-Default-Bankkonto.
        Returniert das korrekte Bankkonto oder eine Fehlermeldung.
    """
    if not company:
        frappe.throw("Bitte wählen Sie ein Unternehmen für das Rechnungs-Bankkonto.")
    
    if not bankkonto:
        bankkonto = frappe.get_cached_value("Company", company, "default_bank_account")
    
    if not bankkonto:
        frappe.throw("Bitte wählen Sie ein Rechnungs-Bankkonto oder hinterlegen Sie ein Standard-Bankkonto im Unternehmen {0}.".format(company))
    
    account = frappe.get_cached_doc("Account", bankkonto)
    if account.company != company or account.account_type != "Bank" or account.is_group or account.disabled:
        frappe.throw("Das Rechnungs-Bankkonto {0} muss ein aktives Bankkonto des Unternehmens {1} sein.".format(bankkonto, company))
    
    return bankkonto

@frappe.whitelist()
def get_bankkonto_vorgabe(sektion=None, company=None, druckvorlage=None, mit_bankkonten=0):
    if druckvorlage:
        vorlage = frappe.get_doc("Druckvorlage", druckvorlage)
        vorlage.check_permission("read")
        sektion = vorlage.sektion_id
    
    if sektion:
        sektion_doc = frappe.get_doc("Sektion", sektion)
        sektion_doc.check_permission("read")
        company = sektion_doc.company
    elif company:
        frappe.get_doc("Company", company).check_permission("read")
    
    vorgabe = {
        "company": company,
        "rechnungs_bankkonto": frappe.get_cached_value("Company", company, "default_bank_account") if company else None
    }

    if int(mit_bankkonten or 0):
        # Zwei Treffer reichen aus, um zu prüfen ob mehrere Bankkonten zur Auswahl stehen...
        bankkonten = frappe.get_list("Account",
            fields=["name"],
            filters={
                "company": company,
                "account_type": "Bank",
                "is_group": 0,
                "disabled": 0
            },
            limit_page_length=2) if company else []
        
        vorgabe["einziges_bankkonto"] = bankkonten[0].name if len(bankkonten) == 1 else None
    
    return vorgabe

def set_rechnungs_bankkonto(doc, method=None):
    doc.rechnungs_bankkonto = get_rechnungs_bankkonto(doc.company, doc.get("rechnungs_bankkonto"))

def validate_rechnungs_bankkonto(doc, method=None):
    if doc.docstatus in (0, 1) and doc.get("rechnungs_bankkonto"):
        get_rechnungs_bankkonto(doc.company, doc.rechnungs_bankkonto)

def set_lauf_bankkonto(doc):
    company = frappe.get_cached_value("Sektion", doc.sektion_id, "company")
    doc.rechnungs_bankkonto = get_rechnungs_bankkonto(company, doc.get("rechnungs_bankkonto"))
