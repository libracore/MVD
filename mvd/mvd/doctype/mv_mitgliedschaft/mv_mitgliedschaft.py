# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class MVMitgliedschaft(Document):
    def validate(self):
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
        #...
        
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
            update_adresse_mitglied(self)
            if self.postfach:
                if self.objekt_adresse:
                    update_objekt_adresse(self)
                    return self.adresse_mitglied, self.objekt_adresse
                else:
                    objekt_adresse = create_objekt_adresse(self)
                    return self.adresse_mitglied, objekt_adresse
            else:
                if self.objekt_adresse:
                    self.remove_objekt_adresse()
                return self.adresse_mitglied, ''
        else:
            address = create_adresse_mitglied(self)
            if self.postfach:
                if self.objekt_adresse:
                    update_objekt_adresse(self)
                    return address, self.objekt_adresse
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
    
def create_objekt_adresse(mitgliedschaft):
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
        'is_shipping_address': is_shipping_address
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
    
    address.links = []
    link = address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied
    address.save(ignore_permissions=True)
    return

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
    
    address.links = []
    link = address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied
    address.save(ignore_permissions=True)
    return

def create_adresse_mitglied(mitgliedschaft):
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
        'is_shipping_address': is_shipping_address
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
    
    new_customer = frappe.get_doc({
        'doctype': 'Customer',
        'customer_name': customer_name,
        'customer_addition': customer_addition,
        'customer_type': customer_type
    })
    new_customer.insert()
    frappe.db.commit()
    return new_customer.name

@frappe.whitelist()
def get_address_overview(mvd):
    try:
        self = frappe.get_doc("MV Mitgliedschaft", mvd)
        # Korrespondenz Adresse
        korrespondenz_adresse = ''
        if self.kundentyp == 'Einzelperson' and self.postfach != 1:
            # Adressformat (Korrespondenz, Einzelperson, kein Postfach):
            '''
                "Anrede" "Vorname" "Nachname"
                "Adress Zusatz"
                "Strasse" "Nummer" "Nummer Zusatz"
                "PLZ" "Ort"
                "---"
                "Tel P"
                "Tel M"
                "Tel G"
                "Email"
            '''
            korrespondenz_adresse += self.anrede_c + " "
            korrespondenz_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
            if self.zusatz_adresse:
                korrespondenz_adresse += self.zusatz_adresse + "<br>"
            korrespondenz_adresse += self.strasse + " "
            if self.nummer:
                korrespondenz_adresse += str(self.nummer)
            if self.nummer_zu:
                korrespondenz_adresse += self.nummer_zu
            korrespondenz_adresse += "<br>"
            korrespondenz_adresse += str(self.plz) + " " + self.ort
        
        if self.kundentyp == 'Unternehmen' and self.postfach != 1:
            # Adressformat (Korrespondenz, Unternehmen, kein Postfach):
            '''
                "Firma"
                "Firma Zusatz"
                "Anrede" "Vorname" "Nachname"
                "Adress Zusatz"
                "Strasse" "Nummer" "Nummer Zusatz"
                "PLZ" "Ort"
                "---"
                "Tel P"
                "Tel M"
                "Tel G"
                "Email"
            '''
            korrespondenz_adresse += self.firma + "<br>"
            if self.zusatz_firma:
                korrespondenz_adresse += self.zusatz_firma + "<br>"
            korrespondenz_adresse += self.anrede_c + " "
            korrespondenz_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
            if self.zusatz_adresse:
                korrespondenz_adresse += self.zusatz_adresse + "<br>"
            korrespondenz_adresse += self.strasse + " "
            if self.nummer:
                korrespondenz_adresse += str(self.nummer)
            if self.nummer_zu:
                korrespondenz_adresse += self.nummer_zu
            korrespondenz_adresse += "<br>"
            korrespondenz_adresse += str(self.plz) + " " + self.ort
        
        if self.kundentyp == 'Einzelperson' and self.postfach == 1:
            # Adressformat (Korrespondenz, Einzelperson, Postfach):
            '''
                "Anrede" "Vorname" "Nachname"
                "Adress Zusatz"
                "Postfach" "Postfach Nummer"
                "PLZ" "Ort"
                "---"
                "Tel P"
                "Tel M"
                "Tel G"
                "Email"
            '''
            korrespondenz_adresse += self.anrede_c + " "
            korrespondenz_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
            korrespondenz_adresse += "Postfach "
            if self.postfach_nummer > 0:
                korrespondenz_adresse += str(self.postfach_nummer)
            korrespondenz_adresse += "<br>"
            korrespondenz_adresse += str(self.plz) + " " + self.ort
        
        if self.kundentyp == 'Unternehmen' and self.postfach == 1:
            # Adressformat (Korrespondenz, Unternehmen, Postfach):
            '''
                "Firma"
                "Firma Zusatz"
                "Anrede" "Vorname" "Nachname"
                "Adress Zusatz"
                "Postfach" "Postfach Nummer"
                "PLZ" "Ort"
                "---"
                "Tel P"
                "Tel M"
                "Tel G"
                "Email"
            '''
            korrespondenz_adresse += self.firma + "<br>"
            if self.zusatz_firma:
                korrespondenz_adresse += self.zusatz_firma + "<br>"
            korrespondenz_adresse += self.anrede_c + " "
            korrespondenz_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
            korrespondenz_adresse += "Postfach "
            if self.postfach_nummer > 0:
                korrespondenz_adresse += str(self.postfach_nummer)
            korrespondenz_adresse += "<br>"
            korrespondenz_adresse += str(self.plz) + " " + self.ort
            
        # Objekt Adresse
        '''
            "Strasse" "Nummer" "Nummer Zusatz"
            "PLZ" "Ort"
        '''
        if self.postfach != 1:
            objekt_adresse = False
        else:
            if self.objekt_zusatz_adresse:
                objekt_adresse = self.objekt_zusatz_adresse + "<br>"
                objekt_adresse += self.objekt_strasse
            else:
                objekt_adresse = self.objekt_strasse
            if self.objekt_hausnummer:
                objekt_adresse += " " + str(self.objekt_hausnummer)
            if self.objekt_nummer_zu:
                objekt_adresse += self.objekt_nummer_zu
            objekt_adresse += "<br>"
            objekt_adresse += str(self.objekt_plz) + " " + self.objekt_ort
            
            
        # Rechnungsadresse
        if self.abweichende_rechnungsadresse == 1:
            rechnungs_adresse = ''
            if self.unabhaengiger_debitor == 1:
                if self.rg_kundentyp == 'Einzelperson' and self.rg_postfach != 1:
                    # Adressformat (Rechnungsadresse, Einzelperson, kein Postfach):
                    '''
                        "Anrede" "Vorname" "Nachname"
                        "Adress Zusatz"
                        "Strasse" "Nummer" "Nummer Zusatz"
                        "PLZ" "Ort"
                        "---"
                        "Tel P"
                        "Tel M"
                        "Tel G"
                        "Email"
                    '''
                    rechnungs_adresse += self.rg_anrede + " "
                    rechnungs_adresse += self.rg_vorname + " " + self.rg_nachname + "<br>"
                    if self.rg_zusatz_adresse:
                        rechnungs_adresse += self.rg_zusatz_adresse + "<br>"
                    rechnungs_adresse += self.rg_strasse + " "
                    if self.rg_nummer:
                        rechnungs_adresse += str(self.rg_nummer)
                    if self.rg_nummer_zu:
                        rechnungs_adresse += self.rg_nummer_zu
                    rechnungs_adresse += "<br>"
                    rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
                
                if self.rg_kundentyp == 'Unternehmen' and self.rg_postfach != 1:
                    # Adressformat (Rechnungsadresse, Unternehmen, kein Postfach):
                    '''
                        "Firma"
                        "Firma Zusatz"
                        "Anrede" "Vorname" "Nachname"
                        "Adress Zusatz"
                        "Strasse" "Nummer" "Nummer Zusatz"
                        "PLZ" "Ort"
                        "---"
                        "Tel P"
                        "Tel M"
                        "Tel G"
                        "Email"
                    '''
                    rechnungs_adresse += self.rg_firma + "<br>"
                    if self.rg_zusatz_firma:
                        rechnungs_adresse += self.rg_zusatz_firma + "<br>"
                    rechnungs_adresse += self.rg_anrede + " "
                    rechnungs_adresse += self.rg_vorname + " " + self.rg_nachname + "<br>"
                    if self.rg_zusatz_adresse:
                        rechnungs_adresse += self.rg_zusatz_adresse + "<br>"
                    rechnungs_adresse += self.rg_strasse + " "
                    if self.rg_nummer:
                        rechnungs_adresse += str(self.rg_nummer)
                    if self.rg_nummer_zu:
                        rechnungs_adresse += self.rg_nummer_zu
                    rechnungs_adresse += "<br>"
                    rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
                
                if self.rg_kundentyp == 'Einzelperson' and self.rg_postfach == 1:
                    # Adressformat (Rechnungsadresse, Einzelperson, Postfach):
                    '''
                        "Anrede" "Vorname" "Nachname"
                        "Adress Zusatz"
                        "Postfach" "Postfach Nummer"
                        "PLZ" "Ort"
                        "---"
                        "Tel P"
                        "Tel M"
                        "Tel G"
                        "Email"
                    '''
                    rechnungs_adresse += self.rg_anrede + " "
                    rechnungs_adresse += self.rg_vorname + " " + self.rg_nachname + "<br>"
                    rechnungs_adresse += "Postfach "
                    if self.rg_postfach_nummer > 0:
                        rechnungs_adresse += str(self.rg_postfach_nummer)
                    rechnungs_adresse += "<br>"
                    rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
                
                if self.rg_kundentyp == 'Unternehmen' and self.rg_postfach == 1:
                    # Adressformat (Rechnungsadresse, Unternehmen, Postfach):
                    '''
                        "Firma"
                        "Firma Zusatz"
                        "Anrede" "Vorname" "Nachname"
                        "Adress Zusatz"
                        "Postfach" "Postfach Nummer"
                        "PLZ" "Ort"
                        "---"
                        "Tel P"
                        "Tel M"
                        "Tel G"
                        "Email"
                    '''
                    rechnungs_adresse += self.rg_firma + "<br>"
                    if self.rg_zusatz_firma:
                        rechnungs_adresse += self.rg_zusatz_firma + "<br>"
                    rechnungs_adresse += self.rg_anrede + " "
                    rechnungs_adresse += self.rg_vorname + " " + self.rg_nachname + "<br>"
                    rechnungs_adresse += "Postfach "
                    if self.rg_postfach_nummer > 0:
                        rechnungs_adresse += str(self.rg_postfach_nummer)
                    rechnungs_adresse += "<br>"
                    rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
            else:
                if self.kundentyp == 'Einzelperson':
                    # Einzelperson
                    if self.rg_postfach != 1:
                        # kein Postfach
                        rechnungs_adresse += self.anrede_c + " "
                        rechnungs_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
                        if self.rg_zusatz_adresse:
                            rechnungs_adresse += self.rg_zusatz_adresse + "<br>"
                        rechnungs_adresse += self.rg_strasse + " "
                        if self.rg_nummer:
                            rechnungs_adresse += str(self.rg_nummer)
                        if self.rg_nummer_zu:
                            rechnungs_adresse += self.rg_nummer_zu
                        rechnungs_adresse += "<br>"
                        rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
                    else:
                        # Postfach
                        rechnungs_adresse += self.anrede_c + " "
                        rechnungs_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
                        rechnungs_adresse += "Postfach "
                        if self.rg_postfach_nummer > 0:
                            rechnungs_adresse += str(self.rg_postfach_nummer)
                        rechnungs_adresse += "<br>"
                        rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
                else:
                    # Unternehmen
                    if self.rg_postfach != 1:
                        # kein Postfach
                        rechnungs_adresse += self.firma + "<br>"
                        if self.zusatz_firma:
                            rechnungs_adresse += self.zusatz_firma + "<br>"
                        rechnungs_adresse += self.anrede_c + " "
                        rechnungs_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
                        if self.rg_zusatz_adresse:
                            rechnungs_adresse += self.rg_zusatz_adresse + "<br>"
                        rechnungs_adresse += self.rg_strasse + " "
                        if self.nummer:
                            rechnungs_adresse += str(self.rg_nummer)
                        if self.rg_nummer_zu:
                            rechnungs_adresse += self.rg_nummer_zu
                        rechnungs_adresse += "<br>"
                        rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
                    else:
                        # Postfach
                        rechnungs_adresse += self.firma + "<br>"
                        if self.zusatz_firma:
                            rechnungs_adresse += self.zusatz_firma + "<br>"
                        rechnungs_adresse += self.anrede_c + " "
                        rechnungs_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
                        rechnungs_adresse += "Postfach "
                        if self.rg_postfach_nummer > 0:
                            rechnungs_adresse += str(self.rg_postfach_nummer)
                        rechnungs_adresse += "<br>"
                        rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
        else:
            rechnungs_adresse = False
            
        # Solidaritäts Adresse
        if self.hat_solidarmitglied:
            soli_adresse = ''
            soli_adresse += self.anrede_2 + " " + self.vorname_2 + " " + self.nachname_2 + "<br>"
            if self.postfach != 1:
                # kein Postfach
                if self.zusatz_adresse:
                    soli_adresse += self.zusatz_adresse + "<br>"
                soli_adresse += self.strasse + " "
                if self.nummer:
                    soli_adresse += str(self.nummer)
                if self.nummer_zu:
                    soli_adresse += self.nummer_zu
                soli_adresse += "<br>"
                soli_adresse += str(self.plz) + " " + self.ort
            else:
                # Postfach
                if self.objekt_zusatz_adresse:
                    soli_adresse += self.objekt_zusatz_adresse + "<br>"
                soli_adresse += self.objekt_strasse
                if self.objekt_hausnummer:
                    soli_adresse += " " + str(self.objekt_hausnummer)
                if self.objekt_nummer_zu:
                    soli_adresse += self.objekt_nummer_zu
                soli_adresse += "<br>"
                soli_adresse += str(self.objekt_plz) + " " + self.objekt_ort
        else:
            soli_adresse = False
            
        return {
                'korrespondenz_adresse': korrespondenz_adresse,
                'objekt_adresse': objekt_adresse,
                'rechnungs_adresse': rechnungs_adresse,
                'soli_adresse': soli_adresse
            }
    except:
        return {}

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
