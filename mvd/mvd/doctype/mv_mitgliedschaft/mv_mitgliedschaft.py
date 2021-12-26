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
    def after_insert(self):
        if not self.sp_no_update:
            if self.creation == self.modified:
                if not self.validierung_notwendig or str(self.validierung_notwendig) == '0':
                    send_mvm_to_sp(self, False)
                    self.sp_no_update = 1
    
    def on_update(self):
        if not self.sp_no_update:
            if self.creation != self.modified:
                if not self.validierung_notwendig or str(self.validierung_notwendig) == '0':
                    close_open_validations(self.name)
                    send_mvm_to_sp(self, True)
                else:
                    create_abl("Daten Validieren", self)
    
    def set_new_name(self):
        if not self.mitglied_nr or not self.mitglied_id:
            mitglied_nummer_obj = mvm_neue_mitglieder_nummer(self)
            self.mitglied_nr = mitglied_nummer_obj["mitgliedNummer"]
            self.mitglied_id = mitglied_nummer_obj["mitgliedId"]
        return
    
    def validate(self):
        if not self.validierung_notwendig or str(self.validierung_notwendig) == '0':
            # Mitglied
            self.kunde_mitglied = self.validate_kunde_mitglied()
            self.kontakt_mitglied = self.validate_kontakt_mitglied(primary=True)
            self.adresse_mitglied, self.objekt_adresse = self.validate_adresse_mitglied()
            join_mitglied_contact_and_address(self.kontakt_mitglied, self.adresse_mitglied)
            
            # Solidarmitglied
            if self.hat_solidarmitglied:
                self.kontakt_solidarmitglied = self.validate_kontakt_mitglied(primary=False)
                if not self.kontakt_solidarmitglied:
                    self.hat_solidarmitglied = '0'
                else:
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
            if self.postfach == 1 or self.abweichende_objektadresse == 1:
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
            if self.postfach == 1 or self.abweichende_objektadresse == 1:
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
    if mitgliedschaft.rg_postfach == 1:
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
    
    if mitgliedschaft.rg_postfach == 1:
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
    address_title = ("-").join((str(mitgliedschaft.mitglied_id), 'Objekt'))
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
    address_title = ("-").join((str(mitgliedschaft.mitglied_id), 'Objekt'))
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
    if mitgliedschaft.postfach == 1:
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
    
    if mitgliedschaft.postfach == 1:
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
        if not  mitgliedschaft.nachname_2 and not mitgliedschaft.vorname_2:
            # Weder Vor- noch Nachname, Anlage Solidarmitglied abgebrochen
            return ''
        
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
        if mitgliedschaft.vorname_1:
            customer.customer_name = (" ").join((mitgliedschaft.vorname_1, mitgliedschaft.nachname_1))
        else:
            customer.customer_name = mitgliedschaft.nachname_1
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
        if mitgliedschaft.vorname_1:
            customer_name = (" ").join((mitgliedschaft.vorname_1, mitgliedschaft.nachname_1))
        else:
            customer_name = mitgliedschaft.nachname_1
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
                return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
        else:
            if mitgliedschaft.anrede_c == mitgliedschaft.anrede_2:
                # selbes Geschlecht
                if mitgliedschaft.nachname_1 == mitgliedschaft.nachname_2:
                    # gleiche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return 'Sehr geehrter Herr {vorname_1} {nachname_1}, sehr geehrter Herr {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return 'Sehr geehrte Frau {vorname_1} {nachname_1}, sehr geehrte Frau {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                else:
                    # unterschiedliche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return 'Sehr geehrter Herr {nachname_1}, sehr geehrter Herr {nachname_2}'.format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return 'Sehr geehrte Frau {nachname_1}, sehr geehrte Frau {nachname_2}'.format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
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
                        return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                else:
                    # unterschiedliche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return 'Sehr geehrter Herr {nachname_1}, sehr geehrte Frau {nachname_2}'.format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return 'Sehr geehrte Frau {nachname_1}, sehr geehrter Herr {nachname_2}'.format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
        
    else:
        # ohne Solidarmitglied
        if mitgliedschaft.anrede_c == 'Herr':
            return 'Sehr geehrter Herr {nachname}'.format(nachname=mitgliedschaft.nachname_1)
        elif mitgliedschaft.anrede_c == 'Frau':
            return 'Sehr geehrte Frau {nachname}'.format(nachname=mitgliedschaft.nachname_1)
        else:
            return 'Guten Tag {vorname} {nachname}'.format(vorname=mitgliedschaft.vorname_1 or '', nachname=mitgliedschaft.nachname_1)

@frappe.whitelist()
def sektionswechsel(mitgliedschaft, neue_sektion, zuzug_per):
    try:
        mitgliedschaft = frappe.get_doc("MV Mitgliedschaft", mitgliedschaft)
        new_mitgliedschaft = frappe.copy_doc(mitgliedschaft)
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

def close_open_validations(mitgliedschaft):
    open_abl = frappe.db.sql("""SELECT `name` FROM `tabArbeits Backlog` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}' AND `status` = 'Open' AND `typ` = 'Daten Validieren'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)
    for abl in open_abl:
        abl = frappe.get_doc("Arbeits Backlog", abl.name)
        abl.status = 'Completed'
        abl.save()

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
def raise_xxx(code, title, message, daten=None):
    frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(code, title, message, frappe.utils.get_traceback(), daten or ''), 'SP API Error!')
    frappe.local.response.http_status_code = code
    frappe.local.response.message = message
    return ['{code} {title}'.format(code=code, title=title), {
        "error": {
            "code": code,
            "message": "{message}".format(message=message)
        }
    }]
    
def raise_200(answer='Success'):
    frappe.local.response.http_status_code = 200
    frappe.local.response.message = answer
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
                return raise_xxx(404, 'Not Found', 'Sektion ({sektion_id}) not found'.format(sektion_id=kwargs['SektionCode']), daten=kwargs)
                
            status_c = get_status_c(kwargs['Status'])
            if not status_c:
                return raise_xxx(404, 'Not Found', 'MitgliedStatus ({status_c}) not found'.format(status_c=kwargs['Status']), daten=kwargs)
                
            mitgliedtyp_c = get_mitgliedtyp_c(kwargs['Typ'])
            if not mitgliedtyp_c:
                return raise_xxx(404, 'Not Found', 'typ ({mitgliedtyp_c}) not found'.format(mitgliedtyp_c=kwargs['Typ']), daten=kwargs)
            
            if kwargs['Eintrittsdatum']:
                eintritt = kwargs['Eintrittsdatum'].split("T")[0]
            else:
                eintritt = None
            if status_c in ('Anmeldung', 'Online-Anmeldung'):
                if kwargs['Erfassungsdatum']:
                    eintritt = kwargs['Erfassungsdatum'].split("T")[0]
                else:
                    eintritt = None
            if not eintritt and status_c == 'Inaktiv':
                if kwargs['Erfassungsdatum']:
                    eintritt = kwargs['Erfassungsdatum'].split("T")[0]
                else:
                    eintritt = None
            
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
            mitgliedschaft.wichtig = kwargs['Bemerkungen'] if kwargs['Bemerkungen'] else ''
            mitgliedschaft.eintritt = eintritt
            mitgliedschaft.zuzug = zuzug
            mitgliedschaft.wegzug = wegzug
            mitgliedschaft.austritt = austritt
            mitgliedschaft.kuendigung = kuendigung
            mitgliedschaft.sp_no_update = 1
            
            mitgliedschaft = adressen_und_kontakt_handling(mitgliedschaft, kwargs)
            
            if not mitgliedschaft:
                return raise_xxx(500, 'Internal Server Error', 'Beim Adressen Update ist etwas schief gelaufen', daten=kwargs)
            
            # logik ob validiert werde muss oder nicht muss noch implementiert werden!
            mitgliedschaft.validierung_notwendig = '0'
            mitgliedschaft.save()
            frappe.db.commit()
            
            return raise_200()
            
        except Exception as err:
            return raise_xxx(500, 'Internal Server Error', err, daten=kwargs)
    else:
        return missing_keys

def mvm_neuanlage(kwargs):
    missing_keys = check_main_keys(kwargs)
    if not missing_keys:
        try:
            sektion_id = get_sektion_id(kwargs['SektionCode'])
            if not sektion_id:
                return raise_xxx(404, 'Not Found', 'Sektion ({sektion_id}) not found'.format(sektion_id=kwargs['SektionCode']), daten=kwargs)
            
            status_c = get_status_c(kwargs['Status'])
            if not status_c:
                return raise_xxx(404, 'Not Found', 'MitgliedStatus ({status_c}) not found'.format(status_c=kwargs['Status']), daten=kwargs)
            
            mitgliedtyp_c = get_mitgliedtyp_c(kwargs['Typ'])
            if not mitgliedtyp_c:
                return raise_xxx(404, 'Not Found', 'typ ({mitgliedtyp_c}) not found'.format(mitgliedtyp_c=kwargs['Typ']), daten=kwargs)
            
            if kwargs['Eintrittsdatum']:
                eintritt = kwargs['Eintrittsdatum'].split("T")[0]
            else:
                eintritt = None
            if status_c in ('Anmeldung', 'Online-Anmeldung'):
                if kwargs['Erfassungsdatum']:
                    eintritt = kwargs['Erfassungsdatum'].split("T")[0]
                else:
                    eintritt = None
            
            if not eintritt and status_c == 'Inaktiv':
                if kwargs['Erfassungsdatum']:
                    eintritt = kwargs['Erfassungsdatum'].split("T")[0]
                else:
                    eintritt = None
            
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
                'wichtig': str(kwargs['Bemerkungen']) if kwargs['Bemerkungen'] else '',
                'eintritt': eintritt,
                'zuzug': zuzug,
                'wegzug': wegzug,
                'austritt': austritt,
                'kuendigung': kuendigung,
                'sp_no_update': 1
            })
            
            new_mitgliedschaft = adressen_und_kontakt_handling(new_mitgliedschaft, kwargs)
            
            if not new_mitgliedschaft:
                return raise_xxx(500, 'Internal Server Error', 'Bei der Adressen Anlage ist etwas schief gelaufen', daten=kwargs)
            
            # logik ob validiert werde muss oder nicht muss noch implementiert werden!
            new_mitgliedschaft.validierung_notwendig = '0'
            
            new_mitgliedschaft.insert()
            frappe.db.commit()
            
            return raise_200()
            
        except Exception as err:
            return raise_xxx(500, 'Internal Server Error', err, daten=kwargs)
            
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
            return raise_xxx(400, 'Bad Request', '{key} missing'.format(key=key), daten=kwargs)
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
        'geschaeft': 'Geschäft',
        'Privat': 'Privat',
        'Kollektiv': 'Kollektiv',
        'Geschaeft': 'Geschäft'
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
    try:
        mitglied = False
        objekt = False
        rechnung = False
        filiale = False
        mitbewohner = False
        zeitung = False
        
        for adresse in kwargs["Adressen"]["AdressenListe"]:
            adressen_dict = adresse
            
            if isinstance(adressen_dict, str):
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
        
        if not mitglied:
            frappe.log_error("{0}".format(kwargs), 'adress/kontakt anlage: Keine mitglied Adresse')
            # muss zwingend vorhanden sein
            return False
        
        if mitglied:
            # erfassung mitglied-daten
            for kontaktdaten in mitglied["Kontakte"]:
                if kontaktdaten["IstHauptkontakt"]:
                    # hauptmiglied
                    if not mitglied["Strasse"] or str(mitglied["Strasse"]) == '':
                        if not mitglied["Postfach"]:
                            # eines von beidem muss zwingend vorhanden sein
                            frappe.log_error("{0}".format(kwargs), 'adress/kontakt anlage: Weder Postfach noch Strasse')
                            return False
                    if kontaktdaten["Firma"]:
                        new_mitgliedschaft.kundentyp = 'Unternehmen'
                        new_mitgliedschaft.firma = str(kontaktdaten["Firma"])
                        new_mitgliedschaft.zusatz_firma = str(kontaktdaten["FirmaZusatz"]) if kontaktdaten["FirmaZusatz"] else ''
                    else:
                        new_mitgliedschaft.kundentyp = 'Einzelperson'
                    if kontaktdaten["Anrede"] != 'Unbekannt':
                        new_mitgliedschaft.anrede_c = str(kontaktdaten["Anrede"]) if kontaktdaten["Anrede"] else ''
                    new_mitgliedschaft.nachname_1 = str(kontaktdaten["Nachname"]) if kontaktdaten["Nachname"] else ''
                    new_mitgliedschaft.vorname_1 = str(kontaktdaten["Vorname"]) if kontaktdaten["Vorname"] else ''
                    new_mitgliedschaft.tel_p_1 = str(kontaktdaten["Telefon"]) if kontaktdaten["Telefon"] else ''
                    if kontaktdaten["Mobile"]:
                        if str(kontaktdaten["Mobile"]) != str(kontaktdaten["Telefon"]):
                            new_mitgliedschaft.tel_m_1 = str(kontaktdaten["Mobile"])
                    new_mitgliedschaft.tel_g_1 = str(kontaktdaten["TelefonGeschaeft"]) if kontaktdaten["TelefonGeschaeft"] else ''
                    new_mitgliedschaft.e_mail_1 = str(kontaktdaten["Email"]) if kontaktdaten["Email"] else ''
                    new_mitgliedschaft.zusatz_adresse = str(mitglied["Adresszusatz"]) if mitglied["Adresszusatz"] else ''
                    new_mitgliedschaft.strasse = str(mitglied["Strasse"]) if mitglied["Strasse"] else ''
                    new_mitgliedschaft.nummer = str(mitglied["Hausnummer"]) if mitglied["Hausnummer"] else ''
                    new_mitgliedschaft.postfach = 1 if mitglied["Postfach"] else '0'
                    new_mitgliedschaft.postfach_nummer = str(mitglied["PostfachNummer"]) if mitglied["PostfachNummer"] else ''
                    new_mitgliedschaft.plz = str(mitglied["Postleitzahl"]) if mitglied["Postleitzahl"] else ''
                    new_mitgliedschaft.ort = str(mitglied["Ort"]) if mitglied["Ort"] else ''
                    if mitglied["FuerKorrespondenzGesperrt"]:
                        new_mitgliedschaft.adressen_gesperrt = 1
                else:
                    # solidarmitglied
                    new_mitgliedschaft.hat_solidarmitglied = 1
                    if kontaktdaten["Anrede"] != 'Unbekannt':
                        new_mitgliedschaft.anrede_2 = str(kontaktdaten["Anrede"]) if kontaktdaten["Anrede"] else ''
                    new_mitgliedschaft.nachname_2 = str(kontaktdaten["Nachname"]) if kontaktdaten["Nachname"] else ''
                    new_mitgliedschaft.vorname_2 = str(kontaktdaten["Vorname"]) if kontaktdaten["Vorname"] else ''
                    new_mitgliedschaft.tel_p_2 = str(kontaktdaten["Telefon"]) if kontaktdaten["Telefon"] else ''
                    if kontaktdaten["Mobile"]:
                        if str(kontaktdaten["Mobile"]) != str(kontaktdaten["Telefon"]):
                            new_mitgliedschaft.tel_m_2 = str(kontaktdaten["Mobile"])
                    new_mitgliedschaft.tel_g_2 = str(kontaktdaten["TelefonGeschaeft"]) if kontaktdaten["TelefonGeschaeft"] else ''
                    new_mitgliedschaft.e_mail_2 = str(kontaktdaten["Email"]) if kontaktdaten["Email"] else ''
        
        if objekt:
            if objekt["Strasse"]:
                new_mitgliedschaft.abweichende_objektadresse = 1
                new_mitgliedschaft.objekt_zusatz_adresse = str(objekt["Adresszusatz"]) if objekt["Adresszusatz"] else ''
                new_mitgliedschaft.objekt_strasse = str(objekt["Strasse"]) if objekt["Strasse"] else ''
                new_mitgliedschaft.objekt_nummer = str(objekt["Hausnummer"]) if objekt["Hausnummer"] else ''
                new_mitgliedschaft.objekt_plz = str(objekt["Postleitzahl"]) if objekt["Postleitzahl"] else ''
                new_mitgliedschaft.objekt_ort = str(objekt["Ort"]) if objekt["Ort"] else ''
                if objekt["FuerKorrespondenzGesperrt"]:
                    new_mitgliedschaft.adressen_gesperrt = 1
            else:
                frappe.log_error("Adressdaten:\n{0}\n\nMitgliedsdaten:\n{1}".format(objekt, kwargs), 'Adresse Typ Objekt: Wurde entfernt; fehlende Strasse')
                # reset objektadresse
                new_mitgliedschaft.abweichende_objektadresse = '0'
                new_mitgliedschaft.objekt_zusatz_adresse = None
                new_mitgliedschaft.objekt_strasse = None
                new_mitgliedschaft.objekt_nummer = None
                new_mitgliedschaft.objekt_plz = None
                new_mitgliedschaft.objekt_ort = None
        else:
            # reset objektadresse
            new_mitgliedschaft.abweichende_objektadresse = '0'
            new_mitgliedschaft.objekt_zusatz_adresse = None
            new_mitgliedschaft.objekt_strasse = None
            new_mitgliedschaft.objekt_nummer = None
            new_mitgliedschaft.objekt_plz = None
            new_mitgliedschaft.objekt_ort = None
        
        
        if rechnung:
            new_mitgliedschaft.abweichende_rechnungsdresse = 1
            new_mitgliedschaft.rg_zusatz_adresse = str(rechnung["Adresszusatz"]) if rechnung["Adresszusatz"] else ''
            new_mitgliedschaft.rg_strasse = str(rechnung["Strasse"]) if rechnung["Strasse"] else ''
            new_mitgliedschaft.rg_nummer = str(rechnung["Hausnummer"]) if rechnung["Hausnummer"] else ''
            new_mitgliedschaft.rg_postfach = 1 if rechnung["Postfach"] else '0'
            new_mitgliedschaft.rg_postfach_nummer = str(rechnung["PostfachNummer"]) if rechnung["PostfachNummer"] else ''
            new_mitgliedschaft.rg_plz = str(rechnung["Postleitzahl"]) if rechnung["Postleitzahl"] else ''
            new_mitgliedschaft.rg_ort = str(rechnung["Ort"]) if rechnung["Ort"] else ''
            if rechnung["FuerKorrespondenzGesperrt"]:
                new_mitgliedschaft.adressen_gesperrt = 1
            for kontaktdaten in rechnung["Kontakte"]:
                if kontaktdaten["IstHauptkontakt"]:
                    if str(kontaktdaten["Nachname"]) != new_mitgliedschaft.nachname_1:
                        if str(kontaktdaten["Vorname"]) != new_mitgliedschaft.vorname_1:
                            # unabhängiger debitor
                            new_mitgliedschaft.unabhaengiger_debitor = 1
                            if kontaktdaten["Firma"]:
                                new_mitgliedschaft.rg_kundentyp = 'Unternehmen'
                                new_mitgliedschaft.rg_firma = str(kontaktdaten["Firma"])
                                new_mitgliedschaft.rg_zusatz_firma = str(kontaktdaten["FirmaZusatz"]) if kontaktdaten["FirmaZusatz"] else ''
                            else:
                                new_mitgliedschaft.rg_kundentyp = 'Einzelperson'
                            if kontaktdaten["Anrede"] != 'Unbekannt':
                                new_mitgliedschaft.rg_anrede = str(kontaktdaten["Anrede"]) if kontaktdaten["Anrede"] else ''
                            new_mitgliedschaft.rg_nachname_ = str(kontaktdaten["Nachname"]) if kontaktdaten["Nachname"] else ''
                            new_mitgliedschaft.rg_vorname = str(kontaktdaten["Vorname"]) if kontaktdaten["Vorname"] else ''
                            new_mitgliedschaft.rg_tel_p = str(kontaktdaten["Telefon"]) if kontaktdaten["Telefon"] else ''
                            if kontaktdaten["Mobile"]:
                                if str(kontaktdaten["Mobile"]) != str(kontaktdaten["Telefon"]):
                                    new_mitgliedschaft.rg_tel_m = str(kontaktdaten["Mobile"])
                            new_mitgliedschaft.rg_tel_g = str(kontaktdaten["TelefonGeschaeft"]) if kontaktdaten["TelefonGeschaeft"] else ''
                            new_mitgliedschaft.rg_e_mail = str(kontaktdaten["Email"]) if kontaktdaten["Email"] else ''
                    
        
        if zeitung:
            # manuelle erfassung zeitung
            frappe.log_error("Adressdaten:\n{0}\n\nMitgliedsdaten:\n{1}".format(zeitung, kwargs), 'Adresse Typ Zeitung: Manuelle Verarbeitung')
        
        if mitbewohner:
            # manuelle erfassung solidarmitglied
            frappe.log_error("Adressdaten:\n{0}\n\nMitgliedsdaten:\n{1}".format(mitbewohner, kwargs), 'Adresse Typ Mitbewohner: Manuelle Verarbeitung')
        
        if filiale:
            # manuelle erfassung filiale
            frappe.log_error("Adressdaten:\n{0}\n\nMitgliedsdaten:\n{1}".format(filiale, kwargs), 'Adresse Typ Filiale: Manuelle Verarbeitung')
        
        
        return new_mitgliedschaft
        
    except Exception as err:
        return raise_xxx(500, 'Internal Server Error', err, daten=kwargs)

# API (ausgehend zu Service-Platform)
# -----------------------------------------------

# Bezug neuer mitgliedId 
def mvm_neue_mitglieder_nummer(mitgliedschaft):
    from mvd.mvd.service_plattform.api import neue_mitglieder_nummer
    sektion_code = get_sektion_code(mitgliedschaft.sektion_id)
    return neue_mitglieder_nummer(sektion_code)

def send_mvm_to_sp(mitgliedschaft, update):
    from mvd.mvd.service_plattform.api import update_mvm
    prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
    update_status = update_mvm(prepared_mvm, update)
    return update_status

def prepare_mvm_for_sp(mitgliedschaft):
    adressen = get_adressen_for_sp(mitgliedschaft)
    typ_mapper = {
        'Kollektiv': 'Kollektiv',
        'Privat': 'Privat',
        'Geschäft': 'Geschaeft'
    }
    status_mapper = {
        'Anmeldung': 'Anmeldung',
        'Online-Anmeldung': 'OnlineAnmeldung',
        'Online-Beitritt': 'OnlineBeitritt',
        'Zuzug': 'Zuzug',
        'Regulär': 'Regulaer',
        'Gestorben': 'Gestorben',
        'Kündigung': 'Kuendigung',
        'Wegzug': 'Wegzug',
        'Ausschluss': 'Ausschluss',
        'Inaktiv': 'Inaktiv',
        'Interessent:In': 'InteressentIn'
    }
    prepared_mvm = {
        "mitgliedNummer": str(mitgliedschaft.mitglied_nr),
        "mitgliedId": int(mitgliedschaft.mitglied_id),
        "sektionCode": str(get_sektion_code(mitgliedschaft.sektion_id)),
        "typ": str(typ_mapper[mitgliedschaft.mitgliedtyp_c]),
        "status": str(status_mapper[mitgliedschaft.status_c]),
        "regionCode": None, # ???
        "istTemporaeresMitglied": False, # ???
        "fuerBewirtschaftungGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
        "erfassungsdatum": str(mitgliedschaft.creation).replace(" ", "T"),
        "eintrittsdatum": mitgliedschaft.eintritt or None, # achtung nur date!
        "austrittsdatum": mitgliedschaft.austritt or None, # achtung nur date!
        "zuzugsdatum": mitgliedschaft.zuzug or None, # achtung nur date!
        "wegzugsdatum": mitgliedschaft.wegzug or None, # achtung nur date!
        "kuendigungPer": mitgliedschaft.kuendigung or None, # achtung nur date!
        "jahrBezahltMitgliedschaft": None, # ???
        "betragBezahltMitgliedschaft": None, # ???
        "jahrBezahltHaftpflicht": None, # ???
        "betragBezahltHaftpflicht": None, # ???
        "naechstesJahrGeschuldet": True, # ???
        "bemerkungen": str(mitgliedschaft.wichtig) if mitgliedschaft.wichtig else None,
        "anzahlZeitungen": int(mitgliedschaft.m_und_w),
        "zeitungAlsPdf": True if mitgliedschaft.m_und_w_pdf else False,
        "adressen": adressen
    }
    
    return prepared_mvm

def get_adressen_for_sp(mitgliedschaft):
    adressen = []
    mitglied = {
        "typ": "Mitglied",
        "strasse": str(mitgliedschaft.strasse) if mitgliedschaft.strasse else None,
        "hausnummer": str(mitgliedschaft.nummer) if mitgliedschaft.nummer else None,
        "hausnummerZusatz": str(mitgliedschaft.nummer_zu) if mitgliedschaft.nummer_zu else None,
        "postleitzahl": str(mitgliedschaft.plz) if mitgliedschaft.plz else None,
        "ort": str(mitgliedschaft.ort) if mitgliedschaft.ort else None,
        "adresszusatz": str(mitgliedschaft.zusatz_adresse) if mitgliedschaft.zusatz_adresse else None,
        "postfach": True if mitgliedschaft.postfach else False,
        "postfachNummer": str(mitgliedschaft.postfach_nummer) if mitgliedschaft.postfach_nummer else None,
        "fuerKorrespondenzGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
        "kontakte": [
            {
                "anrede": str(mitgliedschaft.anrede_c) if mitgliedschaft.anrede_c else "Unbekannt",
                "sprache": "Deutsch",
                "istHauptkontakt": True,
                "vorname": str(mitgliedschaft.vorname_1) if mitgliedschaft.vorname_1 else None,
                "nachname": str(mitgliedschaft.nachname_1) if mitgliedschaft.nachname_1 else None,
                "email": str(mitgliedschaft.e_mail_1) if mitgliedschaft.e_mail_1 else None,
                "telefon": str(mitgliedschaft.tel_p_1) if mitgliedschaft.tel_p_1 else None,
                "mobile": str(mitgliedschaft.tel_m_1) if mitgliedschaft.tel_m_1 else None,
                "telefonGeschaeft": str(mitgliedschaft.tel_g_1) if mitgliedschaft.tel_g_1 else None,
                "firma": str(mitgliedschaft.firma) if mitgliedschaft.kundentyp == 'Unternehmen' else None,
                "firmaZusatz": str(mitgliedschaft.zusatz_firma) if mitgliedschaft.kundentyp == 'Unternehmen' else None
            }
        ]
    }
    
    if mitgliedschaft.hat_solidarmitglied:
        solidarmitglied = {
            "anrede": str(mitgliedschaft.anrede_2) if mitgliedschaft.anrede_2 else "Unbekannt",
            "sprache": "Deutsch",
            "istHauptkontakt": False,
            "vorname": str(mitgliedschaft.vorname_2) if mitgliedschaft.vorname_2 else None,
            "nachname": str(mitgliedschaft.nachname_2) if mitgliedschaft.nachname_2 else None,
            "email": str(mitgliedschaft.e_mail_2) if mitgliedschaft.e_mail_2 else None,
            "telefon": str(mitgliedschaft.tel_p_2) if mitgliedschaft.tel_p_2 else None,
            "mobile": str(mitgliedschaft.tel_m_2) if mitgliedschaft.tel_m_2 else None,
            "telefonGeschaeft": str(mitgliedschaft.tel_g_2) if mitgliedschaft.tel_g_2 else None,
            "firma": '',
            "firmaZusatz": ''
        }
        mitglied['kontakte'].append(solidarmitglied)
    
    adressen.append(mitglied)
    
    if mitgliedschaft.abweichende_objektadresse:
        objekt = {
            "typ": "Objekt",
            "strasse": str(mitgliedschaft.objekt_strasse) if mitgliedschaft.objekt_strasse else None,
            "hausnummer": str(mitgliedschaft.objekt_hausnummer) if mitgliedschaft.objekt_hausnummer else None,
            "hausnummerZusatz": str(mitgliedschaft.objekt_nummer_zu) if mitgliedschaft.objekt_nummer_zu else None,
            "postleitzahl": str(mitgliedschaft.objekt_plz) if mitgliedschaft.objekt_plz else None,
            "ort": str(mitgliedschaft.objekt_ort) if mitgliedschaft.objekt_ort else None,
            "adresszusatz": str(mitgliedschaft.objekt_zusatz_adresse) if mitgliedschaft.objekt_zusatz_adresse else None,
            "postfach": False,
            "postfachNummer": "",
            "fuerKorrespondenzGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
            "kontakte": []
        }
        adressen.append(objekt)
    
    if mitgliedschaft.abweichende_rechnungsadresse:
        rechnung = {
            "typ": "Rechnung",
            "strasse": str(mitgliedschaft.rg_strasse) if mitgliedschaft.rg_strasse else None,
            "hausnummer": str(mitgliedschaft.rg_nummer) if mitgliedschaft.rg_nummer else None,
            "hausnummerZusatz": str(mitgliedschaft.rg_nummer_zu) if mitgliedschaft.rg_nummer_zu else None,
            "postleitzahl": str(mitgliedschaft.rg_plz) if mitgliedschaft.rg_plz else None,
            "ort": str(mitgliedschaft.rg_ort) if mitgliedschaft.rg_ort else None,
            "adresszusatz": str(mitgliedschaft.rg_zusatz_adresse) if mitgliedschaft.rg_zusatz_adresse else None,
            "postfach": True if mitgliedschaft.rg_postfach else False,
            "postfachNummer": str(mitgliedschaft.rg_postfach_nummer) if mitgliedschaft.rg_postfach_nummer else None,
            "fuerKorrespondenzGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
            "kontakte": []
        }
        
        if mitgliedschaft.unabhaengiger_debitor:
            rechnungskontakt = {
                "anrede": str(mitgliedschaft.rg_anrede) if mitgliedschaft.rg_anrede else "Unbekannt",
                "sprache": "Deutsch",
                "istHauptkontakt": False,
                "vorname": str(mitgliedschaft.rg_vorname) if mitgliedschaft.rg_vorname else None,
                "nachname": str(mitgliedschaft.rg_nachname) if mitgliedschaft.rg_nachname else None,
                "email": str(mitgliedschaft.rg_e_mail) if mitgliedschaft.rg_e_mail else None,
                "telefon": str(mitgliedschaft.rg_tel_p) if mitgliedschaft.rg_tel_p else None,
                "mobile": str(mitgliedschaft.rg_tel_m) if mitgliedschaft.rg_tel_m else None,
                "telefonGeschaeft": str(mitgliedschaft.rg_tel_g) if mitgliedschaft.rg_tel_g else None,
                "firma": str(mitgliedschaft.rg_firma) if mitgliedschaft.rg_firma else None,
                "firmaZusatz": str(mitgliedschaft.rg_zusatz_firma) if mitgliedschaft.rg_zusatz_firma else None,
            }
            rechnung['kontakte'].append(rechnungskontakt)
        
        adressen.append(rechnung)
    
    return adressen

# Sektionswechsel
def mvm_sektionswechsel(mitgliedschaft):
    return "Methode in Arbeit"

# Kündigungsmutation
def mvm_kuendigung(mitgliedschaft):
    return "Methode in Arbeit"

# /API
# -----------------------------------------------
