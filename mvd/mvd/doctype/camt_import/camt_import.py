# -*- coding: utf-8 -*-
# Copyright (c) 2022-2024, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint
from frappe.utils.background_jobs import enqueue
from mvd.mvd.doctype.camt_import.helpers import *
from mvd.mvd.doctype.camt_import.utils import *

class CAMTImport(Document):
    def validate(self):
        if not self.sektion_id:
            sektionen = frappe.db.sql("""SELECT `for_value` FROM `tabUser Permission` WHERE `allow` = 'Sektion' AND `is_default` = 1 AND `user` = '{user}'""".format(user=frappe.session.user), as_dict=True)
            if len(sektionen) > 0:
                self.sektion_id = sektionen[0].for_value
                sektion = frappe.get_doc("Sektion", sektionen[0].for_value)
                self.company = sektion.company
                self.account = sektion.account

@frappe.whitelist()
def lese_camt_file(camt_import, file_path, einlesen, matchen, verbuchen, all_in_one):
    def get_camt_step(einlesen, matchen, verbuchen, all_in_one):
        if cint(all_in_one) == 1:
            return 'All in one'
        if cint(einlesen) == 1:
            return 'Einlesen'
        if cint(matchen) == 1:
            return 'Zuweisen'
        if cint(verbuchen) == 1:
            return 'Verbuchen'
    
    # lese und prüfe camt file
    camt_file = get_camt_file(file_path, test=True)
    if not camt_file:
        camt_status_update(camt_import, 'Failed')
        return
    
    args = {
        'camt_file': file_path,
        'camt_import': camt_import,
        'einlesen': einlesen,
        'matchen': matchen,
        'verbuchen': verbuchen,
        'all_in_one': all_in_one
    }
    sektion = frappe.db.get_value("CAMT Import", camt_import, "sektion_id")
    enqueue("mvd.mvd.doctype.camt_import.camt_import.verarbeite_camt_file", queue='long', job_name='Verarbeite {0} CAMT Import {1} ({2})'.format(sektion, camt_import, get_camt_step(einlesen, matchen, verbuchen, all_in_one)), timeout=5000, **args)

def verarbeite_camt_file(camt_file, camt_import, einlesen, matchen, verbuchen, all_in_one):
    def get_next_step(einlesen, matchen, verbuchen):
        if cint(einlesen) == 1:
            return 0, 1, 0
        if cint(matchen) == 1:
            return 0, 0, 1
        if cint(verbuchen) == 1:
            return 0, 0, 0

    # lese und prüfe camt file
    file_path = camt_file
    camt_file = get_camt_file(camt_file)
    
    if cint(einlesen) == 1:
        try:
            zahlungen_einlesen(camt_file, camt_import)
            # Aktualisiere CAMT Übersicht
            aktualisiere_camt_uebersicht(camt_import)
            camt_status_update(camt_import, 'Zahlungen eingelesen')
        except Exception as err:
            camt_status_update(camt_import, 'Failed')
            frappe.log_error("{0}\n\n{1}".format(err, frappe.get_traceback()), 'CAMT-Import {0} failed in einlesen'.format(camt_import))
            return
    elif cint(matchen) == 1:
        # Matchen von Zahlungen
        try:
            zahlungen_matchen(camt_import)
            # Aktualisiere CAMT Übersicht
            aktualisiere_camt_uebersicht(camt_import)
            camt_status_update(camt_import, 'Zahlungen zugeordnet')
        except Exception as err:
            camt_status_update(camt_import, 'Failed')
            frappe.log_error("{0}\n\n{1}".format(err, frappe.get_traceback()), 'CAMT-Import {0} failed in just_match'.format(camt_import))
            return
    elif  cint(verbuchen) == 1:
        # Verbuche Matches
        try:
            verbuche_matches(camt_import)
            # Aktualisiere CAMT Übersicht
            aktualisiere_camt_uebersicht(camt_import)
        except Exception as err:
            camt_status_update(camt_import, 'Failed')
            frappe.log_error("\n\n{1}".format(err, frappe.get_traceback()), 'CAMT-Import {0} failed in verbuchen'.format(camt_import))
            return
    else:
        # Aktualisiere CAMT Übersicht
        aktualisiere_camt_uebersicht(camt_import)
    
    if cint(all_in_one) == 1:
        try:
            einlesen, matchen, verbuchen = get_next_step(einlesen, matchen, verbuchen)
            if cint(einlesen) != 0 or cint(matchen) != 0 or cint(verbuchen) != 0:
                lese_camt_file(camt_import, file_path, einlesen, matchen, verbuchen, all_in_one)
        except Exception as err:
            camt_status_update(camt_import, 'Failed')
            frappe.log_error("\n\n{1}".format(err, frappe.get_traceback()), 'CAMT-Import {0} failed in All in one'.format(camt_import))
    
    return