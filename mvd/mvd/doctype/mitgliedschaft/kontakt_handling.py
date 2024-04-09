# -*- coding: utf-8 -*-
# Copyright (c) 2021-2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def create_kontakt(mitgliedschaft, primary):
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
        # if not  mitgliedschaft.nachname_2 and not mitgliedschaft.vorname_2:
        #     # Weder Vor- noch Nachname, Anlage Solidarmitglied abgebrochen
        #     return ''
        
        sektion = mitgliedschaft.sektion_id
        is_primary_contact = 0
        company_name = ''
        salutation = mitgliedschaft.anrede_2
        first_name = mitgliedschaft.vorname_2 or mitgliedschaft.nachname_2 or 'n/a'
        if first_name != mitgliedschaft.nachname_2:
            last_name = mitgliedschaft.nachname_2 or 'n/a'
        else:
            last_name = ''
    
    # company fallback
    if not first_name:
        if mitgliedschaft.firma and not mitgliedschaft.nachname_1 and not mitgliedschaft.vorname_1:
            first_name = mitgliedschaft.firma
            frappe.log_error("{0}\n---\n{1}".format('fallback: first_name was " "', mitgliedschaft.as_json()), 'create_kontakt_mitglied')
    
    new_contact = frappe.new_doc('Contact')
    new_contact.first_name = first_name
    new_contact.last_name = last_name
    new_contact.salutation = salutation
    new_contact.sektion = sektion
    new_contact.company_name = company_name
    new_contact.is_primary_contact = is_primary_contact
    
    link = new_contact.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied

    new_contact.insert(ignore_permissions=True)
    
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
    
    new_contact.save(ignore_permissions=True)
    frappe.db.commit()

    new_name = ""
    for link in new_contact.links:
        new_name = link.link_name.strip()
        break
    if primary:
        new_name += "-Mitglied"
    else:
        new_name += "-Solidarmitglied"
    frappe.rename_doc('Contact', new_contact.name, new_name)
    frappe.db.commit()
    
    return new_name

def update_kontakt(mitgliedschaft, primary):
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
        first_name = mitgliedschaft.vorname_2 or mitgliedschaft.nachname_2 or 'n/a'
        if first_name != mitgliedschaft.nachname_2:
            last_name = mitgliedschaft.nachname_2 or 'n/a'
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
        contact.phone = ''
        contact.mobile_no = ''
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
        contact.phone = ''
        contact.mobile_no = ''
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
    frappe.db.commit()

    contact_name = contact.name
    # Aktuell aufgrund #892 deaktiviert. Wird im Anschluss durch #886 wieder aktiviert.
    # ---
    # if '-Mitglied' not in contact.name or '-Solidarmitglied' not in contact.name:
    #     contact_name = rename_contact(contact_name, primary)
    #---
    
    return contact_name

def rename_contact(contact_name, primary):
    contact = frappe.get_doc("Contact", contact_name)
    new_name = ""
    for link in contact.links:
        new_name = link.link_name.strip()
        break
    if primary:
        new_name += "-Mitglied"
    else:
        new_name += "-Solidarmitglied"
    
    if contact.name != new_name:
        frappe.rename_doc('Contact', contact.name, new_name)
        frappe.db.commit()
    return new_name

'''
Nur für Migrationszwecke
bench --site [site] execute mvd.mvd.doctype.mitgliedschaft.kontakt_handling.initial_rename_contacts
Wird anfänglich einmal pro Nacht ausgeführt
'''
def initial_rename_contacts(sql_limit=1000):
    haupt_kontakte = frappe.db.sql("""
                                    SELECT
                                        `kontakt_mitglied` AS `contact`
                                    FROM `tabMitgliedschaft`
                                    WHERE `kontakt_mitglied` NOT LIKE '%-Mitglied'
                                    AND `status_c` != 'Inaktiv'
                                    LIMIT {sql_limit}
                                   """.format(sql_limit=sql_limit), as_dict=True)
    total = len(haupt_kontakte)
    loop = 1
    commit_count = 1
    for haupt_kontakt in haupt_kontakte:
        print("{0} of {1}".format(loop, total))
        try:
            contact = frappe.get_doc("Contact", haupt_kontakt.contact)
            new_name = ""
            for link in contact.links:
                new_name = link.link_name.strip()
                break
            new_name += "-Mitglied"
            print("{0} >>> {1}".format(contact.name, new_name))
            frappe.rename_doc('Contact', contact.name, new_name)
            if commit_count == 10:
                frappe.db.commit()
                commit_count = 0
            else:
                commit_count += 1
            loop += 1
        except Exception as err:
            pass
    frappe.db.commit()