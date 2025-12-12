# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

class MRJSektionsSelektion(Document):
    def validate(self):
        if self.docstatus == 0:
            if frappe.db.get_value("Mitglied RG Jahreslauf", self.mrj, "status") != "Warte auf Sektions Selektionen":
                frappe.throw("Der übergeordnete Mitglied RG Jahreslauf Prozess wurde bereits gestartet.<br>Leider ist es nicht mehr möglich dazugehörige Sektions Selektionen vorzunehmen.")
            
            mitgliedtyp_filter = ''
            if self.mitgliedtyp_spezifisch:
                mitgliedtyp_filter = "AND `mitgliedtyp_c` = '{0}'".format(self.mitgliedtyp)
            
            language_filter = ''
            if self.sprach_spezifisch:
                language_filter = "AND `language` = '{0}'".format(self.language)
            
            region_filter = ''
            if self.region_spezifisch:
                region_filter = "AND `region` = '{0}'".format(self.region)
            
            digitalrechnung_filter = ''
            if self.digitalrechnung_spezifisch:
                if self.digitalrechnung == 'Ja':
                    digitalrechnung_filter = "AND `digitalrechnung` = 1"
                else:
                    digitalrechnung_filter = "AND `digitalrechnung` != 1"
            
            self.anz_rechnungen = frappe.db.sql("""
                SELECT COUNT(`name`) AS `qty`
                FROM `tabMitgliedschaft`
                WHERE `bezahltes_mitgliedschaftsjahr` < '{jahr}'
                AND `sektion_id` = '{sektion}'
                AND `status_c` IN ('Regulär', 'Zuzug', 'Online-Mutation')
                AND `validierung_notwendig` != 1
                AND (
                    `kuendigung` IS NULL
                    OR
                    `kuendigung` > '{jahr}-01-01'
                )
                {mitgliedtyp_filter}
                {language_filter}
                {region_filter}
                {digitalrechnung_filter}
                AND `name` NOT IN (
                    SELECT `mv_mitgliedschaft`
                    FROM `tabSales Invoice`
                    WHERE `docstatus` = 1
                    AND `sektion_id` = '{sektion}'
                    AND `mitgliedschafts_jahr` = '{jahr}'
                    AND `ist_mitgliedschaftsrechnung` = 1
                )
            """.format(sektion=self.sektion_id, jahr=self.bezugsjahr, mitgliedtyp_filter=mitgliedtyp_filter, \
                    language_filter=language_filter, region_filter=region_filter, digitalrechnung_filter=digitalrechnung_filter), as_dict=True)[0].qty or 0

            
        return
    
    def on_submit(self):
        frappe.db.set_value(self.doctype, self.name, 'status', 'Bereit zur Ausführung')
        
    def on_cancel(self):
        frappe.db.set_value(self.doctype, self.name, 'status', 'Abgebrochen')
    
    # def on_submit(self):
    #     self.status = 'Bereit zur Ausführung'
    
    # def on_cancel(self):
    #     self.status = 'Abgebrochen'
