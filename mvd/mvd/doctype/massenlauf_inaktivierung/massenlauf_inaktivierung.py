# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import now

class MassenlaufInaktivierung(Document):
    def before_save(self):
        if not self.mitgliedschaften:
            open_invoices = frappe.db.sql("""SELECT
                                                `mv_mitgliedschaft`
                                            FROM `tabSales Invoice`
                                            WHERE `outstanding_amount` > 0
                                            AND `docstatus` = 1
                                            AND `sektion_id` = '{sektion}'
                                            AND `ist_mitgliedschaftsrechnung` = 1
                                            AND `status` = 'Overdue'
                                            AND `mv_mitgliedschaft` IN (
                                                SELECT `name` FROM `tabMitgliedschaft` WHERE `status_c` = 'Regulär'
                                            )""".format(sektion=self.sektion_id), as_dict=True)
            for mitgliedschaft in open_invoices:
                ms = frappe.db.sql("""SELECT
                                        `vorname_1`,
                                        `nachname_1`,
                                        `firma`,
                                        `mitglied_nr`
                                    FROM `tabMitgliedschaft`
                                    WHERE `name` = '{ms}'""".format(ms=mitgliedschaft.mv_mitgliedschaft), as_dict=True)[0]
                
                row = self.append('mitgliedschaften', {})
                row.mv_mitgliedschaft = mitgliedschaft.mv_mitgliedschaft
                row.vorname = ms.vorname_1
                row.nachname = ms.nachname_1
                row.mitglied_nr = ms.mitglied_nr
                row.firma = ms.firma

def start_massenlauf_inaktivierung():
    mi_laeufe = frappe.db.sql("""SELECT `name` FROM `tabMassenlauf Inaktivierung` WHERE `docstatus` = 1 AND `status` = 'Vorgemerkt'""", as_dict=True)
    for mi_lauf in mi_laeufe:
        mi = frappe.get_doc("Massenlauf Inaktivierung", mi_lauf.name)
        for mitgliedschaft in mi.mitgliedschaften:
            ms = frappe.get_doc("Mitgliedschaft", mitgliedschaft.mv_mitgliedschaft)
            
            change_log_row = ms.append('status_change', {})
            change_log_row.datum = now()
            change_log_row.status_alt = ms.status_c
            change_log_row.status_neu = 'Ausschluss'
            change_log_row.grund = mi.grund
            
            ms.austritt = mi.ausschluss
            ms.status_c = 'Ausschluss'
            alte_infos = ms.wichtig
            neue_infos = "Ausschluss:\n" + mi.grund + "\n\n"
            neue_infos = neue_infos + alte_infos
            ms.wichtig = neue_infos
            ms.adressen_gesperrt = 1
            ms.save()
            ms.add_comment('Comment', text='Ausschluss vollzogen')
        mi.status = 'Abgeschlossen'
        mi.save()
