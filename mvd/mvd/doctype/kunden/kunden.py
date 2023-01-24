# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, scrub
from frappe.model.document import Document
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import nowdate, flt, now
import json
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import create_mitgliedschaftsrechnung, create_abl

class Kunden(Document):
    def onload(self):
        if self.rg_kunde or self.kunde_kunde:
            self.load_dashboard_info()

    def load_dashboard_info(self):
        party = self.rg_kunde if self.rg_kunde else self.kunde_kunde
        info = get_dashboard_info(party)
        self.set_onload('dashboard_info', info)
    
    def validate(self):
        if self.kunde_kunde:
            self.update_kunde()
        else:
            self.create_kunde()
        
        if self.adresse_kunde:
            self.update_adresse()
        else:
            self.create_adresse()
        
        if self.kontakt_kunde:
            self.update_kontakt()
        else:
            self.create_kontakt()
        
        if int(self.abweichende_rechnungsadresse) == 1:
            if int(self.unabhaengiger_debitor) == 1:
                if self.rg_kunde:
                    self.update_rg_kunde()
                else:
                    self.create_rg_kunde()
                
                if self.rg_kontakt:
                    self.update_rg_kontakt()
                else:
                    self.create_rg_kontakt()
            
            if self.rg_adresse:
                self.update_rg_adresse()
            else:
                self.create_rg_adresse()
    
    def create_kunde(self):
        if self.kundentyp == 'Unternehmen':
            customer_name = self.firma
            customer_addition = self.zusatz_firma
            customer_type = 'Company'
        else:
            if self.vorname:
                customer_name = (" ").join((self.vorname, self.nachname))
            else:
                customer_name = self.nachname
            customer_addition = ''
            customer_type = 'Individual'
            
        new_customer = frappe.get_doc({
            'doctype': 'Customer',
            'customer_name': customer_name,
            'customer_addition': customer_addition,
            'customer_type': customer_type,
            'sektion': self.sektion_id,
            'customer_group': 'All Customer Groups' if not self.mv_mitgliedschaft else 'Mitglied',
            'territory': 'All Territories'
        })
        
        new_customer.insert(ignore_permissions=True)
        frappe.db.commit()
        self.kunde_kunde = new_customer.name
    
    def update_kunde(self):
        customer = frappe.get_doc("Customer", self.kunde_kunde)
        if self.kundentyp == 'Unternehmen':
            customer.customer_name = self.firma
            customer.customer_addition = self.zusatz_firma
            customer.customer_type = 'Company'
        else:
            if self.vorname:
                customer.customer_name = (" ").join((self.vorname, self.nachname))
            else:
                customer.customer_name = self.nachname
            customer.customer_addition = ''
            customer.customer_type = 'Individual'
        customer.sektion = self.sektion_id
        
        if self.mv_mitgliedschaft:
            customer.customer_group = 'Mitglied'
        else:
            customer.customer_group = 'All Customer Groups'
        
        customer.save(ignore_permissions=True)
    
    def create_kontakt(self):
        sektion = self.sektion_id
        is_primary_contact = 1
        if self.kundentyp == 'Unternehmen':
            salutation = ''
            company_name = self.firma
            if not self.nachname and not self.vorname:
                first_name = company_name
                last_name = ''
            else:
                company_name = ''
                salutation = self.anrede
                first_name = self.vorname or self.nachname
                if first_name != self.nachname:
                    last_name = self.nachname
                else:
                    last_name = ''
        else:
            company_name = ''
            salutation = self.anrede
            first_name = self.vorname or self.nachname
            if first_name != self.nachname:
                last_name = self.nachname
            else:
                last_name = ''
        
        new_contact = frappe.get_doc({
            'doctype': 'Contact',
            'first_name': first_name,
            'last_name': last_name,
            'salutation': salutation,
            'sektion': sektion,
            'company_name': company_name,
            'is_primary_contact': is_primary_contact
        })
        
        link = new_contact.append("links", {})
        link.link_doctype = 'Customer'
        link.link_name = self.kunde_kunde
        
        # email
        email_id = self.e_mail
        if email_id:
            email_row = new_contact.append("email_ids", {})
            email_row.email_id = email_id
            email_row.is_primary = 1
            
        # private phone
        is_primary_phone = self.tel_p
        if is_primary_phone:
            is_primary_phone_row = new_contact.append("phone_nos", {})
            is_primary_phone_row.phone = is_primary_phone
            is_primary_phone_row.is_primary_phone = 1
            
        # mobile phone
        is_primary_mobile_no = self.tel_m
        if is_primary_mobile_no:
            is_primary_mobile_no_row = new_contact.append("phone_nos", {})
            is_primary_mobile_no_row.phone = is_primary_mobile_no
            is_primary_mobile_no_row.is_primary_mobile_no = 1
            
        # other (company) phone
        phone = self.tel_g
        if phone:
            phone_row = new_contact.append("phone_nos", {})
            phone_row.phone = phone
        
        new_contact.insert(ignore_permissions=True)
        frappe.db.commit()
        
        self.kontakt_kunde = new_contact.name
    
    def update_kontakt(self):
        contact = frappe.get_doc("Contact", self.kontakt_kunde)
        sektion = self.sektion_id
        is_primary_contact = 1
        if self.kundentyp == 'Unternehmen':
            salutation = ''
            company_name = self.firma
            if not self.nachname and not self.vorname:
                first_name = company_name
                last_name = ''
            else:
                company_name = ''
                salutation = self.anrede
                first_name = self.vorname or self.nachname
                if first_name != self.nachname:
                    last_name = self.nachname
                else:
                    last_name = ''
        else:
            company_name = ''
            salutation = self.anrede
            first_name = self.vorname or self.nachname
            if first_name != self.nachname:
                last_name = self.nachname
            else:
                last_name = ''
        
        # company fallback
        if not first_name:
            if self.firma and not self.nachname and not self.vorname:
                first_name = self.firma
        
        contact.first_name = first_name
        contact.last_name = last_name
        contact.salutation = salutation
        contact.sektion = sektion
        contact.company_name = company_name
        contact.is_primary_contact = is_primary_contact
        
        contact.links = []
        link = contact.append("links", {})
        link.link_doctype = 'Customer'
        link.link_name = self.kunde_kunde
        
        # email
        contact.email_ids = []
        email_id = self.e_mail
        if email_id:
            email_row = contact.append("email_ids", {})
            email_row.email_id = email_id
            email_row.is_primary = 1
            
        contact.phone_nos = []
        contact.phone = ''
        contact.mobile_no = ''
        # private phone
        is_primary_phone = self.tel_p
        if is_primary_phone:
            is_primary_phone_row = contact.append("phone_nos", {})
            is_primary_phone_row.phone = is_primary_phone
            is_primary_phone_row.is_primary_phone = 1
            
        # mobile phone
        is_primary_mobile_no = self.tel_m
        if is_primary_mobile_no:
            is_primary_mobile_no_row = contact.append("phone_nos", {})
            is_primary_mobile_no_row.phone = is_primary_mobile_no
            is_primary_mobile_no_row.is_primary_mobile_no = 1
            
        # other (company) phone
        phone = self.tel_g
        if phone:
            phone_row = contact.append("phone_nos", {})
            phone_row.phone = phone
        
        contact.save(ignore_permissions=True)
    
    def create_adresse(self):
        if self.postfach == 1:
            strasse = address_line1 = 'Postfach'
            postfach = 1
        else:
            strasse = address_line1 = (" ").join((str(self.strasse or ''), str(self.nummer or ''), str(self.nummer_zu or '')))
            postfach = 0
        
        is_primary_address = 1
        is_shipping_address = 1
        address_title = self.name
        address_line2 = self.zusatz_adresse
        sektion = self.sektion_id
        plz = self.plz
        postfach_nummer = self.postfach_nummer
        city = self.ort
        country = self.land or 'Schweiz'
        
        new_address = frappe.get_doc({
            'doctype': 'Address',
            'address_title': address_title,
            'address_line1': address_line1,
            'address_line2': address_line2,
            'zusatz': address_line2,
            'strasse': strasse,
            'sektion': sektion,
            'pincode': plz,
            'plz': plz,
            'postfach': postfach,
            'postfach_nummer': postfach_nummer,
            'city': city,
            'country': country,
            'is_primary_address': is_primary_address,
            'is_shipping_address': is_shipping_address
        })
        
        link = new_address.append("links", {})
        link.link_doctype = 'Customer'
        link.link_name = self.kunde_kunde
        
        new_address.insert(ignore_permissions=True)
        frappe.db.commit()
        
        self.adresse_kunde = new_address.name
    
    def update_adresse(self):
        address = frappe.get_doc("Address", self.adresse_kunde)
        if self.postfach == 1:
            strasse = address_line1 = 'Postfach'
            postfach = 1
        else:
            strasse = address_line1 = (" ").join((str(self.strasse or ''), str(self.nummer or ''), str(self.nummer_zu or '')))
            postfach = 0
        
        is_primary_address = 1
        is_shipping_address = 1
        address_title = self.name
        address_line2 = self.zusatz_adresse
        sektion = self.sektion_id
        plz = self.plz
        postfach_nummer = self.postfach_nummer
        city = self.ort
        country = self.land or 'Schweiz'
        
        address.address_title = address_title
        address.address_line1 = address_line1
        address.address_line2 = address_line2
        address.zusatz = address_line2
        address.strasse = strasse
        address.sektion = sektion
        address.pincode = plz
        address.plz = plz
        address.postfach = postfach
        address.postfach_nummer = postfach_nummer
        address.city = city
        address.country = country
        address.is_primary_address = is_primary_address
        address.is_shipping_address = is_shipping_address
        
        address.links = []
        link = address.append("links", {})
        link.link_doctype = 'Customer'
        link.link_name = self.kunde_kunde
        address.save(ignore_permissions=True)
    
    def create_rg_kunde(self):
        if self.rg_kundentyp == 'Unternehmen':
            customer_name = self.rg_firma
            customer_addition = self.rg_zusatz_firma
            customer_type = 'Company'
        else:
            if self.rg_vorname:
                customer_name = (" ").join((self.rg_vorname, self.rg_nachname))
            else:
                customer_name = self.rg_nachname
            customer_addition = ''
            customer_type = 'Individual'
            
        new_customer = frappe.get_doc({
            'doctype': 'Customer',
            'customer_name': customer_name,
            'customer_addition': customer_addition,
            'customer_type': customer_type,
            'sektion': self.sektion_id,
            'customer_group': 'All Customer Groups',
            'territory': 'All Territories'
        })
        
        new_customer.insert(ignore_permissions=True)
        frappe.db.commit()
        self.rg_kunde = new_customer.name
    
    def update_rg_kunde(self):
        customer = frappe.get_doc("Customer", self.rg_kunde)
        if self.rg_kundentyp == 'Unternehmen':
            customer.customer_name = self.rg_firma
            customer.customer_addition = self.rg_zusatz_firma
            customer.customer_type = 'Company'
        else:
            if self.rg_vorname:
                customer.customer_name = (" ").join((self.rg_vorname, self.rg_nachname))
            else:
                customer.customer_name = self.rg_nachname
            customer.customer_addition = ''
            customer.customer_type = 'Individual'
        customer.sektion = self.sektion_id
        
        customer.save(ignore_permissions=True)
    
    def create_rg_kontakt(self):
        sektion = self.sektion_id
        is_primary_contact = 1
        if self.rg_kundentyp == 'Unternehmen':
            salutation = ''
            company_name = self.rg_firma
            if not self.rg_nachname and not self.rg_vorname:
                first_name = company_name
                last_name = ''
            else:
                company_name = ''
                salutation = self.rg_anrede
                first_name = self.rg_vorname or self.rg_nachname
                if first_name != self.rg_nachname:
                    last_name = self.rg_nachname
                else:
                    last_name = ''
        else:
            company_name = ''
            salutation = self.rg_anrede
            first_name = self.rg_vorname or self.rg_nachname
            if first_name != self.rg_nachname:
                last_name = self.rg_nachname
            else:
                last_name = ''
        
        new_contact = frappe.get_doc({
            'doctype': 'Contact',
            'first_name': first_name,
            'last_name': last_name,
            'salutation': salutation,
            'sektion': sektion,
            'company_name': company_name,
            'is_primary_contact': is_primary_contact
        })
        
        link = new_contact.append("links", {})
        link.link_doctype = 'Customer'
        if int(self.unabhaengiger_debitor) == 1:
            link.link_name = self.rg_kunde
        else:
            ink.link_name = self.kunde_kunde
        
        # email
        email_id = self.rg_e_mail
        if email_id:
            email_row = new_contact.append("email_ids", {})
            email_row.email_id = email_id
            email_row.is_primary = 1
            
        # private phone
        is_primary_phone = self.rg_tel_p
        if is_primary_phone:
            is_primary_phone_row = new_contact.append("phone_nos", {})
            is_primary_phone_row.phone = is_primary_phone
            is_primary_phone_row.is_primary_phone = 1
            
        # mobile phone
        is_primary_mobile_no = self.rg_tel_m
        if is_primary_mobile_no:
            is_primary_mobile_no_row = new_contact.append("phone_nos", {})
            is_primary_mobile_no_row.phone = is_primary_mobile_no
            is_primary_mobile_no_row.is_primary_mobile_no = 1
            
        # other (company) phone
        phone = self.rg_tel_g
        if phone:
            phone_row = new_contact.append("phone_nos", {})
            phone_row.phone = phone
        
        new_contact.insert(ignore_permissions=True)
        frappe.db.commit()
        
        self.rg_kontakt = new_contact.name
    
    def update_rg_kontakt(self):
        contact = frappe.get_doc("Contact", self.rg_kontakt)
        sektion = self.sektion_id
        is_primary_contact = 1
        if self.rg_kundentyp == 'Unternehmen':
            salutation = ''
            company_name = self.rg_firma
            if not self.rg_nachname and not self.rg_vorname:
                first_name = company_name
                last_name = ''
            else:
                company_name = ''
                salutation = self.rg_anrede
                first_name = self.rg_vorname or self.rg_nachname
                if first_name != self.rg_nachname:
                    last_name = self.rg_nachname
                else:
                    last_name = ''
        else:
            company_name = ''
            salutation = self.rg_anrede
            first_name = self.rg_vorname or self.rg_nachname
            if first_name != self.rg_nachname:
                last_name = self.rg_nachname
            else:
                last_name = ''
        
        # company fallback
        if not first_name:
            if self.rg_firma and not self.rg_nachname and not self.rg_vorname:
                first_name = self.rg_firma
        
        contact.first_name = first_name
        contact.last_name = last_name
        contact.salutation = salutation
        contact.sektion = sektion
        contact.company_name = company_name
        contact.is_primary_contact = is_primary_contact
        
        contact.links = []
        link = contact.append("links", {})
        link.link_doctype = 'Customer'
        if int(self.unabhaengiger_debitor) == 1:
            link.link_name = self.rg_kunde
        else:
            link.link_name = self.kunde_kunde
        
        # email
        contact.email_ids = []
        email_id = self.rg_e_mail
        if email_id:
            email_row = contact.append("email_ids", {})
            email_row.email_id = email_id
            email_row.is_primary = 1
            
        contact.phone_nos = []
        contact.phone = ''
        contact.mobile_no = ''
        # private phone
        is_primary_phone = self.rg_tel_p
        if is_primary_phone:
            is_primary_phone_row = contact.append("phone_nos", {})
            is_primary_phone_row.phone = is_primary_phone
            is_primary_phone_row.is_primary_phone = 1
            
        # mobile phone
        is_primary_mobile_no = self.rg_tel_m
        if is_primary_mobile_no:
            is_primary_mobile_no_row = contact.append("phone_nos", {})
            is_primary_mobile_no_row.phone = is_primary_mobile_no
            is_primary_mobile_no_row.is_primary_mobile_no = 1
            
        # other (company) phone
        phone = self.rg_tel_g
        if phone:
            phone_row = contact.append("phone_nos", {})
            phone_row.phone = phone
        
        contact.save(ignore_permissions=True)
    
    def create_rg_adresse(self):
        if self.rg_postfach == 1:
            strasse = address_line1 = 'Postfach'
            postfach = 1
        else:
            strasse = address_line1 = (" ").join((str(self.rg_strasse or ''), str(self.rg_nummer or ''), str(self.rg_nummer_zu or '')))
            postfach = 0
        
        is_primary_address = 1
        is_shipping_address = 1
        address_title = self.name + '-RG'
        address_line2 = self.rg_zusatz_adresse
        sektion = self.sektion_id
        plz = self.rg_plz
        postfach_nummer = self.rg_postfach_nummer
        city = self.rg_ort
        country = self.rg_land or 'Schweiz'
        
        new_address = frappe.get_doc({
            'doctype': 'Address',
            'address_title': address_title,
            'address_line1': address_line1,
            'address_line2': address_line2,
            'zusatz': address_line2,
            'strasse': strasse,
            'sektion': sektion,
            'pincode': plz,
            'plz': plz,
            'postfach': postfach,
            'postfach_nummer': postfach_nummer,
            'city': city,
            'country': country,
            'is_primary_address': is_primary_address,
            'is_shipping_address': is_shipping_address
        })
        
        link = new_address.append("links", {})
        link.link_doctype = 'Customer'
        if int(self.unabhaengiger_debitor) == 1:
            link.link_name = self.rg_kunde
        else:
            link.link_name = self.kunde_kunde
        
        new_address.insert(ignore_permissions=True)
        frappe.db.commit()
        
        self.rg_adresse = new_address.name
    
    def update_rg_adresse(self):
        address = frappe.get_doc("Address", self.rg_adresse)
        if self.rg_postfach == 1:
            strasse = address_line1 = 'Postfach'
            postfach = 1
        else:
            strasse = address_line1 = (" ").join((str(self.rg_strasse or ''), str(self.rg_nummer or ''), str(self.rg_nummer_zu or '')))
            postfach = 0
        
        is_primary_address = 1
        is_shipping_address = 1
        address_title = self.name + '-RG'
        address_line2 = self.rg_zusatz_adresse
        sektion = self.sektion_id
        plz = self.rg_plz
        postfach_nummer = self.rg_postfach_nummer
        city = self.rg_ort
        country = self.rg_land or 'Schweiz'
        
        address.address_title = address_title
        address.address_line1 = address_line1
        address.address_line2 = address_line2
        address.zusatz = address_line2
        address.strasse = strasse
        address.sektion = sektion
        address.pincode = plz
        address.plz = plz
        address.postfach = postfach
        address.postfach_nummer = postfach_nummer
        address.city = city
        address.country = country
        address.is_primary_address = is_primary_address
        address.is_shipping_address = is_shipping_address
        
        address.links = []
        link = address.append("links", {})
        link.link_doctype = 'Customer'
        if int(self.unabhaengiger_debitor) == 1:
            link.link_name = self.rg_kunde
        else:
            link.link_name = self.kunde_kunde
        address.save(ignore_permissions=True)

def get_dashboard_info(party):
    current_fiscal_year = get_fiscal_year(nowdate(), as_dict=True)
    party_type = "Customer"
    doctype = "Sales Invoice"

    companies = frappe.get_all(doctype, filters={
        'docstatus': 1,
        party_type.lower(): party
    }, distinct=1, fields=['company'])

    company_wise_info = []

    company_wise_grand_total = frappe.get_all(doctype,
        filters={
            'docstatus': 1,
            party_type.lower(): party,
            'posting_date': ('between', [current_fiscal_year.year_start_date, current_fiscal_year.year_end_date])
            },
            group_by="company",
            fields=["company", "sum(grand_total) as grand_total", "sum(base_grand_total) as base_grand_total"]
        )

    company_wise_billing_this_year = frappe._dict()

    for d in company_wise_grand_total:
        company_wise_billing_this_year.setdefault(
            d.company,{
                "grand_total": d.grand_total,
                "base_grand_total": d.base_grand_total
            })


    company_wise_total_unpaid = frappe._dict(frappe.db.sql("""
        select company, sum(debit_in_account_currency) - sum(credit_in_account_currency)
        from `tabGL Entry`
        where party_type = %s and party=%s
        group by company""", (party_type, party)))

    for d in companies:
        company_default_currency = frappe.db.get_value("Company", d.company, 'default_currency')
        party_account_currency = get_party_account_currency(party_type, party, d.company)

        if party_account_currency==company_default_currency:
            billing_this_year = flt(company_wise_billing_this_year.get(d.company,{}).get("base_grand_total"))
        else:
            billing_this_year = flt(company_wise_billing_this_year.get(d.company,{}).get("grand_total"))

        total_unpaid = flt(company_wise_total_unpaid.get(d.company))

        info = {}
        info["billing_this_year"] = flt(billing_this_year) if billing_this_year else 0
        info["currency"] = party_account_currency
        info["total_unpaid"] = flt(total_unpaid) if total_unpaid else 0
        info["company"] = d.company

        company_wise_info.append(info)

    return company_wise_info

def get_party_account_currency(party_type, party, company):
    def generator():
        party_account = get_party_account(party_type, party, company)
        return frappe.db.get_value("Account", party_account, "account_currency", cache=True)

    return frappe.local_cache("party_account_currency", (party_type, party, company), generator)

@frappe.whitelist()
def get_party_account(party_type, party, company):
    """Returns the account for the given `party`.
        Will first search in party (Customer / Supplier) record, if not found,
        will search in group (Customer Group / Supplier Group),
        finally will return default."""
    if not company:
        frappe.throw(_("Please select a Company"))

    if not party:
        return

    account = frappe.db.get_value("Party Account",
        {"parenttype": party_type, "parent": party, "company": company}, "account")

    if not account and party_type in ['Customer', 'Supplier']:
        party_group_doctype = "Customer Group" if party_type=="Customer" else "Supplier Group"
        group = frappe.get_cached_value(party_type, party, scrub(party_group_doctype))
        account = frappe.db.get_value("Party Account",
            {"parenttype": party_group_doctype, "parent": group, "company": company}, "account")

    if not account and party_type in ['Customer', 'Supplier']:
        default_account_name = "default_receivable_account" \
            if party_type=="Customer" else "default_payable_account"
        account = frappe.get_cached_value('Company',  company,  default_account_name)

    existing_gle_currency = get_party_gle_currency(party_type, party, company)
    if existing_gle_currency:
        if account:
            account_currency = frappe.db.get_value("Account", account, "account_currency", cache=True)
        if (account and account_currency != existing_gle_currency) or not account:
                account = get_party_gle_account(party_type, party, company)

    return account

def get_party_gle_currency(party_type, party, company):
    def generator():
        existing_gle_currency = frappe.db.sql("""select account_currency from `tabGL Entry`
            where docstatus=1 and company=%(company)s and party_type=%(party_type)s and party=%(party)s
            limit 1""", { "company": company, "party_type": party_type, "party": party })

        return existing_gle_currency[0][0] if existing_gle_currency else None

    return frappe.local_cache("party_gle_currency", (party_type, party, company), generator,
        regenerate_if_none=True)

@frappe.whitelist()
def anlage_prozess(anlage_daten, status):
    if isinstance(anlage_daten, str):
        anlage_daten = json.loads(anlage_daten)
    
    firma = ''
    if 'firma' in anlage_daten:
        firma = anlage_daten["firma"] if anlage_daten["firma"] else ''
    zusatz_firma = ''
    if 'zusatz_firma' in anlage_daten:
        zusatz_firma = anlage_daten["zusatz_firma"] if anlage_daten["zusatz_firma"] else ''
    
    eintritt = None
    if status == 'Regulär':
        eintritt = now()
    
    # erstelle mitgliedschaft
    mitgliedschaft = frappe.get_doc({
        "doctype": "Mitgliedschaft",
        "sektion_id": anlage_daten["sektion_id"],
        "status_c": status,
        "language": anlage_daten["language"],
        "m_und_w": 1,
        "mitgliedtyp_c": 'Privat',
        "inkl_hv": 1,
        "eintrittsdatum": eintritt,
        "kundentyp": anlage_daten["kundentyp"],
        "firma": firma,
        "zusatz_firma": zusatz_firma,
        "anrede_c": anlage_daten["anrede"] if 'anrede' in anlage_daten else '',
        "nachname_1": anlage_daten["nachname"],
        "vorname_1": anlage_daten["vorname"],
        "tel_p_1": anlage_daten["tel_p"] if 'tel_p' in anlage_daten else '',
        "tel_m_1": anlage_daten["tel_m"] if 'tel_m' in anlage_daten else '',
        "tel_g_1": anlage_daten["tel_g"] if 'tel_g' in anlage_daten else '',
        "e_mail_1": anlage_daten["e_mail"] if 'e_mail' in anlage_daten else '',
        "zusatz_adresse": anlage_daten["zusatz_adresse"] if 'zusatz_adresse' in anlage_daten else '',
        "strasse": anlage_daten["strasse"] if 'strasse' in anlage_daten else '',
        "nummer": anlage_daten["nummer"] if 'nummer' in anlage_daten else '',
        "nummer_zu": anlage_daten["nummer_zu"] if 'nummer_zu' in anlage_daten else '',
        "postfach": anlage_daten["postfach"],
        "postfach_nummer": anlage_daten["postfach_nummer"] if 'postfach_nummer' in anlage_daten else '',
        "plz": anlage_daten["plz"],
        "ort": anlage_daten["ort"],
        "objekt_strasse": anlage_daten["strasse"] if int(anlage_daten["postfach"]) == 1 else '',
        "objekt_plz": anlage_daten["plz"] if int(anlage_daten["postfach"]) == 1 else '',
        "objekt_ort": anlage_daten["ort"] if int(anlage_daten["postfach"]) == 1 else '',
        "abweichende_objektadresse": 1 if int(anlage_daten["postfach"]) == 1 else '0',
        "kunde_mitglied": anlage_daten["kunde_kunde"],
        "kontakt_mitglied": anlage_daten["kontakt_kunde"],
        "adresse_mitglied": anlage_daten["adresse_kunde"],
        "rg_kunde": anlage_daten["rg_kunde"] if "rg_kunde" in anlage_daten else None,
        "rg_kontakt": anlage_daten["rg_kontakt"] if "rg_kontakt" in anlage_daten else None,
        "rg_adresse": anlage_daten["rg_adresse"] if "rg_adresse" in anlage_daten else None,
        "abweichende_rechnungsadresse": anlage_daten["abweichende_rechnungsadresse"],
        "unabhaengiger_debitor": anlage_daten["unabhaengiger_debitor"],
        "rg_zusatz_adresse": anlage_daten["rg_zusatz_adresse"] if "rg_zusatz_adresse" in anlage_daten else None,
        "rg_strasse": anlage_daten["rg_strasse"] if "rg_strasse" in anlage_daten else None,
        "rg_nummer": anlage_daten["rg_nummer"] if "rg_nummer" in anlage_daten else None,
        "rg_nummer_zu": anlage_daten["rg_nummer_zu"] if "rg_nummer_zu" in anlage_daten else None,
        "rg_postfach": anlage_daten["rg_postfach"] if "rg_postfach" in anlage_daten else None,
        "rg_postfach_nummer": anlage_daten["rg_postfach_nummer"] if "rg_postfach_nummer" in anlage_daten else None,
        "rg_plz": anlage_daten["rg_plz"] if "rg_plz" in anlage_daten else None,
        "rg_ort": anlage_daten["rg_ort"] if "rg_ort" in anlage_daten else None,
        "rg_land": anlage_daten["rg_land"] if "rg_land" in anlage_daten else None,
        "rg_kundentyp": anlage_daten["rg_kundentyp"] if "rg_kundentyp" in anlage_daten else None,
        "rg_firma": anlage_daten["rg_firma"] if "rg_firma" in anlage_daten else None,
        "rg_zusatz_firma": anlage_daten["rg_zusatz_firma"] if "rg_zusatz_firma" in anlage_daten else None,
        "rg_anrede": anlage_daten["rg_anrede"] if "rg_anrede" in anlage_daten else None,
        "rg_nachname": anlage_daten["rg_nachname"] if "rg_nachname" in anlage_daten else None,
        "rg_vorname": anlage_daten["rg_vorname"] if "rg_vorname" in anlage_daten else None,
        "rg_tel_p": anlage_daten["rg_tel_p"] if "rg_tel_p" in anlage_daten else None,
        "rg_tel_m": anlage_daten["rg_tel_m"] if "rg_tel_m" in anlage_daten else None,
        "rg_tel_g": anlage_daten["rg_tel_g"] if "rg_tel_g" in anlage_daten else None,
        "rg_e_mail": anlage_daten["rg_e_mail"] if "rg_e_mail" in anlage_daten else None
    })
    mitgliedschaft.insert(ignore_permissions=True)
    
    if status == 'Regulär':
        bezahlt = True
        hv_bar_bezahlt = False
        sinv = create_mitgliedschaftsrechnung(mitgliedschaft=mitgliedschaft.name, bezahlt=bezahlt, submit=True, attach_as_pdf=True, hv_bar_bezahlt=hv_bar_bezahlt, druckvorlage='', massendruck=False)
    elif status == 'Interessent*in':
        # erstelle ABL für Interessent*Innenbrief mit EZ
        create_abl("Interessent*Innenbrief mit EZ", mitgliedschaft)
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
        mitgliedschaft.interessent_innenbrief_mit_ez = 1
        mitgliedschaft.save()
    elif status == 'Anmeldung':
        # erstelle ABL für Anmeldung mit EZ
        create_abl("Anmeldung mit EZ", mitgliedschaft)
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
        mitgliedschaft.anmeldung_mit_ez = 1
        mitgliedschaft.save()
    
    verknuepfe_kunde_mitglied(anlage_daten['name'], mitgliedschaft.name)
    add_comment_to_kunde(anlage_daten['name'], mitgliedschaft)
    
    return mitgliedschaft.name

def verknuepfe_kunde_mitglied(kunde, mitgliedschaft):
    safe_mode_off = frappe.db.sql("""SET SQL_SAFE_UPDATES=0""", as_list=True)
    sales_invoice = frappe.db.sql("""UPDATE `tabSales Invoice` SET `mv_mitgliedschaft` = '{mitgliedschaft}' WHERE `mv_kunde` = '{kunde}'""".format(mitgliedschaft=mitgliedschaft, kunde=kunde), as_list=True)
    payment_entry = frappe.db.sql("""UPDATE `tabPayment Entry` SET `mv_mitgliedschaft` = '{mitgliedschaft}' WHERE `mv_kunde` = '{kunde}'""".format(mitgliedschaft=mitgliedschaft, kunde=kunde), as_list=True)
    safe_mode_on = frappe.db.sql("""SET SQL_SAFE_UPDATES=1""", as_list=True)

def add_comment_to_kunde(kunde, mitgliedschaft):
    kunde = frappe.get_doc("Kunden", kunde)
    kunde.add_comment('Comment', text="Umgewandelt in Mitgliedschaft <a href='/desk#Form/Mitgliedschaft/{mitgliedschaft}'>{mitglied_nr} ({mitgliedschaft})</a>".format(mitglied_nr=mitgliedschaft.mitglied_nr, mitgliedschaft=mitgliedschaft.name))

@frappe.whitelist()
def update_faktura_kunde(mitgliedschaft=None, kunde=None):
    faktura_kunde = frappe.get_doc('Kunden', kunde)
    if not mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", faktura_kunde.mv_mitgliedschaft)
    faktura_kunde.language = mitgliedschaft.language
    faktura_kunde.kundentyp = mitgliedschaft.kundentyp
    faktura_kunde.anrede = mitgliedschaft.anrede_c
    faktura_kunde.vorname = mitgliedschaft.vorname_1
    faktura_kunde.nachname = mitgliedschaft.nachname_1
    faktura_kunde.tel_p = mitgliedschaft.tel_p_1
    faktura_kunde.tel_m = mitgliedschaft.tel_m_1
    faktura_kunde.tel_g = mitgliedschaft.tel_g_1
    faktura_kunde.e_mail = mitgliedschaft.e_mail_1
    faktura_kunde.strasse = mitgliedschaft.strasse
    faktura_kunde.zusatz_adresse = mitgliedschaft.zusatz_adresse
    faktura_kunde.nummer = mitgliedschaft.nummer
    faktura_kunde.nummer_zu = mitgliedschaft.nummer_zu
    faktura_kunde.plz = mitgliedschaft.plz
    faktura_kunde.ort = mitgliedschaft.ort
    faktura_kunde.postfach = mitgliedschaft.postfach
    faktura_kunde.land = mitgliedschaft.land
    faktura_kunde.postfach_nummer = mitgliedschaft.postfach_nummer
    faktura_kunde.abweichende_rechnungsadresse = mitgliedschaft.abweichende_rechnungsadresse
    faktura_kunde.rg_zusatz_adresse = mitgliedschaft.rg_zusatz_adresse
    faktura_kunde.rg_strasse = mitgliedschaft.rg_strasse
    faktura_kunde.rg_nummer = mitgliedschaft.rg_nummer
    faktura_kunde.rg_nummer_zu = mitgliedschaft.rg_nummer_zu
    faktura_kunde.rg_postfach = mitgliedschaft.rg_postfach
    faktura_kunde.rg_postfach_nummer = mitgliedschaft.rg_postfach_nummer
    faktura_kunde.rg_plz = mitgliedschaft.rg_plz
    faktura_kunde.rg_ort = mitgliedschaft.rg_ort
    faktura_kunde.rg_land = mitgliedschaft.rg_land
    faktura_kunde.save()
