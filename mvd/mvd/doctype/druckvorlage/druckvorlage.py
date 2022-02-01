# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Druckvorlage(Document):
    def validate(self):
        self.validiere_inhalt()
        self.set_validierungsstring()
        self.check_default()
    
    def validiere_inhalt(self):
        if self.dokument in ('Beitritt mit EZ', 'Interessent*Innenbrief mit EZ'):
            if self.mitgliedtyp_c == 'Privat':
                if self.anzahl_seiten == '1':
                    frappe.throw("Es müssen mindestens 2 Seiten aktiviert werden (Mitgliedschaftsrechnung & HV Rechnung)")
                
                if self.anzahl_seiten == '2':
                    if self.seite_1_qrr == 'Keiner' or self.seite_2_qrr == 'Keiner':
                        frappe.throw("Bei 2 Seiten muss sowohl der Mitgliedschafts QRR wie auch der HV QRR ausgewählt werden.")
                    if self.seite_1_qrr == self.seite_2_qrr:
                        frappe.throw("Es kann nicht derselbe QRR Typ für Seite 1 wie auch Seite 2 gewählt werden.")
                
                if self.anzahl_seiten == '3':
                    if self.seite_2_qrr == self.seite_3_qrr:
                        frappe.throw("Es kann nicht derselbe QRR Typ für Seite 2 wie auch Seite 3 gewählt werden.")
                
                mitgliedschaft = False
                hv = False
                if self.anzahl_seiten == '2':
                    if self.seite_1_qrr == 'Mitgliedschaft':
                        mitgliedschaft = True
                    if self.seite_1_qrr == 'HV':
                        hv = True
                    if self.seite_2_qrr == 'Mitgliedschaft':
                        mitgliedschaft = True
                    if self.seite_2_qrr == 'HV':
                        hv = True
                else:
                    if self.seite_2_qrr == 'Mitgliedschaft':
                        mitgliedschaft = True
                    if self.seite_2_qrr == 'HV':
                        hv = True
                    if self.seite_3_qrr == 'Mitgliedschaft':
                        mitgliedschaft = True
                    if self.seite_3_qrr == 'HV':
                        hv = True
                if not mitgliedschaft:
                    frappe.throw("Bitte wählen Sie als QRR Typ exakt einmal Mitgliedschaft aus.")
                if not hv:
                    frappe.throw("Bitte wählen Sie als QRR Typ exakt einmal HV aus.")
            elif self.mitgliedtyp_c == 'Geschäft':
                mitgliedschaft = 0
                hv = 0
                if self.anzahl_seiten == '1':
                    if self.seite_1_qrr == 'Mitgliedschaft':
                        mitgliedschaft += 1
                    if self.seite_1_qrr == 'HV':
                        hv += 1
                elif self.anzahl_seiten == '2':
                    if self.seite_1_qrr == 'Mitgliedschaft':
                        mitgliedschaft += 1
                    if self.seite_1_qrr == 'HV':
                        hv += 1
                    if self.seite_2_qrr == 'Mitgliedschaft':
                        mitgliedschaft += 1
                    if self.seite_2_qrr == 'HV':
                        hv += 1
                else:
                    if self.seite_2_qrr == 'Mitgliedschaft':
                        mitgliedschaft += 1
                    if self.seite_2_qrr == 'HV':
                        hv += 1
                    if self.seite_3_qrr == 'Mitgliedschaft':
                        mitgliedschaft += 1
                    if self.seite_3_qrr == 'HV':
                        hv += 1
                if mitgliedschaft != 1:
                    frappe.throw("Bitte wählen Sie als QRR Typ exakt einmal Mitgliedschaft aus.")
                if hv > 0:
                    frappe.throw("Der QRR Typ HV darf in Kombination mit Mitgliedtyp Geschäft nicht gewählt werden.")
                
        elif self.dokument == 'Begrüssung mit Ausweis':
            if self.doppelseitiger_druck != 1:
                frappe.throw("Aufgrund des Ausweises muss diese Druckvorlage doppelseitig sein.")
            
            ausweis_druck = 0
            if self.seite_1_ausweis:
                ausweis_druck += 1
            if self.seite_2_ausweis:
                ausweis_druck += 1
            if self.seite_3_ausweis:
                ausweis_druck += 1
            if ausweis_druck == 0:
                frappe.throw("Bitte mindestens eine Seite zum Andruck des Ausweises auswählen.")
            elif ausweis_druck > 1:
                frappe.throw("Bitte maximal eine Seite zum Andruck des Ausweises auswählen.")
                
        elif self.dokument in ('HV mit EZ', 'Spende mit EZ'):
            qrr_druck = 0
            if self.seite_1_qrr_spende_hv:
                qrr_druck += 1
            if self.seite_2_qrr_spende_hv:
                qrr_druck += 1
            if self.seite_3_qrr_spende_hv:
                qrr_druck += 1
            if qrr_druck == 0:
                frappe.throw("Bitte mindestens eine Seite zum Andruck des QRR Zahlteils auswählen.")
            elif qrr_druck > 1:
                frappe.throw("Bitte maximal eine Seite zum Andruck des QRR Zahlteils auswählen.")
    
    def set_validierungsstring(self):
        validierungsstring = ''
        validierungsstring += self.sektion_id + "-"
        validierungsstring += self.dokument + "-"
        validierungsstring += self.mitgliedtyp_c + "-"
        validierungsstring += str(self.reduzierte_mitgliedschaft)
        
        self.validierungsstring = validierungsstring
    
    def check_default(self):
        anz_defaults = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabDruckvorlage` WHERE `validierungsstring` = '{validierungsstring}' AND `default` = 1 AND `name` != '{name}'""".format(validierungsstring=self.validierungsstring, name=self.name), as_dict=True)[0].qty
        if anz_defaults > 0:
            if self.default == 1:
                defaults = frappe.db.sql("""SELECT `name` FROM `tabDruckvorlage` WHERE `validierungsstring` = '{validierungsstring}' AND `default` = 1 AND `name` != '{name}'""".format(validierungsstring=self.validierungsstring, name=self.name), as_dict=True)
                for default in defaults:
                    frappe.db.sql("""UPDATE `tabDruckvorlage` SET `default` = 0 WHERE `name` = '{name}'""".format(name=default.name), as_list=True)
        else:
            if self.default != 1:
                self.default = 1
