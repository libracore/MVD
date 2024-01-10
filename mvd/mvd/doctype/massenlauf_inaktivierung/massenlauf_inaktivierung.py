# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import now, getdate
from frappe.utils.background_jobs import enqueue
from frappe.utils import cint
from mvd.mvd.doctype.retouren.retouren import close_open_retouren

class MassenlaufInaktivierung(Document):
    def before_save(self):
        if not self.mitgliedschaften:
            additional_filters = """"""
            if cint(self.relevantes_mitgliedschaftsjahr) > 0:
                additional_filters += """AND `mitgliedschafts_jahr` = '{0}'""".format(self.relevantes_mitgliedschaftsjahr)
                if cint(self.ausnahme_folgejahr) == 1:
                    if cint(self.ausnahme_jahr) > 0:
                        additional_filters += """AND `mv_mitgliedschaft` NOT IN (
                                                    SELECT
                                                        `name`
                                                    FROM `tabMitgliedschaft`
                                                    WHERE `bezahltes_mitgliedschaftsjahr` = '{0}'
                                                )""".format(self.ausnahme_jahr)
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
                                            )
                                            {additional_filters}""".format(sektion=self.sektion_id, additional_filters=additional_filters), as_dict=True)
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
    errors = []
    try:
        for mitgliedschaft in doc.mitgliedschaften:
            try:
                ms = frappe.get_doc("Mitgliedschaft", mitgliedschaft.mv_mitgliedschaft)
                
                if ms.status_c in ('Ausschluss', 'Inaktiv'):
                    doc.add_comment('Comment', text="Mitgliedschaft {0} ist bereits ausgeschlossen repsektive Inaktiv!".format(ms.mitglied_nr))
                    continue
                
                change_log_row = ms.append('status_change', {})
                change_log_row.datum = now()
                change_log_row.status_alt = ms.status_c
                change_log_row.status_neu = 'Ausschluss'
                change_log_row.grund = doc.grund
                
                ms.austritt = doc.ausschluss
                ms.status_c = 'Ausschluss'
                alte_infos = ms.wichtig
                neue_infos = "Ausschluss:\n" + doc.grund + "\n\n"
                neue_infos = neue_infos + alte_infos or ''
                ms.wichtig = neue_infos
                ms.adressen_gesperrt = 1
                ms.validierung_notwendig = None
                ms.kuendigung_verarbeiten = None
                ms.interessent_innenbrief_mit_ez = None
                ms.anmeldung_mit_ez = None
                ms.zuzug_massendruck = None
                ms.rg_massendruck_vormerkung = None
                ms.begruessung_massendruck = None
                ms.begruessung_via_zahlung = None
                ms.zuzugs_rechnung = None
                ms.zuzug_korrespondenz = None
                ms.kuendigung_druckvorlage = None
                ms.rg_massendruck = None
                ms.begruessung_massendruck_dokument = None
                
                ms.save()
                ms.add_comment('Comment', text='Ausschluss vollzogen ({0} {1} ({2}))'.format(doc.ausschluss, doc.sektion_id, doc.name))

                if cint(doc.m_w_retouren_schliessen) ==1:
                    close_open_retouren(ms.name)
                
                if doc.rg_storno:
                    if cint(doc.rg_storno) == 1:
                        curr_year = getdate(now()).strftime("%Y")
                        
                        # Sales Invoice Storno
                        sinvs = frappe.db.sql("""SELECT
                                                    `name`
                                                FROM `tabSales Invoice`
                                                WHERE `ist_mitgliedschaftsrechnung` = 1
                                                AND `mitgliedschafts_jahr` = '{curr_year}'
                                                AND `docstatus` = 1
                                                AND `mv_mitgliedschaft` = '{mv_mitgliedschaft}'
                                                AND `status` != 'Paid'""".format(curr_year=curr_year, mv_mitgliedschaft=ms.name), as_dict=True)
                        if len(sinvs) > 0:
                            for sinv in sinvs:
                                # check linked mahnung
                                linked_mahnung = frappe.db.sql("""SELECT
                                                                        `parent`
                                                                    FROM `tabMahnung Invoices`
                                                                    WHERE `sales_invoice` = '{sinv}'
                                                                    AND `docstatus` = 1""".format(sinv=sinv.name), as_dict=True)
                                
                                if len(linked_mahnung) > 0:
                                    for mahnung in linked_mahnung:
                                        mahnung_doc = frappe.get_doc("Mahnung", mahnung.parent)
                                        mahnung_doc.cancel()
                                        mahnung_doc.add_comment('Comment', text='Storniert aufgrund Ausschluss ({0} {1} ({2}))'.format(doc.ausschluss, doc.sektion_id, doc.name))
                                
                                sinv_doc = frappe.get_doc("Sales Invoice", sinv.name)
                                sinv_doc.cancel()
                                sinv_doc.add_comment('Comment', text='Storniert aufgrund Ausschluss ({0} {1} ({2}))'.format(doc.ausschluss, doc.sektion_id, doc.name))
                        
                        # Fakultative Rechnung Storno
                        frs = frappe.db.sql("""SELECT
                                                    `name`
                                                FROM `tabFakultative Rechnung`
                                                WHERE `bezugsjahr` = '{curr_year}'
                                                AND `docstatus` = 1
                                                AND `mv_mitgliedschaft` = '{mv_mitgliedschaft}'
                                                AND `status` != 'Paid'""".format(curr_year=curr_year, mv_mitgliedschaft=ms.name), as_dict=True)
                        if len(frs) > 0:
                            for fr in frs:
                                fr_doc = frappe.get_doc("Fakultative Rechnung", fr.name)
                                fr_doc.cancel()
                                fr_doc.add_comment('Comment', text='Storniert aufgrund Ausschluss ({0} {1} ({2}))'.format(doc.ausschluss, doc.sektion_id, doc.name))
            except Exception as error:
                errors.append([mitgliedschaft.mv_mitgliedschaft, str(error)])
        
        doc.reload()
        doc.db_set('status', 'Abgeschlossen', commit=True)
        if len(errors) > 0:
            for e in errors:
                doc.add_comment('Comment', text='Fehlgeschlagen: {0} // {1}'.format(e[0], e[1]))
    except Exception as err:
        failed = True
        doc.reload()
        doc.db_set('status', 'Fehlgeschlagen', commit=True)
        doc.add_comment('Comment', text='{0}'.format(str(err)))
