# -*- coding: utf-8 -*-
# Copyright (c) 2022-2024, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
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
def lese_camt_file(camt_import, file_path, einlesen, matchen, verbuchen):
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
        'verbuchen': verbuchen
    }
    enqueue("mvd.mvd.doctype.camt_import.camt_import.verarbeite_camt_file", queue='long', job_name='Verarbeite CAMT Import {0}'.format(camt_import), timeout=5000, **args)

def verarbeite_camt_file(camt_file, camt_import, einlesen, matchen, verbuchen):
    # lese und prüfe camt file
    camt_file = get_camt_file(camt_file)
    
    if int(einlesen) == 1:
        try:
            zahlungen_einlesen(camt_file, camt_import)
            # Aktualisiere CAMT Übersicht
            aktualisiere_camt_uebersicht(camt_import)
            camt_status_update(camt_import, 'Zahlungen eingelesen')
        except Exception as err:
            camt_status_update(camt_import, 'Failed')
            frappe.log_error("{0}".format(err), 'CAMT-Import {0} failed in einlesen'.format(camt_import))
    
    if int(matchen) == 1:
        # Matchen von Zahlungen
        try:
            zahlungen_matchen(camt_import)
            # Aktualisiere CAMT Übersicht
            aktualisiere_camt_uebersicht(camt_import)
            camt_status_update(camt_import, 'Zahlungen zugeordnet')
        except Exception as err:
            camt_status_update(camt_import, 'Failed')
            frappe.log_error("{0}".format(err), 'CAMT-Import {0} failed in just_match'.format(camt_import))
    
    if  int(verbuchen) == 1:
        # Verbuche Matches
        try:
            verbuche_matches(camt_import)
        except Exception as err:
            camt_status_update(camt_import, 'Failed')
            frappe.log_error("{0}".format(err), 'CAMT-Import {0} failed in verbuchen'.format(camt_import))
        
        # Aktualisiere CAMT Übersicht
        aktualisiere_camt_uebersicht(camt_import)