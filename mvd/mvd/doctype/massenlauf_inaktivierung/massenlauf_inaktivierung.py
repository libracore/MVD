# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import now, getdate
from frappe.utils.background_jobs import enqueue

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
                                                SELECT
                                                    `name`
                                                FROM `tabMitgliedschaft`
                                                WHERE `status_c` = 'Regulär'
                                                AND `kuendigung` IS NULL
                                            )""".format(sektion=self.sektion_id), as_dict=True)
            for mitgliedschaft in open_invoices:
                ms = frappe.db.sql("""SELECT
                                        `vorname_1` AS `vorname`,
                                        `nachname_1` AS `nachname`,
                                        `firma` AS `firma`,
                                        `mitglied_nr`,
                                        `nachname_2`,
                                        `vorname_2`,
                                        `strasse`,
                                        `nummer`,
                                        `plz`,
                                        `ort`,
                                        `eintrittsdatum` AS `eintritt`
                                    FROM `tabMitgliedschaft`
                                    WHERE `name` = '{ms}'""".format(ms=mitgliedschaft.mv_mitgliedschaft), as_dict=True)[0]
                
                row = self.append('mitgliedschaften', {})
                row.mv_mitgliedschaft = mitgliedschaft.mv_mitgliedschaft
                row.vorname = ms.vorname
                row.nachname = ms.nachname
                row.mitglied_nr = ms.mitglied_nr
                row.firma = ms.firma
                row.nachname_2 = ms.nachname_2
                row.vorname_2 = ms.vorname_2
                row.strasse = ms.strasse
                row.nummer = ms.nummer
                row.plz = ms.plz
                row.ort = ms.ort
                row.eintritt = ms.eintritt
    
    def before_submit(self):
        self.status = 'In Arbeit'
        args = {
            'doc': self
        }
        enqueue("mvd.mvd.doctype.massenlauf_inaktivierung.massenlauf_inaktivierung.start_massenlauf_inaktivierung", queue='long', job_name='Massenlauf Inaktivierung {0} {1} ({2})'.format(self.ausschluss, self.sektion_id, self.name), timeout=5000, **args)

def start_massenlauf_inaktivierung(doc):
    try:
        for mitgliedschaft in doc.mitgliedschaften:
            ms = frappe.get_doc("Mitgliedschaft", mitgliedschaft.mv_mitgliedschaft)
            
            if ms.status_c in ('Ausschluss', 'Inaktiv'):
                frappe.throw("Mitgliedschaft {0} ist bereits ausgeschlossen repsektive Inaktiv!".format(ms.mitglied_nr))
            
            change_log_row = ms.append('status_change', {})
            change_log_row.datum = now()
            change_log_row.status_alt = ms.status_c
            change_log_row.status_neu = 'Ausschluss'
            change_log_row.grund = doc.grund
            
            ms.austritt = doc.ausschluss
            ms.status_c = 'Ausschluss'
            alte_infos = ms.wichtig
            neue_infos = "Ausschluss:\n" + doc.grund + "\n\n"
            neue_infos = neue_infos + alte_infos
            ms.wichtig = neue_infos
            ms.adressen_gesperrt = 1
            ms.save()
            ms.add_comment('Comment', text='Ausschluss vollzogen ({0} {1} ({2}))'.format(doc.ausschluss, doc.sektion_id, doc.name))
            
            if int(doc.rg_storno) == 1:
                curr_year = getdate(now()).strftime("%Y")
                sinvs = frappe.db.sql("""SELECT
                                            `name`
                                        FROM `tabSales Invoice`
                                        WHERE `ist_mitgliedschaftsrechnung` = 1
                                        AND `mitgliedschafts_jahr` = '{curr_year}'
                                        AND `docstatus` = 1
                                        AND `mv_mitgliedschaft` = '{mv_mitgliedschaft}'""".format(curr_year=curr_year, mv_mitgliedschaft=ms.name), as_dict=True)
                if len(sinvs) > 0:
                    for sinv in sinvs:
                        sinv_doc = frappe.get_doc("Sales Invoice", sinv.name)
                        sinv_doc.cancel()
                        sinv_doc.add_comment('Comment', text='Storniert aufgrund Ausschluss ({0} {1} ({2}))'.format(doc.ausschluss, doc.sektion_id, doc.name))
        
        doc.reload()
        doc.status = 'Abgeschlossen'
        doc.db_set('status', 'Abgeschlossen', commit=True)
    except Exception as err:
        failed = True
        doc.reload()
        doc.db_set('status', 'Fehlgeschlagen', commit=True)
        doc.add_comment('Comment', text='{0}'.format(str(err)))
