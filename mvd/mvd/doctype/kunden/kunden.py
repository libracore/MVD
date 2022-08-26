# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, scrub
from frappe.model.document import Document
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import nowdate, flt

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
            'customer_group': 'All Customer Groups',
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
