# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Kunden(Document):
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
