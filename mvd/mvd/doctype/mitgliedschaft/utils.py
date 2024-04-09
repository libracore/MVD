# -*- coding: utf-8 -*-
# Copyright (c) 2021-2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from PyPDF2 import PdfFileWriter
from frappe.utils.data import now
from frappe.utils.pdf import get_file_data_from_writer


@frappe.whitelist()
def create_korrespondenz(mitgliedschaft, titel, druckvorlage=False, massenlauf=False, attach_as_pdf=False, sinv_mitgliedschaftsjahr=False):
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    if druckvorlage == 'keine':
        new_korrespondenz = frappe.get_doc({
            "doctype": "Korrespondenz",
            "mv_mitgliedschaft": mitgliedschaft.name,
            "sektion_id": mitgliedschaft.sektion_id,
            "titel": titel
        })
        new_korrespondenz.insert(ignore_permissions=True)
        frappe.db.commit()
        return new_korrespondenz.name
    else:
        druckvorlage = frappe.get_doc("Druckvorlage", druckvorlage)
        _new_korrespondenz = frappe.copy_doc(druckvorlage)
        _new_korrespondenz.doctype = 'Korrespondenz'
        _new_korrespondenz.sektion_id = mitgliedschaft.sektion_id
        _new_korrespondenz.titel = titel
        
        new_korrespondenz = frappe._dict(_new_korrespondenz.as_dict())
        
        keys_to_remove = [
            'mitgliedtyp_c',
            'validierungsstring',
            'language',
            'reduzierte_mitgliedschaft',
            'dokument',
            'default',
            'deaktiviert',
            'seite_1_qrr',
            'seite_1_qrr_spende_hv',
            'seite_2_qrr',
            'seite_2_qrr_spende_hv',
            'seite_3_qrr',
            'seite_3_qrr_spende_hv',
            'blatt_2_info_mahnung',
            'tipps_mahnung',
            'geschenkmitgliedschaft_dok_empfaenger',
            'tipps_geschenkmitgliedschaft'
        ]
        for key in keys_to_remove:
            try:
                new_korrespondenz.pop(key)
            except:
                pass
        
        new_korrespondenz['mv_mitgliedschaft'] = mitgliedschaft.name
        new_korrespondenz['massenlauf'] = 1 if massenlauf else 0
        
        new_korrespondenz = frappe.get_doc(new_korrespondenz)
        if sinv_mitgliedschaftsjahr:
            bezugsjahr = frappe.db.get_value("Sales Invoice", sinv_mitgliedschaftsjahr, 'mitgliedschafts_jahr')
            new_korrespondenz.mitgliedschafts_jahr_manuell = 1
            new_korrespondenz.mitgliedschafts_jahr = bezugsjahr
        new_korrespondenz.insert(ignore_permissions=True)
        frappe.db.commit()
        
        if attach_as_pdf:
            # add doc signature to allow print
            frappe.form_dict.key = new_korrespondenz.get_signature()
            
            # erstellung Rechnungs PDF
            output = PdfFileWriter()
            output = frappe.get_print("Korrespondenz", new_korrespondenz.name, 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
            
            file_name = "{new_korrespondenz}_{datetime}".format(new_korrespondenz=new_korrespondenz.name, datetime=now().replace(" ", "_"))
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
        return new_korrespondenz.name