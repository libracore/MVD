# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import add_days, getdate, now
from mvd.mvd.utils.qrr_reference import get_qrr_reference
import json
from PyPDF2 import PdfFileWriter
from mvd.mvd.doctype.arbeits_backlog.arbeits_backlog import create_abl

class MVMitgliedschaft(Document):
    def set_new_name(self):
        if not self.mitglied_nr:
            # Mitglied Nr
            self.mitglied_nr = str(get_mitgliedid(self))
        
        if not self.mitglied_id:
            # Mitglied ID
            self.mitglied_id = str(get_mitgliedid(self))
    
    def validate(self):
        if not self.validierung_notwendig:
            # Mitglied
            self.kunde_mitglied = self.validate_kunde_mitglied()
            self.kontakt_mitglied = self.validate_kontakt_mitglied(primary=True)
            self.adresse_mitglied, self.objekt_adresse = self.validate_adresse_mitglied()
            join_mitglied_contact_and_address(self.kontakt_mitglied, self.adresse_mitglied)
            
            # Solidarmitglied
            if self.hat_solidarmitglied:
                self.kontakt_solidarmitglied = self.validate_kontakt_mitglied(primary=False)
                if self.objekt_adresse:
                    join_mitglied_contact_and_address(self.kontakt_solidarmitglied, self.objekt_adresse)
                else:
                    join_mitglied_contact_and_address(self.kontakt_solidarmitglied, self.adresse_mitglied)
            else:
                if self.kontakt_solidarmitglied:
                    self.kontakt_solidarmitglied = self.remove_solidarmitglied()

            # Rechnungsempfaenger
            if self.abweichende_rechnungsadresse:
                if self.unabhaengiger_debitor:
                    self.rg_kunde = self.validate_rg_kunde()
                    self.rg_kontakt = self.validate_rg_kontakt()
                else:
                    self.rg_kunde = ''
                    self.rg_kontakt = ''
                self.rg_adresse = self.validate_rg_adresse()
            else:
                self.rg_kunde = ''
                self.rg_kontakt = ''
                self.rg_adresse = ''
            
            # Briefanrede
            self.briefanrede = get_anredekonvention(self=self)
            
            # Adressblock
            self.adressblock = get_adressblock(self)
        
    def validate_rg_kunde(self):
        if self.rg_kunde:
            update_rg_kunde(self)
            return self.rg_kunde
        else:
            customer = create_rg_kunde(self)
            return customer
    
    def validate_rg_kontakt(self):
        if self.rg_kontakt:
            update_rg_kontakt(self)
            return self.rg_kontakt
        else:
            contact = create_rg_kontakt(self)
            return contact
    
    def validate_rg_adresse(self):
        if self.rg_adresse:
            rg_adresse = update_rg_adresse(self)
            return rg_adresse
        else:
            address = create_rg_adresse(self)
            return address

    def validate_kunde_mitglied(self):
        if self.kunde_mitglied:
            update_kunde_mitglied(self)
            return self.kunde_mitglied
        else:
            customer = create_kunde_mitglied(self)
            return customer
    
    def validate_kontakt_mitglied(self, primary):
        if primary:
            if self.kontakt_mitglied:
                update_kontakt_mitglied(self, primary)
                return self.kontakt_mitglied
            else:
                contact = create_kontakt_mitglied(self, primary)
                return contact
        else:
            if self.kontakt_solidarmitglied:
                update_kontakt_mitglied(self, primary)
                return self.kontakt_solidarmitglied
            else:
                contact = create_kontakt_mitglied(self, primary)
                return contact
    
    def validate_adresse_mitglied(self):
        if self.adresse_mitglied:
            adresse_mitglied = update_adresse_mitglied(self)
            if self.postfach or self.abweichende_objektadresse:
                if self.objekt_adresse:
                    objekt_adresse = update_objekt_adresse(self)
                    return adresse_mitglied, objekt_adresse
                else:
                    objekt_adresse = create_objekt_adresse(self)
                    return adresse_mitglied, objekt_adresse
            else:
                if self.objekt_adresse:
                    self.remove_objekt_adresse()
                return adresse_mitglied, ''
        else:
            address = create_adresse_mitglied(self)
            if self.postfach or self.abweichende_objektadresse:
                if self.objekt_adresse:
                    objekt_adresse = update_objekt_adresse(self)
                    return address, objekt_adresse
                else:
                    objekt_adresse = create_objekt_adresse(self)
                    return address, objekt_adresse
            else:
                if self.objekt_adresse:
                    self.remove_objekt_adresse()
                return address, ''
    
    def remove_objekt_adresse(self):
        if self.kontakt_solidarmitglied:
            join_mitglied_contact_and_address(self.kontakt_solidarmitglied, '')
        address = frappe.get_doc("Address", self.objekt_adresse)
        address.disabled = 1
        address.links = []
        address.save(ignore_permissions=True)
        return
    
    def remove_solidarmitglied(self):
        contact = frappe.get_doc("Contact", self.kontakt_solidarmitglied)
        contact.links = []
        contact.save(ignore_permissions=True)
        return ''

def get_mitgliedid(mitgliedschaft):
    # zum testen, nachher via API!
    anz_mitgliedschaften = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabMV Mitgliedschaft`""", as_dict=True)[0].qty
    anz_mitgliedschaften += 1
    return anz_mitgliedschaften
    
def get_adressblock(mitgliedschaft):
    adressblock = ''
    if mitgliedschaft.kundentyp == 'Unternehmen':
        adressblock += mitgliedschaft.firma or ''
        adressblock += mitgliedschaft.zusatz_firma or ''
        adressblock += '\n'
    
    if mitgliedschaft.vorname_1:
        adressblock += mitgliedschaft.vorname_1 or ''
        adressblock += ' '
    adressblock += mitgliedschaft.nachname_1 or ''
    adressblock += '\n'
    
    if mitgliedschaft.hat_solidarmitglied:
        if mitgliedschaft.vorname_2:
            adressblock += mitgliedschaft.vorname_2 or ''
            adressblock += ' '
        if mitgliedschaft.nachname_2:
            adressblock += mitgliedschaft.nachname_2 or ''
        if  mitgliedschaft.vorname_2 or mitgliedschaft.nachname_2:
            adressblock += '\n'
    
    if mitgliedschaft.zusatz_adresse:
        adressblock += mitgliedschaft.zusatz_adresse or ''
        adressblock += '\n'
    
    adressblock += mitgliedschaft.strasse or ''
    if mitgliedschaft.nummer:
        adressblock += ' '
        adressblock += str(mitgliedschaft.nummer) or ''
        if mitgliedschaft.nummer_zu:
            adressblock += str(mitgliedschaft.nummer_zu) or ''
    adressblock += '\n'
    
    if mitgliedschaft.postfach:
        adressblock += 'Postfach '
        adressblock += str(mitgliedschaft.postfach_nummer) or ''
        adressblock += '\n'
    
    adressblock += str(mitgliedschaft.plz) or ''
    adressblock += ' '
    adressblock += mitgliedschaft.ort or ''
    
    return adressblock
    
def update_rg_adresse(mitgliedschaft):
    address = frappe.get_doc("Address", mitgliedschaft.rg_adresse)
    if mitgliedschaft.rg_postfach:
        strasse = address_line1 = 'Postfach'
        postfach = 1
    else:
        strasse = address_line1 = (" ").join((str(mitgliedschaft.rg_strasse or ''), str(mitgliedschaft.rg_nummer or ''), str(mitgliedschaft.rg_nummer_zu or '')))
        postfach = 0
    
    is_primary_address = 0
    is_shipping_address = 0
    address_title = mitgliedschaft.mitglied_id
    address_line2 = mitgliedschaft.rg_zusatz_adresse
    sektion = mitgliedschaft.sektion_id
    plz = mitgliedschaft.rg_plz
    postfach_nummer = mitgliedschaft.rg_postfach_nummer
    city = mitgliedschaft.rg_ort
    
    address.address_title = address_title
    address.address_line1 = address_line1
    address.address_line2 = address_line2
    address.strasse = strasse
    address.sektion = sektion
    address.pincode = plz
    address.plz = plz
    address.postfach = postfach
    address.postfach_nummer = postfach_nummer
    address.city = city
    address.is_primary_address = is_primary_address
    address.is_shipping_address = is_shipping_address
    address.adress_id = mitgliedschaft.adress_id_rg
    
    if mitgliedschaft.rg_kunde:
        link_name = mitgliedschaft.rg_kunde
    else:
        link_name = mitgliedschaft.kunde_mitglied
    
    address.links = []
    link = address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = link_name
    address.save(ignore_permissions=True)
    
    return address.name

def create_rg_adresse(mitgliedschaft):
    if mitgliedschaft.adress_id_rg:
        existierende_adresse = existierende_adresse_anhand_id(mitgliedschaft.adress_id_rg)
        if existierende_adresse:
            mitgliedschaft.rg_adresse = existierende_adresse
            return update_rg_adresse(mitgliedschaft)
    
    if mitgliedschaft.rg_postfach:
        strasse = address_line1 = 'Postfach'
        postfach = 1
    else:
        strasse = address_line1 = (" ").join((str(mitgliedschaft.rg_strasse or ''), str(mitgliedschaft.rg_nummer or ''), str(mitgliedschaft.rg_nummer_zu or '')))
        postfach = 0
    
    is_primary_address = 0
    is_shipping_address = 0
    address_title = mitgliedschaft.mitglied_id
    address_line2 = mitgliedschaft.rg_zusatz_adresse
    sektion = mitgliedschaft.sektion_id
    plz = mitgliedschaft.rg_plz
    postfach_nummer = mitgliedschaft.rg_postfach_nummer
    city = mitgliedschaft.rg_ort
    
    new_address = frappe.get_doc({
        'doctype': 'Address',
        'address_title': address_title,
        'address_line1': address_line1,
        'address_line2': address_line2,
        'strasse': strasse,
        'sektion': sektion,
        'pincode': plz,
        'plz': plz,
        'postfach': postfach,
        'postfach_nummer': postfach_nummer,
        'city': city,
        'is_primary_address': is_primary_address,
        'is_shipping_address': is_shipping_address,
        'adress_id': mitgliedschaft.adress_id_rg
    })
    
    if mitgliedschaft.rg_kunde:
        link_name = mitgliedschaft.rg_kunde
    else:
        link_name = mitgliedschaft.kunde_mitglied
    
    link = new_address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = link_name
    
    new_address.insert()
    frappe.db.commit()
    
    return new_address.name

def update_rg_kontakt(mitgliedschaft):
    contact = frappe.get_doc("Contact", mitgliedschaft.rg_kontakt)
    sektion = mitgliedschaft.sektion_id
    if mitgliedschaft.rg_kunde:
        is_primary_contact = 1
        link_name = mitgliedschaft.rg_kunde
    else:
        is_primary_contact = 0
        link_name = mitgliedschaft.kunde_mitglied
    
    if mitgliedschaft.rg_kundentyp == 'Unternehmen':
        salutation = ''
        company_name = mitgliedschaft.rg_firma
        if not mitgliedschaft.rg_nachname and not mitgliedschaft.rg_vorname:
            first_name = company_name
        else:
            company_name = ''
            salutation = mitgliedschaft.rg_anrede
            first_name = mitgliedschaft.rg_vorname or mitgliedschaft.rg_nachname
            if first_name != mitgliedschaft.rg_nachname:
                last_name = mitgliedschaft.rg_nachname
            else:
                last_name = ''
    else:
        company_name = ''
        salutation = mitgliedschaft.rg_anrede
        first_name = mitgliedschaft.rg_vorname or mitgliedschaft.rg_nachname
        if first_name != mitgliedschaft.rg_nachname:
            last_name = mitgliedschaft.rg_nachname
        else:
            last_name = ''
    
    contact.first_name = first_name
    contact.last_name = last_name
    contact.salutation = salutation
    contact.sektion = sektion
    contact.company_name = company_name
    contact.is_primary_contact = is_primary_contact
    
    contact.links = []
    link = contact.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = link_name
    
    # email
    contact.email_ids = []
    email_id = mitgliedschaft.rg_e_mail
    if email_id:
        email_row = contact.append("email_ids", {})
        email_row.email_id = email_id
        email_row.is_primary = 1
        
    contact.phone_nos = []
    # private phone
    is_primary_phone = mitgliedschaft.rg_tel_p
    if is_primary_phone:
        is_primary_phone_row = contact.append("phone_nos", {})
        is_primary_phone_row.phone = is_primary_phone
        is_primary_phone_row.is_primary_phone = 1
        
    # mobile phone
    is_primary_mobile_no = mitgliedschaft.rg_tel_m
    if is_primary_mobile_no:
        is_primary_mobile_no_row = contact.append("phone_nos", {})
        is_primary_mobile_no_row.phone = is_primary_mobile_no
        is_primary_mobile_no_row.is_primary_mobile_no = 1
        
    # other (company) phone
    phone = mitgliedschaft.rg_tel_g
    if phone:
        phone_row = contact.append("phone_nos", {})
        phone_row.phone = phone
    
    contact.save(ignore_permissions=True)
    return

def create_rg_kontakt(mitgliedschaft):
    sektion = mitgliedschaft.sektion_id
    if mitgliedschaft.rg_kunde:
        is_primary_contact = 1
        link_name = mitgliedschaft.rg_kunde
    else:
        is_primary_contact = 0
        link_name = mitgliedschaft.kunde_mitglied
    
    if mitgliedschaft.rg_kundentyp == 'Unternehmen':
        salutation = ''
        company_name = mitgliedschaft.rg_firma
        if not mitgliedschaft.rg_nachname and not mitgliedschaft.rg_vorname:
            first_name = company_name
        else:
            company_name = ''
            salutation = mitgliedschaft.rg_anrede
            first_name = mitgliedschaft.rg_vorname or mitgliedschaft.rg_nachname
            if first_name != mitgliedschaft.rg_nachname:
                last_name = mitgliedschaft.rg_nachname
            else:
                last_name = ''
    else:
        company_name = ''
        salutation = mitgliedschaft.rg_anrede
        first_name = mitgliedschaft.rg_vorname or mitgliedschaft.rg_nachname
        if first_name != mitgliedschaft.rg_nachname:
            last_name = mitgliedschaft.rg_nachname
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
    link.link_name = link_name
    
    # email
    email_id = mitgliedschaft.rg_e_mail
    if email_id:
        email_row = new_contact.append("email_ids", {})
        email_row.email_id = email_id
        email_row.is_primary = 1
        
    # private phone
    is_primary_phone = mitgliedschaft.rg_tel_p
    if is_primary_phone:
        is_primary_phone_row = new_contact.append("phone_nos", {})
        is_primary_phone_row.phone = is_primary_phone
        is_primary_phone_row.is_primary_phone = 1
        
    # mobile phone
    is_primary_mobile_no = mitgliedschaft.rg_tel_m
    if is_primary_mobile_no:
        is_primary_mobile_no_row = new_contact.append("phone_nos", {})
        is_primary_mobile_no_row.phone = is_primary_mobile_no
        is_primary_mobile_no_row.is_primary_mobile_no = 1
        
    # other (company) phone
    phone = mitgliedschaft.rg_tel_g
    if phone:
        phone_row = new_contact.append("phone_nos", {})
        phone_row.phone = phone
    
    try:
        new_contact.insert()
        frappe.db.commit()
    except frappe.DuplicateEntryError:
        frappe.local.message_log = []
        mitgliedschaft.rg_kontakt = new_contact.name
        update_rg_kontakt(mitgliedschaft)
        return new_contact.name
    
    return new_contact.name

def update_rg_kunde(mitgliedschaft):
    customer = frappe.get_doc("Customer", mitgliedschaft.rg_kunde)
    if mitgliedschaft.rg_kundentyp == 'Unternehmen':
        customer.customer_name = mitgliedschaft.rg_firma
        customer.customer_addition = mitgliedschaft.rg_zusatz_firma
        customer.customer_type = 'Company'
    else:
        customer.customer_name = (" ").join((mitgliedschaft.rg_vorname, mitgliedschaft.rg_nachname))
        customer.customer_addition = ''
        customer.customer_type = 'Individual'
    customer.sektion = mitgliedschaft.sektion_id
    customer.save(ignore_permissions=True)
    return

def create_rg_kunde(mitgliedschaft):
    if mitgliedschaft.rg_kundentyp == 'Unternehmen':
        customer_name = mitgliedschaft.rg_firma
        customer_addition = mitgliedschaft.rg_zusatz_firma
        customer_type = 'Company'
    else:
        customer_name = (" ").join((mitgliedschaft.rg_vorname, mitgliedschaft.rg_nachname))
        customer_addition = ''
        customer_type = 'Individual'
    
    new_customer = frappe.get_doc({
        'doctype': 'Customer',
        'customer_name': customer_name,
        'customer_addition': customer_addition,
        'customer_type': customer_type,
        'sektion': mitgliedschaft.sektion_id
    })
    new_customer.insert()
    frappe.db.commit()
    return new_customer.name

def create_objekt_adresse(mitgliedschaft):
    if mitgliedschaft.adress_id_objekt:
        existierende_adresse = existierende_adresse_anhand_id(mitgliedschaft.adress_id_objekt)
        if existierende_adresse:
            mitgliedschaft.objekt_adresse = existierende_adresse
            return update_objekt_adresse(mitgliedschaft)
    
    strasse = address_line1 = (" ").join((str(mitgliedschaft.objekt_strasse or ''), str(mitgliedschaft.objekt_hausnummer or ''), str(mitgliedschaft.objekt_nummer_zu or '')))
    postfach = 0
    is_primary_address = 0
    is_shipping_address = 0
    address_title = ("-").join((mitgliedschaft.mitglied_id, 'Objekt'))
    address_line2 = mitgliedschaft.objekt_zusatz_adresse
    sektion = mitgliedschaft.sektion_id
    plz = mitgliedschaft.objekt_plz
    postfach_nummer = ''
    city = mitgliedschaft.objekt_ort
    
    if not strasse:
        strasse = address_line1 = "Achtung Fehler!"
    if not city:
        city = "Achtung Fehler!"
    
    new_address = frappe.get_doc({
        'doctype': 'Address',
        'address_title': address_title,
        'address_line1': address_line1,
        'address_line2': address_line2,
        'strasse': strasse,
        'sektion': sektion,
        'pincode': plz,
        'plz': plz,
        'postfach': postfach,
        'postfach_nummer': postfach_nummer,
        'city': city,
        'is_primary_address': is_primary_address,
        'is_shipping_address': is_shipping_address,
        'adress_id': mitgliedschaft.adress_id_objekt
    })
    
    link = new_address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied
    
    new_address.insert()
    frappe.db.commit()
    
    return new_address.name

def update_objekt_adresse(mitgliedschaft):
    address = frappe.get_doc("Address", mitgliedschaft.objekt_adresse)
    strasse = address_line1 = (" ").join((str(mitgliedschaft.objekt_strasse or ''), str(mitgliedschaft.objekt_hausnummer or ''), str(mitgliedschaft.objekt_nummer_zu or '')))
    postfach = 0
    is_primary_address = 0
    is_shipping_address = 0
    address_title = ("-").join((mitgliedschaft.mitglied_id, 'Objekt'))
    address_line2 = mitgliedschaft.objekt_zusatz_adresse
    sektion = mitgliedschaft.sektion_id
    plz = mitgliedschaft.objekt_plz
    postfach_nummer = ''
    city = mitgliedschaft.objekt_ort
    
    if not strasse:
        strasse = address_line1 = "Achtung Fehler!"
    if not city:
        city = "Achtung Fehler!"
    
    address.address_title = address_title
    address.address_line1 = address_line1
    address.address_line2 = address_line2
    address.strasse = strasse
    address.sektion = sektion
    address.pincode = plz
    address.plz = plz
    address.postfach = postfach
    address.postfach_nummer = postfach_nummer
    address.city = city
    address.is_primary_address = is_primary_address
    address.is_shipping_address = is_shipping_address
    address.adress_id = mitgliedschaft.adress_id_objekt
    
    address.links = []
    link = address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied
    address.save(ignore_permissions=True)
    
    return address.name

def join_mitglied_contact_and_address(contact, address):
    contact = frappe.get_doc("Contact", contact)
    contact.address = address
    contact.save(ignore_permissions=True)
    
def update_adresse_mitglied(mitgliedschaft):
    address = frappe.get_doc("Address", mitgliedschaft.adresse_mitglied)
    if mitgliedschaft.postfach:
        strasse = address_line1 = 'Postfach'
        postfach = 1
    else:
        strasse = address_line1 = (" ").join((str(mitgliedschaft.strasse or ''), str(mitgliedschaft.nummer or ''), str(mitgliedschaft.nummer_zu or '')))
        postfach = 0
    
    is_primary_address = 1
    is_shipping_address = 1
    address_title = mitgliedschaft.mitglied_id
    address_line2 = mitgliedschaft.zusatz_adresse
    sektion = mitgliedschaft.sektion_id
    plz = mitgliedschaft.plz
    postfach_nummer = mitgliedschaft.postfach_nummer
    city = mitgliedschaft.ort
    
    address.address_title = address_title
    address.address_line1 = address_line1
    address.address_line2 = address_line2
    address.strasse = strasse
    address.sektion = sektion
    address.pincode = plz
    address.plz = plz
    address.postfach = postfach
    address.postfach_nummer = postfach_nummer
    address.city = city
    address.is_primary_address = is_primary_address
    address.is_shipping_address = is_shipping_address
    address.adress_id = mitgliedschaft.adress_id_mitglied
    
    address.links = []
    link = address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied
    address.save(ignore_permissions=True)
    
    return address.name

def create_adresse_mitglied(mitgliedschaft):
    if mitgliedschaft.adress_id_mitglied:
        existierende_adresse = existierende_adresse_anhand_id(mitgliedschaft.adress_id_mitglied)
        if existierende_adresse:
            mitgliedschaft.adresse_mitglied = existierende_adresse
            return update_adresse_mitglied(mitgliedschaft)
    
    if mitgliedschaft.postfach:
        strasse = address_line1 = 'Postfach'
        postfach = 1
    else:
        strasse = address_line1 = (" ").join((str(mitgliedschaft.strasse or ''), str(mitgliedschaft.nummer or ''), str(mitgliedschaft.nummer_zu or '')))
        postfach = 0
    
    is_primary_address = 1
    is_shipping_address = 1
    address_title = mitgliedschaft.mitglied_id
    address_line2 = mitgliedschaft.zusatz_adresse
    sektion = mitgliedschaft.sektion_id
    plz = mitgliedschaft.plz
    postfach_nummer = mitgliedschaft.postfach_nummer
    city = mitgliedschaft.ort
    
    new_address = frappe.get_doc({
        'doctype': 'Address',
        'address_title': address_title,
        'address_line1': address_line1,
        'address_line2': address_line2,
        'strasse': strasse,
        'sektion': sektion,
        'pincode': plz,
        'plz': plz,
        'postfach': postfach,
        'postfach_nummer': postfach_nummer,
        'city': city,
        'is_primary_address': is_primary_address,
        'is_shipping_address': is_shipping_address,
        'adress_id': mitgliedschaft.adress_id_mitglied
    })
    
    link = new_address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied
    
    new_address.insert()
    frappe.db.commit()
    
    return new_address.name

def remove_solidarmitglied(mitgliedschaft):
    return

def update_kontakt_mitglied(mitgliedschaft, primary=True):
    if primary:
        contact = frappe.get_doc("Contact", mitgliedschaft.kontakt_mitglied)
        sektion = mitgliedschaft.sektion_id
        is_primary_contact = 1
        if mitgliedschaft.kundentyp == 'Unternehmen':
            salutation = ''
            company_name = mitgliedschaft.firma
            if not mitgliedschaft.nachname_1 and not mitgliedschaft.vorname_1:
                first_name = company_name
                last_name = ''
            else:
                company_name = ''
                salutation = mitgliedschaft.anrede_c
                first_name = mitgliedschaft.vorname_1 or mitgliedschaft.nachname_1
                if first_name != mitgliedschaft.nachname_1:
                    last_name = mitgliedschaft.nachname_1
                else:
                    last_name = ''
        else:
            company_name = ''
            salutation = mitgliedschaft.anrede_c
            first_name = mitgliedschaft.vorname_1 or mitgliedschaft.nachname_1
            if first_name != mitgliedschaft.nachname_1:
                last_name = mitgliedschaft.nachname_1
            else:
                last_name = ''
    else:
        contact = frappe.get_doc("Contact", mitgliedschaft.kontakt_solidarmitglied)
        sektion = mitgliedschaft.sektion_id
        is_primary_contact = 0
        company_name = ''
        salutation = mitgliedschaft.anrede_2
        first_name = mitgliedschaft.vorname_2 or mitgliedschaft.nachname_2
        if first_name != mitgliedschaft.nachname_2:
            last_name = mitgliedschaft.nachname_2
        else:
            last_name = ''
    
    # company fallback
    if not first_name:
        if mitgliedschaft.firma and not mitgliedschaft.nachname_1 and not mitgliedschaft.vorname_1:
            first_name = mitgliedschaft.firma
            frappe.log_error("{0}\n---\n{1}".format('fallback: first_name was " "', mitgliedschaft.as_json()), 'update_kontakt_mitglied')
    
    contact.first_name = first_name
    contact.last_name = last_name
    contact.salutation = salutation
    contact.sektion = sektion
    contact.company_name = company_name
    contact.is_primary_contact = is_primary_contact
    
    contact.links = []
    link = contact.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied
    
    if primary:
        # email
        contact.email_ids = []
        email_id = mitgliedschaft.e_mail_1
        if email_id:
            email_row = contact.append("email_ids", {})
            email_row.email_id = email_id
            email_row.is_primary = 1
            
        contact.phone_nos = []
        # private phone
        is_primary_phone = mitgliedschaft.tel_p_1
        if is_primary_phone:
            is_primary_phone_row = contact.append("phone_nos", {})
            is_primary_phone_row.phone = is_primary_phone
            is_primary_phone_row.is_primary_phone = 1
            
        # mobile phone
        is_primary_mobile_no = mitgliedschaft.tel_m_1
        if is_primary_mobile_no:
            is_primary_mobile_no_row = contact.append("phone_nos", {})
            is_primary_mobile_no_row.phone = is_primary_mobile_no
            is_primary_mobile_no_row.is_primary_mobile_no = 1
            
        # other (company) phone
        phone = mitgliedschaft.tel_g_1
        if phone:
            phone_row = contact.append("phone_nos", {})
            phone_row.phone = phone
    else:
        # email
        contact.email_ids = []
        email_id = mitgliedschaft.e_mail_2
        if email_id:
            email_row = contact.append("email_ids", {})
            email_row.email_id = email_id
            email_row.is_primary = 1
            
        contact.phone_nos = []
        # private phone
        is_primary_phone = mitgliedschaft.tel_p_2
        if is_primary_phone:
            is_primary_phone_row = contact.append("phone_nos", {})
            is_primary_phone_row.phone = is_primary_phone
            is_primary_phone_row.is_primary_phone = 1
            
        # mobile phone
        is_primary_mobile_no = mitgliedschaft.tel_m_2
        if is_primary_mobile_no:
            is_primary_mobile_no_row = contact.append("phone_nos", {})
            is_primary_mobile_no_row.phone = is_primary_mobile_no
            is_primary_mobile_no_row.is_primary_mobile_no = 1
            
        # other (company) phone
        phone = mitgliedschaft.tel_g_2
        if phone:
            phone_row = contact.append("phone_nos", {})
            phone_row.phone = phone
    
    contact.save(ignore_permissions=True)
    return

def create_kontakt_mitglied(mitgliedschaft, primary=True):
    if primary:
        sektion = mitgliedschaft.sektion_id
        is_primary_contact = 1
        if mitgliedschaft.kundentyp == 'Unternehmen':
            salutation = ''
            company_name = mitgliedschaft.firma
            if not mitgliedschaft.nachname_1 and not mitgliedschaft.vorname_1:
                first_name = company_name
                last_name = ''
            else:
                company_name = ''
                salutation = mitgliedschaft.anrede_c
                first_name = mitgliedschaft.vorname_1 or mitgliedschaft.nachname_1
                if first_name != mitgliedschaft.nachname_1:
                    last_name = mitgliedschaft.nachname_1
                else:
                    last_name = ''
        else:
            company_name = ''
            salutation = mitgliedschaft.anrede_c
            first_name = mitgliedschaft.vorname_1 or mitgliedschaft.nachname_1
            if first_name != mitgliedschaft.nachname_1:
                last_name = mitgliedschaft.nachname_1
            else:
                last_name = ''
    else:
        sektion = mitgliedschaft.sektion_id
        is_primary_contact = 0
        company_name = ''
        salutation = mitgliedschaft.anrede_2
        first_name = mitgliedschaft.vorname_2 or mitgliedschaft.nachname_2
        if first_name != mitgliedschaft.nachname_2:
            last_name = mitgliedschaft.nachname_2
        else:
            last_name = ''
    
    # company fallback
    if not first_name:
        if mitgliedschaft.firma and not mitgliedschaft.nachname_1 and not mitgliedschaft.vorname_1:
            first_name = mitgliedschaft.firma
            frappe.log_error("{0}\n---\n{1}".format('fallback: first_name was " "', mitgliedschaft.as_json()), 'create_kontakt_mitglied')
    
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
    link.link_name = mitgliedschaft.kunde_mitglied
    
    if primary:
        # email
        email_id = mitgliedschaft.e_mail_1
        if email_id:
            email_row = new_contact.append("email_ids", {})
            email_row.email_id = email_id
            email_row.is_primary = 1
            
        # private phone
        is_primary_phone = mitgliedschaft.tel_p_1
        if is_primary_phone:
            is_primary_phone_row = new_contact.append("phone_nos", {})
            is_primary_phone_row.phone = is_primary_phone
            is_primary_phone_row.is_primary_phone = 1
            
        # mobile phone
        is_primary_mobile_no = mitgliedschaft.tel_m_1
        if is_primary_mobile_no:
            is_primary_mobile_no_row = new_contact.append("phone_nos", {})
            is_primary_mobile_no_row.phone = is_primary_mobile_no
            is_primary_mobile_no_row.is_primary_mobile_no = 1
            
        # other (company) phone
        phone = mitgliedschaft.tel_g_1
        if phone:
            phone_row = new_contact.append("phone_nos", {})
            phone_row.phone = phone
    else:
        # email
        email_id = mitgliedschaft.e_mail_2
        if email_id:
            email_row = new_contact.append("email_ids", {})
            email_row.email_id = email_id
            email_row.is_primary = 1
            
        # private phone
        is_primary_phone = mitgliedschaft.tel_p_2
        if is_primary_phone:
            is_primary_phone_row = new_contact.append("phone_nos", {})
            is_primary_phone_row.phone = is_primary_phone
            is_primary_phone_row.is_primary_phone = 1
            
        # mobile phone
        is_primary_mobile_no = mitgliedschaft.tel_m_2
        if is_primary_mobile_no:
            is_primary_mobile_no_row = new_contact.append("phone_nos", {})
            is_primary_mobile_no_row.phone = is_primary_mobile_no
            is_primary_mobile_no_row.is_primary_mobile_no = 1
            
        # other (company) phone
        phone = mitgliedschaft.tel_g_2
        if phone:
            phone_row = new_contact.append("phone_nos", {})
            phone_row.phone = phone
    
    try:
        new_contact.insert()
        frappe.db.commit()
    except frappe.DuplicateEntryError:
        frappe.local.message_log = []
        mitgliedschaft.kontakt_solidarmitglied = new_contact.name
        update_kontakt_mitglied(mitgliedschaft, primary)
        return new_contact.name
    
    return new_contact.name

def update_kunde_mitglied(mitgliedschaft):
    customer = frappe.get_doc("Customer", mitgliedschaft.kunde_mitglied)
    if mitgliedschaft.kundentyp == 'Unternehmen':
        customer.customer_name = mitgliedschaft.firma
        customer.customer_addition = mitgliedschaft.zusatz_firma
        customer.customer_type = 'Company'
    else:
        customer.customer_name = (" ").join((mitgliedschaft.vorname_1, mitgliedschaft.nachname_1))
        customer.customer_addition = ''
        customer.customer_type = 'Individual'
    customer.sektion = mitgliedschaft.sektion_id
    
    # fallback wrong import data
    if customer.customer_name == ' ' and mitgliedschaft.firma:
        customer.customer_name = mitgliedschaft.firma
        customer.customer_addition = mitgliedschaft.zusatz_firma
        customer.customer_type = 'Company'
        frappe.log_error("{0}\n---\n{1}".format('fallback: customer_name was " "', mitgliedschaft.as_json()), 'update_kunde_mitglied')
    
    customer.save(ignore_permissions=True)
    return
    
def create_kunde_mitglied(mitgliedschaft):
    if mitgliedschaft.kundentyp == 'Unternehmen':
        customer_name = mitgliedschaft.firma
        customer_addition = mitgliedschaft.zusatz_firma
        customer_type = 'Company'
    else:
        customer_name = (" ").join((mitgliedschaft.vorname_1, mitgliedschaft.nachname_1))
        customer_addition = ''
        customer_type = 'Individual'
        
    # fallback wrong import data
    if customer_name == ' ' and mitgliedschaft.firma:
        customer_name = mitgliedschaft.firma
        customer_addition = mitgliedschaft.zusatz_firma
        customer_type = 'Company'
        frappe.log_error("{0}\n---\n{1}".format('fallback: customer_name was " "', mitgliedschaft.as_json()), 'create_kunde_mitglied')
    
    new_customer = frappe.get_doc({
        'doctype': 'Customer',
        'customer_name': customer_name,
        'customer_addition': customer_addition,
        'customer_type': customer_type,
        'sektion': mitgliedschaft.sektion_id
    })
    
    new_customer.insert()
    frappe.db.commit()
    return new_customer.name

def existierende_adresse_anhand_id(adress_id):
    address = False
    adress_lookup = frappe.db.sql("""SELECT `name` FROM `tabAddress` WHERE `adress_id` = '{adress_id}' LIMIT 1""".format(adress_id=adress_id), as_dict=True)
    if len(adress_lookup) > 0:
        address = adress_lookup[0].name
    return address

@frappe.whitelist()
def get_timeline_data(doctype, name):
    '''returns timeline data for the past one year'''
    from frappe.desk.form.load import get_communication_data
    from frappe.utils import add_years, now, add_days, getdate, get_timestamp

    
    out = {}
    fields = 'DATE(`creation`) AS `date`, COUNT(`name`) AS `qty`'
    after = add_years(None, -1).strftime('%Y-%m-%d')
    group_by='GROUP BY DATE(`creation`)'

    # fetch and append data from Version Log
    timeline_items = frappe.db.sql("""SELECT {fields}
        FROM `tabVersion`
        WHERE `ref_doctype` = "{doctype}" AND `docname` = "{name}"
        AND `creation` > '{after}'
        {group_by} ORDER BY `creation` DESC
        """.format(doctype=doctype, name=name, fields=fields,
            group_by=group_by, after=after), as_dict=True)

    for timeline_item in timeline_items:
        timestamp = get_timestamp(timeline_item.date)
        out.update({ timestamp: timeline_item.qty })
    return out

@frappe.whitelist()
def get_uebersicht_html(name):
    col_qty = 1
    mitgliedschaft = frappe.get_doc("MV Mitgliedschaft", name)
    
    kunde_mitglied = False
    if mitgliedschaft.kunde_mitglied:
        kunde_mitglied = frappe.get_doc("Customer", mitgliedschaft.kunde_mitglied).as_dict()
    
    kontakt_mitglied = False
    if mitgliedschaft.kontakt_mitglied:
        kontakt_mitglied = frappe.get_doc("Contact", mitgliedschaft.kontakt_mitglied).as_dict()
    
    adresse_mitglied = False
    if mitgliedschaft.adresse_mitglied:
        adresse_mitglied = frappe.get_doc("Address", mitgliedschaft.adresse_mitglied).as_dict()
    
    objekt_adresse = False
    if mitgliedschaft.objekt_adresse:
        objekt_adresse = frappe.get_doc("Address", mitgliedschaft.objekt_adresse).as_dict()
        col_qty += 1
    
    kontakt_solidarmitglied = False
    if mitgliedschaft.kontakt_solidarmitglied:
        kontakt_solidarmitglied = frappe.get_doc("Contact", mitgliedschaft.kontakt_solidarmitglied).as_dict()
        col_qty += 1
    
    rg_kunde = False
    if mitgliedschaft.rg_kunde:
        rg_kunde = frappe.get_doc("Customer", mitgliedschaft.rg_kunde).as_dict()
    
    rg_kontakt = False
    if mitgliedschaft.rg_kontakt:
        rg_kontakt = frappe.get_doc("Contact", mitgliedschaft.rg_kontakt).as_dict()
    
    rg_adresse = False
    if mitgliedschaft.rg_adresse:
        rg_adresse = frappe.get_doc("Address", mitgliedschaft.rg_adresse).as_dict()
    
    rg_sep = False
    if mitgliedschaft.abweichende_rechnungsadresse:
        rg_sep = True
        col_qty += 1
    
    ''' mögliche Ampelfarben:
        - Grün: ampelgruen --> Mitglied kann alle Dienstleistungen beziehen (keine Karenzfristen, keine überfälligen oder offen Rechnungen)
        - Gelb: ampelgelb --> Karenzfristen oder offene Rechnungen
        - Rot: ampelrot --> überfällige offene Rechnungen
    '''
    
    rechnungs_kunde = mitgliedschaft.kunde_mitglied
    ueberfaellige_rechnungen = 0
    offene_rechnungen = 0
    
    sektion = frappe.get_doc("Sektion", mitgliedschaft.sektion_id)
    karenzfrist_in_d = sektion.karenzfrist
    ablauf_karenzfrist = add_days(getdate(mitgliedschaft.eintritt), karenzfrist_in_d)
    if getdate() < ablauf_karenzfrist:
        karenzfrist = False
    else:
        karenzfrist = True
        
    if mitgliedschaft.zuzug:
        zuzug = mitgliedschaft.zuzug
        zuzug_von = mitgliedschaft.zuzug_von
    else:
        zuzug = False
        zuzug_von = False
        
    if mitgliedschaft.wegzug:
        wegzug = mitgliedschaft.wegzug
        wegzug_zu = mitgliedschaft.wegzug_zu
    else:
        wegzug = False
        wegzug_zu = False
    
    if mitgliedschaft.inkl_hv:
        if mitgliedschaft.zahlung_hv:
            hv_status = 'HV bezahlt am {0}'.format(frappe.utils.get_datetime(mitgliedschaft.zahlung_hv).strftime('%d.%m.%Y'))
        else:
            hv_status = 'HV unbezahlt'
    else:
        hv_status = False
    
    if mitgliedschaft.rg_kunde:
        rechnungs_kunde = mitgliedschaft.rg_kunde
    ueberfaellige_rechnungen = frappe.db.sql("""SELECT IFNULL(SUM(`outstanding_amount`), 0) AS `open_amount`
                                                FROM `tabSales Invoice` 
                                                WHERE `customer` = '{rechnungs_kunde}'
                                                AND `due_date` < CURDATE()
                                                AND `docstatus` = 1""".format(rechnungs_kunde=rechnungs_kunde), as_dict=True)[0].open_amount
    
    if ueberfaellige_rechnungen > 0:
        ampelfarbe = 'ampelrot'
    else:
        offene_rechnungen = frappe.db.sql("""SELECT IFNULL(SUM(`outstanding_amount`), 0) AS `open_amount`
                                            FROM `tabSales Invoice` 
                                            WHERE `customer` = '{rechnungs_kunde}'
                                            AND `due_date` >= CURDATE()
                                            AND `docstatus` = 1""".format(rechnungs_kunde=rechnungs_kunde), as_dict=True)[0].open_amount
        
        if offene_rechnungen > 0:
            ampelfarbe = 'ampelgelb'
        else:
            if not karenzfrist:
                ampelfarbe = 'ampelgelb'
            else:
                ampelfarbe = 'ampelgruen'
    
    data = {
        'kunde_mitglied': kunde_mitglied,
        'kontakt_mitglied': kontakt_mitglied,
        'adresse_mitglied': adresse_mitglied,
        'objekt_adresse': objekt_adresse,
        'kontakt_solidarmitglied': kontakt_solidarmitglied,
        'rg_kunde': rg_kunde,
        'rg_kontakt': rg_kontakt,
        'rg_adresse': rg_adresse,
        'rg_sep': rg_sep,
        'col_qty': int(12 / col_qty),
        'allgemein': {
            'status': mitgliedschaft.status_c,
            'eintritt': mitgliedschaft.eintritt,
            'austritt': mitgliedschaft.austritt,
            'ampelfarbe': ampelfarbe,
            'ueberfaellige_rechnungen': ueberfaellige_rechnungen,
            'offene_rechnungen': offene_rechnungen,
            'ablauf_karenzfrist': ablauf_karenzfrist,
            'zuzug': zuzug,
            'wegzug': wegzug,
            'zuzug_von': zuzug_von,
            'wegzug_zu': wegzug_zu,
            'mitgliedtyp_c': mitgliedschaft.mitgliedtyp_c,
            'hv_status': hv_status,
            'wichtig': mitgliedschaft.wichtig
        }
    }
    
    return frappe.render_template('templates/includes/mitgliedschaft_overview.html', data)
    
def get_anredekonvention(mitgliedschaft=None, self=None):
    if self:
        mitgliedschaft = self
    else:
        mitgliedschaft = frappe.get_doc("MV Mitgliedschaft", mitgliedschaft)
    if mitgliedschaft.hat_solidarmitglied:
        # mit Solidarmitglied
        if mitgliedschaft.anrede_c not in ('Herr', 'Frau') and mitgliedschaft.anrede_2 not in ('Herr', 'Frau'):
            # enthält neutrale Anrede
            if mitgliedschaft.nachname_1 == mitgliedschaft.nachname_2 and mitgliedschaft.vorname_1 == mitgliedschaft.vorname_2:
                # gleiche Namen Fallback
                return 'Guten Tag'
            else:
                return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1, nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
        else:
            if mitgliedschaft.anrede_c == mitgliedschaft.anrede_2:
                # selbes Geschlecht
                if mitgliedschaft.nachname_1 == mitgliedschaft.nachname_2:
                    # gleiche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return 'Sehr geehrter Herr {vorname_1} {nachname_1}, sehr geehrter Herr {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1, nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return 'Sehr geehrte Frau {vorname_1} {nachname_1}, sehr geehrte Frau {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1, nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1, nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                else:
                    # unterschiedliche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return 'Sehr geehrter Herr {nachname_1}, sehr geehrter Herr {nachname_2}'.format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return 'Sehr geehrte Frau {nachname_1}, sehr geehrte Frau {nachname_2}'.format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1, nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
            else:
                # unterschiedliches Geschlecht
                if mitgliedschaft.nachname_1 == mitgliedschaft.nachname_2:
                    # gleiche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return 'Sehr geehrte Herr und Frau {nachname_1}'.format(nachname_1=mitgliedschaft.nachname_1)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return 'Sehr geehrte Frau und Herr {nachname_1}'.format(nachname_1=mitgliedschaft.nachname_1)
                    else:
                        # Fallback
                        return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1, nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                else:
                    # unterschiedliche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return 'Sehr geehrter Herr {nachname_1}, sehr geehrte Frau {nachname_2}'.format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return 'Sehr geehrte Frau {nachname_1}, sehr geehrter Herr {nachname_2}'.format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1, nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
        
    else:
        # ohne Solidarmitglied
        if mitgliedschaft.anrede_c == 'Herr':
            return 'Sehr geehrter Herr {nachname}'.format(nachname=mitgliedschaft.nachname_1)
        elif mitgliedschaft.anrede_c == 'Frau':
            return 'Sehr geehrte Frau {nachname}'.format(nachname=mitgliedschaft.nachname_1)
        else:
            return 'Guten Tag {vorname} {nachname}'.format(vorname=mitgliedschaft.vorname_1, nachname=mitgliedschaft.nachname_1)

@frappe.whitelist()
def sektionswechsel(mitgliedschaft, neue_sektion, zuzug_per):
    try:
        mitgliedschaft = frappe.get_doc("MV Mitgliedschaft", mitgliedschaft)
        new_mitgliedschaft = frappe.copy_doc(mitgliedschaft)
        new_mitgliedschaft.mitglied_nr = ''
        new_mitgliedschaft.mitglied_id = ''
        new_mitgliedschaft.zuzug_von = new_mitgliedschaft.sektion_id
        new_mitgliedschaft.sektion_id = neue_sektion
        new_mitgliedschaft.status_c = 'Zuzug'
        new_mitgliedschaft.zuzug = zuzug_per
        new_mitgliedschaft.wegzug = ''
        new_mitgliedschaft.kunde_mitglied = ''
        new_mitgliedschaft.kontakt_mitglied = ''
        new_mitgliedschaft.adresse_mitglied = ''
        new_mitgliedschaft.adress_id_mitglied = ''
        new_mitgliedschaft.kontakt_solidarmitglied = ''
        new_mitgliedschaft.objekt_adresse = ''
        new_mitgliedschaft.adress_id_objekt = ''
        new_mitgliedschaft.rg_kunde = ''
        new_mitgliedschaft.rg_kontakt = ''
        new_mitgliedschaft.rg_adresse = ''
        new_mitgliedschaft.adress_id_rg = ''
        new_mitgliedschaft.insert()
        return 1
    except:
        return 0

@frappe.whitelist()
def create_mitgliedschaftsrechnung(mitgliedschaft):
    mitgliedschaft = frappe.get_doc("MV Mitgliedschaft", mitgliedschaft)
    sektion = frappe.get_doc("Sektion", mitgliedschaft.sektion_id)
    if not mitgliedschaft.rg_kunde:
        customer = mitgliedschaft.kunde_mitglied
        contact = mitgliedschaft.kontakt_mitglied
        if not mitgliedschaft.rg_adresse:
            address = mitgliedschaft.adresse_mitglied
        else:
            address = mitgliedschaft.rg_adresse
    else:
        customer = mitgliedschaft.kunde_mitglied
        address = mitgliedschaft.adresse_mitglied
        contact = mitgliedschaft.kontakt_mitglied
    
    sinv = frappe.get_doc({
        "doctype": "Sales Invoice",
        "ist_mitgliedschaftsrechnung": 1,
        "mv_mitgliedschaft": mitgliedschaft.name,
        "company": sektion.company,
        "customer": customer,
        "customer_address": address,
        "contact_person": contact,
        "items": [
            {
                "item_code": sektion.mitgliedschafts_artikel,
                "qty": 1
            }
        ],
        "inkl_hv": mitgliedschaft.inkl_hv
    })
    sinv.insert()
    #sinv.esr_reference = get_qrr_reference()
    
    return sinv.name

@frappe.whitelist()
def create_korrespondenz_serienbriefe(mitgliedschaften, korrespondenzdaten):
    if isinstance(korrespondenzdaten, str):
        korrespondenzdaten = json.loads(korrespondenzdaten)
    
    if isinstance(mitgliedschaften, str):
        mitgliedschaften = json.loads(mitgliedschaften)
    
    erstellte_korrespondenzen = []
    
    for mitgliedschaft in mitgliedschaften:
        new_korrespondenz = frappe.get_doc({
            "doctype": "MV Korrespondenz",
            "mv_mitgliedschaft": mitgliedschaft['name'],
            "sektion_id": korrespondenzdaten['sektion_id'],
            "check_ansprechperson": korrespondenzdaten['check_ansprechperson'] if 'check_ansprechperson' in korrespondenzdaten else 0,
            "ansprechperson": korrespondenzdaten['ansprechperson'] if 'ansprechperson' in korrespondenzdaten else '',
            "tel_ma": korrespondenzdaten['tel_ma'] if 'tel_ma' in korrespondenzdaten else '',
            "email_ma": korrespondenzdaten['email_ma'] if 'email_ma' in korrespondenzdaten else '',
            "mit_ausweis": korrespondenzdaten['mit_ausweis'] if 'mit_ausweis' in korrespondenzdaten else 0,
            "ort": korrespondenzdaten['ort'],
            "datum": korrespondenzdaten['datum'],
            "brieftitel": korrespondenzdaten['brieftitel'],
            "check_anrede": korrespondenzdaten['check_anrede'] if 'check_anrede' in korrespondenzdaten else 0,
            "anrede": korrespondenzdaten['anrede'] if 'anrede' in korrespondenzdaten else '',
            "inhalt": korrespondenzdaten['inhalt'],
            "inhalt_2": korrespondenzdaten['inhalt_2'] if 'inhalt_2' in korrespondenzdaten else ''
        })
        new_korrespondenz.insert()
        frappe.db.commit()
        erstellte_korrespondenzen.append(new_korrespondenz.name)
    
    return erstellte_korrespondenzen

@frappe.whitelist()
def make_kuendigungs_prozess(mitgliedschaft, datum_kuendigung, massenlauf):
    # erfassung Kündigung
    mitgliedschaft = frappe.get_doc("MV Mitgliedschaft", mitgliedschaft)
    mitgliedschaft.kuendigung = datum_kuendigung
    mitgliedschaft.status_c = 'Kündigung'
    if massenlauf == '1':
        mitgliedschaft.kuendigung_verarbeiten = 1
        create_abl("Kündigung verarbeiten", mitgliedschaft)
    mitgliedschaft.save()
    
    # erstellung Kündigungs PDF
    output = PdfFileWriter()
    output = frappe.get_print("MV Mitgliedschaft", mitgliedschaft.name, 'Kündigungsbestätigung', as_pdf = True, output = output)
    
    pdf = frappe.utils.pdf.get_file_data_from_writer(output)
    file_name = "Kündigungsbestätigung_{mitgliedschaft}_{datetime}.pdf".format(mitgliedschaft=mitgliedschaft.name, datetime=now().replace(" ", "_"))
    
    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "folder": "Home/Attachments",
        "is_private": 1,
        "content": pdf,
        "attached_to_doctype": 'MV Mitgliedschaft',
        "attached_to_name": mitgliedschaft.name
    })
    
    _file.save()
    
    return 'done'

# API (eingehend von Service-Platform)
# -----------------------------------------------

# Neuanlage / Update Mitgliedschaft
def mvm_mitglieder(kwargs):
    if 'MitgliedId' in kwargs:
        if kwargs["MitgliedId"] > 0:
            return check_update_vs_neuanlage(kwargs)
        else:
            return raise_xxx(400, 'Bad Request', 'mitgliedId == 0')
    else:
        return raise_xxx(400, 'Bad Request', 'mitgliedId missing')

# Status Returns
def raise_xxx(code, title, message):
    frappe.log_error("{0}\n{1}\n{2}".format(code, title, message), 'raise_xxx')
    return ['{code} {title}'.format(code=code, title=title), {
        "error": {
            "code": code,
            "message": "{message}".format(message=message)
        }
    }]
    
def raise_200(answer='Success'):
    frappe.log_error("200 Success", '200 Success')
    return ['200 Success', answer]

# API Funktionshelfer
# -----------------------------------------------
def check_update_vs_neuanlage(kwargs):
    if not frappe.db.exists("MV Mitgliedschaft", kwargs["MitgliedId"]):
        return mvm_neuanlage(kwargs)
    else:
        mitgliedschaft = frappe.get_doc("MV Mitgliedschaft", kwargs["MitgliedId"])
        return mvm_update(mitgliedschaft, kwargs)
        

def mvm_update(mitgliedschaft, kwargs):
    missing_keys = check_main_keys(kwargs)
    if not missing_keys:
        try:
            sektion_id = get_sektion_id(kwargs['SektionCode'])
            if not sektion_id:
                return raise_xxx(404, 'Not Found', 'Sektion ({sektion_id}) not found'.format(sektion_id=kwargs['SektionCode']))
                
            status_c = get_status_c(kwargs['Status'])
            if not status_c:
                return raise_xxx(404, 'Not Found', 'MitgliedStatus ({status_c}) not found'.format(status_c=kwargs['Status']))
                
            mitgliedtyp_c = get_mitgliedtyp_c(kwargs['Typ'])
            if not mitgliedtyp_c:
                return raise_xxx(404, 'Not Found', 'typ ({mitgliedtyp_c}) not found'.format(mitgliedtyp_c=kwargs['Typ']))
            
            if kwargs['Eintrittsdatum']:
                eintritt = kwargs['Eintrittsdatum'].split("T")[0]
            else:
                eintritt = ''
            
            if kwargs['Zuzugsdatum']:
                zuzug = kwargs['Zuzugsdatum'].split("T")[0]
            else:
                zuzug = ''
            
            if kwargs['Wegzugsdatum']:
                wegzug = kwargs['Wegzugsdatum'].split("T")[0]
            else:
                wegzug = ''
            
            if kwargs['Austrittsdatum']:
                austritt = kwargs['Austrittsdatum'].split("T")[0]
            else:
                austritt = ''
            
            if kwargs['KuendigungPer']:
                kuendigung = kwargs['KuendigungPer'].split("T")[0]
            else:
                kuendigung = ''
            
            if kwargs['ZeitungAlsPdf']:
                m_und_w_pdf = 1
            else:
                m_und_w_pdf = 0
            
            mitgliedschaft.mitglied_nr = kwargs['MitgliedNummer']
            mitgliedschaft.sektion_id = sektion_id
            mitgliedschaft.status_c = status_c
            mitgliedschaft.mitglied_id = kwargs['MitgliedId']
            mitgliedschaft.mitgliedtyp_c = mitgliedtyp_c
            mitgliedschaft.inkl_hv = get_inkl_hv(kwargs["JahrBezahltHaftpflicht"])
            mitgliedschaft.m_und_w = kwargs['AnzahlZeitungen']
            mitgliedschaft.m_und_w_pdf = m_und_w_pdf
            mitgliedschaft.wichtig = kwargs['Bemerkungen']
            mitgliedschaft.eintritt = eintritt
            mitgliedschaft.zuzug = zuzug
            mitgliedschaft.wegzug = wegzug
            mitgliedschaft.austritt = austritt
            mitgliedschaft.kuendigung = kuendigung
            mitgliedschaft.validierung_notwendig = 1
            mitgliedschaft.save()
            
            mitgliedschaft = adressen_und_kontakt_handling(mitgliedschaft, kwargs)
            if not mitgliedschaft:
                return raise_xxx(500, 'Internal Server Error', 'Bei dem Adressen Update ist etwas schief gelaufen')
            
            mitgliedschaft.validierung_notwendig = 0
            mitgliedschaft.save()
            
            return raise_200()
            
        except Exception as err:
            return raise_xxx(500, 'Internal Server Error', err)
    else:
        return missing_keys

def mvm_neuanlage(kwargs):
    missing_keys = check_main_keys(kwargs)
    if not missing_keys:
        try:
            sektion_id = get_sektion_id(kwargs['SektionCode'])
            if not sektion_id:
                return raise_xxx(404, 'Not Found', 'Sektion ({sektion_id}) not found'.format(sektion_id=kwargs['SektionCode']))
                
            status_c = get_status_c(kwargs['Status'])
            if not status_c:
                return raise_xxx(404, 'Not Found', 'MitgliedStatus ({status_c}) not found'.format(status_c=kwargs['Status']))
                
            mitgliedtyp_c = get_mitgliedtyp_c(kwargs['Typ'])
            if not mitgliedtyp_c:
                return raise_xxx(404, 'Not Found', 'typ ({mitgliedtyp_c}) not found'.format(mitgliedtyp_c=kwargs['Typ']))
            
            if kwargs['Eintrittsdatum']:
                eintritt = kwargs['Eintrittsdatum'].split("T")[0]
            else:
                eintritt = ''
            
            if kwargs['Zuzugsdatum']:
                zuzug = kwargs['Zuzugsdatum'].split("T")[0]
            else:
                zuzug = ''
            
            if kwargs['Wegzugsdatum']:
                wegzug = kwargs['Wegzugsdatum'].split("T")[0]
            else:
                wegzug = ''
            
            if kwargs['Austrittsdatum']:
                austritt = kwargs['Austrittsdatum'].split("T")[0]
            else:
                austritt = ''
            
            if kwargs['KuendigungPer']:
                kuendigung = kwargs['KuendigungPer'].split("T")[0]
            else:
                kuendigung = ''
            
            if kwargs['ZeitungAlsPdf']:
                m_und_w_pdf = 1
            else:
                m_und_w_pdf = 0
            
            new_mitgliedschaft = frappe.get_doc({
                'doctype': 'MV Mitgliedschaft',
                'mitglied_nr': str(kwargs['MitgliedNummer']),
                'sektion_id': sektion_id,
                'status_c': status_c,
                'mitglied_id': str(kwargs['MitgliedId']),
                'mitgliedtyp_c': mitgliedtyp_c,
                'inkl_hv': get_inkl_hv(kwargs["JahrBezahltHaftpflicht"]),
                'm_und_w': kwargs['AnzahlZeitungen'],
                'm_und_w_pdf': m_und_w_pdf,
                'wichtig': kwargs['Bemerkungen'],
                'eintritt': eintritt,
                'zuzug': zuzug,
                'wegzug': wegzug,
                'austritt': austritt,
                #'zuzug_von': kwargs['???'], --> woher erhalte ich diese Info?
                #'wegzug_zu': kwargs['mitgliedNummer'], --> benötige ich bei neumitglieder nicht
                'kuendigung': kuendigung,
                'validierung_notwendig': 1,
                'nachname_1': 'API',
                'plz': 'API',
                'ort': 'API'
            })
            new_mitgliedschaft.insert()
            
            new_mitgliedschaft = adressen_und_kontakt_handling(new_mitgliedschaft, kwargs)
            if not new_mitgliedschaft:
                return raise_xxx(500, 'Internal Server Error', 'Bei der Adressen Anlage ist etwas schief gelaufen')
            
            new_mitgliedschaft.validierung_notwendig = 0
            new_mitgliedschaft.save()
            
            return raise_200()
            
        except Exception as err:
            return raise_xxx(500, 'Internal Server Error', err)
            
    else:
        return missing_keys

def check_main_keys(kwargs):
    mandatory_keys = [
        'MitgliedNummer',
        'MitgliedId',
        'SektionCode',
        'Typ',
        'Status',
        'RegionCode',
        'IstTemporaeresMitglied',
        'FuerBewirtschaftungGesperrt',
        'Erfassungsdatum',
        'Eintrittsdatum',
        'Austrittsdatum',
        'Zuzugsdatum',
        'Wegzugsdatum',
        'KuendigungPer',
        'JahrBezahltMitgliedschaft',
        'JahrBezahltHaftpflicht',
        'NaechstesJahrGeschuldet',
        'Bemerkungen',
        'AnzahlZeitungen',
        'ZeitungAlsPdf',
        'Adressen'
    ]
    for key in mandatory_keys:
        if key not in kwargs:
            return raise_xxx(400, 'Bad Request', '{key} missing'.format(key=key))
    return False

def get_sektion_id(sektion_c):
    sektionen = frappe.db.sql("""SELECT `name` FROM `tabSektion` WHERE `sektion_c` = '{sektion_c}'""".format(sektion_c=sektion_c), as_dict=True)
    if len(sektionen) > 0:
        return sektionen[0].name
    else:
        return False

def get_sektion_code(sektion):
    sektionen = frappe.db.sql("""SELECT `sektion_c` FROM `tabSektion` WHERE `name` = '{sektion}'""".format(sektion=sektion), as_dict=True)
    if len(sektionen) > 0:
        return sektionen[0].sektion_c
    else:
        return False

def get_status_c(status_c):
    mapper = {
        'Anmeldung': 'Anmeldung',
        'OnlineAnmeldung': 'Online-Anmeldung',
        'OnlineBeitritt': 'Online-Beitritt',
        'Zuzug': 'Zuzug',
        'Regulaer': 'Regulär',
        'Gestorben': 'Gestorben',
        'Kuendigung': 'Kündigung',
        'Wegzug': 'Wegzug',
        'Ausschluss': 'Ausschluss',
        'Inaktiv': 'Inaktiv',
        'InteressentIn': 'Interessent:In'
    }
    if status_c in mapper:
        return mapper[status_c]
    else:
        return False

def get_mitgliedtyp_c(mitgliedtyp_c):
    mapper = {
        'privat': 'Privat',
        'kollektiv': 'Kollektiv',
        'geschaeft': 'Geschäft'
    }
    if mitgliedtyp_c.lower() in mapper:
        return mapper[mitgliedtyp_c.lower()]
    else:
        return False
def get_inkl_hv(inkl_hv):
    curr_year = int(getdate().strftime("%Y"))
    if inkl_hv:
        if int(inkl_hv) >= curr_year:
            return 1
        else:
            return 0
    else:
        return 0

def adressen_und_kontakt_handling(new_mitgliedschaft, kwargs):
    mitglied = False
    objekt = False
    rechnung = False
    filiale = False
    mitbewohner = False
    zeitung = False
    
    for adresse in kwargs["Adressen"]["AdressenListe"]:
        adressen_dict = adresse
    
        if isinstance(adressen_dict, str):
            frappe.log_error("{0}".format(adressen_dict), 'umwandlung str in dict')
            adressen_dict = json.loads(adressen_dict)
        
        if adressen_dict['Typ'] == 'Filiale':
            filiale = adressen_dict
        elif adressen_dict['Typ'] == 'Mitbewohner':
            mitbewohner = adressen_dict
        elif adressen_dict['Typ'] == 'Zeitung':
            zeitung = adressen_dict
        elif adressen_dict['Typ'] == 'Mitglied':
            mitglied = adressen_dict
        elif adressen_dict['Typ'] == 'Objekt':
            objekt = adressen_dict
        elif adressen_dict['Typ'] == 'Rechnung':
            rechnung = adressen_dict
        else:
            # unbekannter adresstyp
            frappe.log_error("{0}".format(adressen_dict), 'unbekannter adresstyp')
            return False
    
    if not mitglied and not objekt:
        frappe.log_error("{0}".format(kwargs), 'adress/kontakt anlage: weder mitglied noch objekt')
        # eines von beiden muss zwingend vorhanden sein
        return False
    
    if mitglied:
        # erfassung mitglied-daten
        for kontaktdaten in mitglied["Kontakte"]:
            if kontaktdaten["IstHauptkontakt"]:
                # hauptmiglied
                if kontaktdaten["Firma"]:
                    new_mitgliedschaft.kundentyp = 'Unternehmen'
                    new_mitgliedschaft.firma = kontaktdaten["Firma"]
                    new_mitgliedschaft.zusatz_firma = kontaktdaten["FirmaZusatz"]
                else:
                    new_mitgliedschaftkundentyp = 'Einzelperson'
                if kontaktdaten["Anrede"] != 'Unbekannt':
                    new_mitgliedschaft.anrede_c = str(kontaktdaten["Anrede"])
                new_mitgliedschaft.nachname_1 = str(kontaktdaten["Nachname"])
                new_mitgliedschaft.vorname_1 = str(kontaktdaten["Vorname"])
                new_mitgliedschaft.tel_p_1 = str(kontaktdaten["Telefon"])
                new_mitgliedschaft.tel_m_1 = str(kontaktdaten["Mobile"])
                new_mitgliedschaft.tel_g_1 = str(kontaktdaten["TelefonGeschaeft"])
                new_mitgliedschaft.e_mail_1 = str(kontaktdaten["Email"])
                new_mitgliedschaft.zusatz_adresse = str(mitglied["Adresszusatz"])
                new_mitgliedschaft.strasse = str(mitglied["Strasse"])
                new_mitgliedschaft.nummer = str(mitglied["Hausnummer"])
                new_mitgliedschaft.postfach = str(mitglied["Postfach"])
                new_mitgliedschaft.postfach_nummer = str(mitglied["PostfachNummer"])
                new_mitgliedschaft.plz = str(mitglied["Postleitzahl"])
                new_mitgliedschaft.ort = str(mitglied["Ort"])
                if mitglied["FuerKorrespondenzGesperrt"]:
                    new_mitgliedschaft.adressen_gesperrt = 1
            else:
                # solidarmitglied
                new_mitgliedschaft.hat_solidarmitglied = 1
                if kontaktdaten["Anrede"] != 'Unbekannt':
                    new_mitgliedschaft.anrede_2 = str(kontaktdaten["Anrede"])
                new_mitgliedschaft.nachname_2 = str(kontaktdaten["Nachname"])
                new_mitgliedschaft.vorname_2 = str(kontaktdaten["Vorname"])
                new_mitgliedschaft.tel_p_2 = str(kontaktdaten["Telefon"])
                new_mitgliedschaft.tel_m_2 = str(kontaktdaten["Mobile"])
                new_mitgliedschaft.tel_g_2 = str(kontaktdaten["TelefonGeschaeft"])
                new_mitgliedschaft.e_mail_2 = str(kontaktdaten["Email"])
        
    
    if objekt:
        if mitglied:
            # erfassung objektadresse
            new_mitgliedschaft.abweichende_objektadresse = 1
            new_mitgliedschaft.objekt_zusatz_adresse = objekt["Adresszusatz"]
            new_mitgliedschaft.objekt_strasse = objekt["Strasse"]
            new_mitgliedschaft.objekt_nummer = objekt["Hausnummer"]
            new_mitgliedschaft.objekt_plz = objekt["Postleitzahl"]
            new_mitgliedschaft.objekt_ort = mitglied["Ort"]
            if objekt["FuerKorrespondenzGesperrt"]:
                new_mitgliedschaft.adressen_gesperrt = 1
        else:
            # erfassung mitglied-daten auf basis objekt-daten
            for kontaktdaten in objekt["Kontakte"]:
                if kontaktdaten["IstHauptkontakt"]:
                    # hauptmiglied
                    if kontaktdaten["Firma"]:
                        new_mitgliedschaft.kundentyp = 'Unternehmen'
                        new_mitgliedschaft.firma = kontaktdaten["Firma"]
                        new_mitgliedschaft.zusatz_firma = kontaktdaten["FirmaZusatz"]
                    else:
                        new_mitgliedschaftkundentyp = 'Einzelperson'
                    if kontaktdaten["Anrede"] != 'Unbekannt':
                        new_mitgliedschaft.anrede_c = kontaktdaten["Anrede"]
                    new_mitgliedschaft.nachname_1 = kontaktdaten["Nachname"]
                    new_mitgliedschaft.vorname_1 = kontaktdaten["Vorname"]
                    new_mitgliedschaft.tel_p_1 = kontaktdaten["Telefon"]
                    new_mitgliedschaft.tel_m_1 = kontaktdaten["Mobile"]
                    new_mitgliedschaft.tel_g_1 = kontaktdaten["TelefonGeschaeft"]
                    new_mitgliedschaft.e_mail_1 = kontaktdaten["Email"]
                    new_mitgliedschaft.zusatz_adresse = objekt["Adresszusatz"]
                    new_mitgliedschaft.strasse = objekt["Strasse"]
                    new_mitgliedschaft.nummer = objekt["Hausnummer"]
                    new_mitgliedschaft.postfach = objekt["Postfach"]
                    new_mitgliedschaft.postfach_nummer = objekt["PostfachNummer"]
                    new_mitgliedschaft.plz = objekt["Postleitzahl"]
                    new_mitgliedschaft.ort = objekt["Ort"]
                    if objekt["FuerKorrespondenzGesperrt"]:
                        new_mitgliedschaft.adressen_gesperrt = 1
                else:
                    # solidarmitglied
                    new_mitgliedschaft.hat_solidarmitglied = 1
                    if kontaktdaten["Anrede"] != 'Unbekannt':
                        new_mitgliedschaft.anrede_2 = kontaktdaten["Anrede"]
                    new_mitgliedschaft.nachname_2 = kontaktdaten["Nachname"]
                    new_mitgliedschaft.vorname_2 = kontaktdaten["Vorname"]
                    new_mitgliedschaft.tel_p_2 = kontaktdaten["Telefon"]
                    new_mitgliedschaft.tel_m_2 = kontaktdaten["Mobile"]
                    new_mitgliedschaft.tel_g_2 = kontaktdaten["TelefonGeschaeft"]
                    new_mitgliedschaft.e_mail_2 = kontaktdaten["Email"]
    else:
        # reset objektadresse
        new_mitgliedschaft.abweichende_objektadresse = 0
        new_mitgliedschaft.objekt_zusatz_adresse = ''
        new_mitgliedschaft.objekt_strasse = ''
        new_mitgliedschaft.objekt_nummer = ''
        new_mitgliedschaft.objekt_plz = ''
        new_mitgliedschaft.objekt_ort = ''
    
    if rechnung:
        # erfassung rechnungsadresse
        # tbd...
        frappe.log_error("{0}".format(rechnung), 'Adressen Handling Typ Rechnung noch nicht umgesetzt')
        
    if mitbewohner:
        # erfassung solidarmitglied
        # tbd...
        frappe.log_error("{0}".format(mitbewohner), 'Adressen Handling Typ Mitbewohner noch nicht umgesetzt')
        
    if filiale:
        # erfassung filiale
        # tbd...
        frappe.log_error("{0}".format(filiale), 'Adressen Handling Typ Filiale noch nicht umgesetzt')
        
    if zeitung:
        # erfassung zeitung
        # tbd...
        frappe.log_error("{0}".format(zeitung), 'Adressen Handling Typ Zeitung noch nicht umgesetzt')
    
    return new_mitgliedschaft

# API (ausgehend zu Service-Platform)
# -----------------------------------------------

# Bezug neuer mitgliedId 
def mvm_neue_mitglieder_nummer(mitgliedschaft):
    from mvd.mvd.service_plattform.api import neue_mitglieder_nummer
    sektion_code = get_sektion_code(mitgliedschaft.sektion_id)
    return neue_mitglieder_nummer(sektion_code)

def send_mvm_to_sp(mitgliedschaft):
    from mvd.mvd.service_plattform.api import update_mvm
    prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
    update_status = update_mvm(prepared_mvm)
    return update_status

def prepare_mvm_for_sp(mitgliedschaft):
    adressen = get_adressen_for_sp(mitgliedschaft)
    prepared_mvm = {
        "mitgliedNummer": str(mitgliedschaft.mitglied_nr),
        "mitgliedId": int(mitgliedschaft.mitglied_id),
        "sektionCode": str(get_sektion_code(mitgliedschaft.sektion_id)),
        "typ": str(mitgliedschaft.mitgliedtyp_c),
        "status": str(mitgliedschaftstatus_c),
        "regionCode": "", # ???
        "istTemporaeresMitglied": False, # ???
        "fuerBewirtschaftungGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
        "erfassungsdatum": "2021-12-15T18:56:17.583Z",
        "eintrittsdatum": mitgliedschaft.eintritt, # achtung nur date!
        "austrittsdatum": mitgliedschaft.austritt, # achtung nur date!
        "zuzugsdatum": mitgliedschaft.zuzug or '', # achtung nur date!
        "wegzugsdatum": mitgliedschaft.wegzug or '', # achtung nur date!
        "kuendigungPer": mitgliedschaft.kuendigung or '', # achtung nur date!
        "jahrBezahltMitgliedschaft": 0, # ???
        "betragBezahltMitgliedschaft": 0, # ???
        "jahrBezahltHaftpflicht": 0, # ???
        "betragBezahltHaftpflicht": 0, # ???
        "naechstesJahrGeschuldet": True, # ???
        "bemerkungen": str(mitgliedschaft.wichtig) or '',
        "anzahlZeitungen": int(mitgliedschaft.m_und_w),
        "zeitungAlsPdf": True if mitgliedschaft.m_und_w_pdf else False,
        "adressen": adressen
    }
    
    return prepared_mvm

def get_adressen_for_sp(mitgliedschaft):
    adressen = []
    mitglied = {
        "typ": "Mitglied",
        "strasse": str(mitgliedschaft.strasse),
        "hausnummer": str(mitgliedschaft.nummer),
        "hausnummerZusatz": str(mitgliedschaft.nummer_zu),
        "postleitzahl": str(mitgliedschaft.plz),
        "ort": str(mitgliedschaft.ort),
        "adresszusatz": str(mitgliedschaft.zusatz_adresse),
        "postfach": True if mitgliedschaft.postfach else False,
        "postfachNummer": str(mitgliedschaft.postfach_nummer),
        "fuerKorrespondenzGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
        "kontakte": [
            {
                "anrede": str(mitgliedschaft.anrede_c) if mitgliedschaft.anrede_c else "Unbekannt",
                "sprache": "Deutsch",
                "istHauptkontakt": True,
                "vorname": str(mitgliedschaft.vorname_1),
                "nachname": str(mitgliedschaft.nachname_1),
                "email": str(mitgliedschafte_mail_1) or '',
                "telefon": str(mitgliedschaft.tel_p_1) or '',
                "mobile": str(mitgliedschafttel_m_1) or '',
                "telefonGeschaeft": str(mitgliedschaft.tel_g_1) or '',
                "firma": str(mitgliedschaft.firma) if mitgliedschaft.kundentyp == 'Unternehmen' else '',
                "firmaZusatz": str(mitgliedschaft.zusatz_firma) if mitgliedschaft.kundentyp == 'Unternehmen' else ''
            }
        ]
    }
    
    if mitgliedschaft.hat_solidarmitglied:
        solidarmitglied = {
            "anrede": str(mitgliedschaft.anrede_2) if mitgliedschaft.anrede_2 else "Unbekannt",
            "sprache": "Deutsch",
            "istHauptkontakt": False,
            "vorname": str(mitgliedschaft.vorname_2),
            "nachname": str(mitgliedschaft.nachname_2),
            "email": str(mitgliedschafte_mail_2) or '',
            "telefon": str(mitgliedschaft.tel_p_2) or '',
            "mobile": str(mitgliedschafttel_m_2) or '',
            "telefonGeschaeft": str(mitgliedschaft.tel_g_2) or '',
            "firma": '',
            "firmaZusatz": ''
        }
        mitglied['kontakte'].append(solidarmitglied)
    
    adressen.append(mitglied)
    
    return adressen

# Sektionswechsel
def mvm_sektionswechsel(mitgliedschaft):
    return "Methode in Arbeit"

# Kündigungsmutation
def mvm_kuendigung(mitgliedschaft):
    return "Methode in Arbeit"

# /API
# -----------------------------------------------
