# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Druckvorlage(Document):
    def validate(self):
        if not self.deaktiviert:
            self.validiere_inhalt()
            self.set_validierungsstring()
            self.check_default()
        else:
            self.default = '0'
    
    def validiere_inhalt(self):
        if self.dokument in ('Anmeldung mit EZ', 'Interessent*Innenbrief mit EZ', 'Zuzug mit EZ'):
            if self.mitgliedtyp_c == 'Privat':
                if self.anzahl_seiten == '1':
                    frappe.throw("Es müssen mindestens 2 Seiten aktiviert werden (Mitgliedschaftsrechnung & HV Rechnung)")
                
                if self.anzahl_seiten == '2':
                    if self.seite_1_qrr == 'Keiner' or self.seite_2_qrr == 'Keiner':
                        frappe.throw("Bei 2 Seiten muss sowohl der Mitgliedschafts QRR wie auch der HV QRR ausgewählt werden.")
                    if self.seite_1_qrr == self.seite_2_qrr:
                        frappe.throw("Es kann nicht derselbe QRR Typ für Seite 1 wie auch Seite 2 gewählt werden.")
                
                if self.anzahl_seiten == '3':
                    self.seite_1_qrr = 'Keiner'
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
            
            if ausweis_druck > 0:
                if self.doppelseitiger_druck != 1:
                    frappe.throw("Aufgrund des Ausweises muss diese Druckvorlage doppelseitig sein.")
                if self.seite_1_ausweis:
                    if not self.seite_1_referenzblock_ausblenden:
                        frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                if self.seite_2_ausweis:
                    if self.anzahl_seiten != '1':
                        if not self.seite_2_referenzblock_ausblenden:
                            if not self.seite_2_adressblock_ausblenden:
                                frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                if self.seite_3_ausweis:
                   if self.anzahl_seiten == '3':
                        if not self.seite_3_referenzblock_ausblenden:
                            if not self.seite_3_adressblock_ausblenden:
                                frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                                
        elif self.dokument == 'Zuzug ohne EZ':
            ausweis_druck = 0
            if self.seite_1_ausweis:
                ausweis_druck += 1
            if self.seite_2_ausweis:
                ausweis_druck += 1
            if self.seite_3_ausweis:
                ausweis_druck += 1
            
            if ausweis_druck > 0:
                if self.doppelseitiger_druck != 1:
                    frappe.throw("Aufgrund des Ausweises muss diese Druckvorlage doppelseitig sein.")
                if self.seite_1_ausweis:
                    if not self.seite_1_referenzblock_ausblenden:
                        frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                if self.seite_2_ausweis:
                    if self.anzahl_seiten != '1':
                        if not self.seite_2_referenzblock_ausblenden:
                            if not self.seite_2_adressblock_ausblenden:
                                frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                if self.seite_3_ausweis:
                   if self.anzahl_seiten == '3':
                        if not self.seite_3_referenzblock_ausblenden:
                            if not self.seite_3_adressblock_ausblenden:
                                frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                
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
        elif self.dokument == 'Korrespondenz':
            ausweis_druck = 0
            if self.seite_1_ausweis:
                ausweis_druck += 1
            if self.seite_2_ausweis:
                ausweis_druck += 1
            if self.seite_3_ausweis:
                ausweis_druck += 1
            if ausweis_druck > 0:
                if self.doppelseitiger_druck != 1:
                    frappe.throw("Aufgrund des Ausweises muss diese Druckvorlage doppelseitig sein.")
                if self.seite_1_ausweis:
                    if not self.seite_1_referenzblock_ausblenden:
                        frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                if self.seite_2_ausweis:
                    if self.anzahl_seiten != '1':
                        if not self.seite_2_referenzblock_ausblenden:
                            if not self.seite_2_adressblock_ausblenden:
                                frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                if self.seite_3_ausweis:
                   if self.anzahl_seiten == '3':
                        if not self.seite_3_referenzblock_ausblenden:
                            if not self.seite_3_adressblock_ausblenden:
                                frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                
    
    def set_validierungsstring(self):
        if self.dokument != 'Geschenkmitgliedschaft':
            validierungsstring = ''
            validierungsstring += self.sektion_id + "-"
            validierungsstring += self.language + "-"
            validierungsstring += self.dokument + "-"
            validierungsstring += self.mitgliedtyp_c + "-"
            validierungsstring += str(self.reduzierte_mitgliedschaft)
        else:
            validierungsstring = ''
            validierungsstring += self.sektion_id + "-"
            validierungsstring += self.language + "-"
            validierungsstring += self.dokument + "-"
            validierungsstring += self.geschenkmitgliedschaft_dok_empfaenger
        
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

@frappe.whitelist()
def get_druckvorlagen(sektion, dokument='Korrespondenz', mitgliedtyp=False, reduzierte_mitgliedschaft=False, language=False, serienbrief=False):
    if not serienbrief:
        additional_filters = ''
        if mitgliedtyp:
            additional_filters += """ AND `mitgliedtyp_c` = '{mitgliedtyp}'""".format(mitgliedtyp=mitgliedtyp)
        if language:
            additional_filters += """ AND `language` = '{language}'""".format(language=language)
        
        _alle_druckvorlagen = frappe.db.sql("""SELECT
                                                `name`,
                                                `default`
                                            FROM `tabDruckvorlage`
                                            WHERE `sektion_id` = '{sektion}'
                                            AND `deaktiviert` != 1
                                            AND `dokument` = '{dokument}'
                                            {additional_filters}""".format(sektion=sektion, dokument=dokument, additional_filters=additional_filters), as_dict=True)
        
        alle_druckvorlagen = []
        default_druckvorlage = ''
        for druckvorlage in _alle_druckvorlagen:
            if int(druckvorlage.default) == 1:
                default_druckvorlage = druckvorlage.name
            alle_druckvorlagen.append(druckvorlage.name)
        
        return {
            'alle_druckvorlagen': alle_druckvorlagen,
            'default_druckvorlage': default_druckvorlage
        }
    else:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", sektion)
        sektion = mitgliedschaft.sektion_id
        druckvorlagen = frappe.db.sql("""SELECT
                                                `name`
                                            FROM `tabDruckvorlage`
                                            WHERE `sektion_id` = '{sektion}'
                                            AND `deaktiviert` != 1
                                            AND `dokument` = '{dokument}'""".format(sektion=sektion, dokument=dokument), as_dict=True)
        
        alle_druckvorlagen = []
        for druckvorlage in druckvorlagen:
            alle_druckvorlagen.append(druckvorlage.name)
        
        return alle_druckvorlagen

def replace_mv_keywords(txt, mitgliedschaft, mahnung=False, idx=False, sinv=False, fr=False):
    try:
        mitgliedschaft.name
    except:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    
    key_words = [
        {'key_word': '%%ANREDE%%', 'value': mitgliedschaft.briefanrede},
        {'key_word': '%%MIETGLIEDERNUMMER%%', 'value': mitgliedschaft.mitglied_nr},
        {'key_word': '%%ANREDE BESCHENKTE%%', 'value': mitgliedschaft.briefanrede},
        {'key_word': '%%ANREDE SCHENKENDE%%', 'value': mitgliedschaft.rg_briefanrede},
        {'key_word': '%%VOR- NACHNAME BESCHENKTE%%', 'value': " ".join((mitgliedschaft.vorname_1 or '', mitgliedschaft.nachname_1 or ''))},
        {'key_word': '%%VOR- NACHNAME SCHENKENDE%%', 'value': " ".join((mitgliedschaft.rg_vorname or '', mitgliedschaft.rg_nachname or ''))}
    ]
    
    if sinv or fr:
        if sinv:
            sinv = frappe.get_doc("Sales Invoice", sinv)
            amount = sinv.outstanding_amount
        if fr:
            fr = frappe.get_doc("Fakultative Rechnung", fr)
            amount = fr.betrag
        key_words.append({
            'key_word': '%%RECHNUNGSBETRAG%%', 'value': "{:,.2f}".format(amount).replace(",", "'")
        })
    
    if mahnung:
        mahnung = frappe.get_doc("Mahnung", mahnung)
        key_words.append({
            'key_word': '%%Gesamtbetrag_gemahnte_Rechnungen%%', 'value': "{:,.2f}".format(mahnung.total_with_charge).replace(",", "'")
        })
        if mahnung.sales_invoices[idx].ist_mitgliedschaftsrechnung:
            if mahnung.sales_invoices[idx].amount == mahnung.sales_invoices[idx].outstanding_amount:
                key_words.append({
                    'key_word': '%%Jahresrechnung_Jahr%%', 'value': 'Jahresrechnung ' + str(mahnung.sales_invoices[idx].mitgliedschafts_jahr)
                })
            else:
                key_words.append({
                    'key_word': '%%Jahresrechnung_Jahr%%', 'value': 'Jahresrechnung ' + str(mahnung.sales_invoices[idx].mitgliedschafts_jahr) + ' (Restbetrag)'
                })
        else:
            if mahnung.sales_invoices[idx].amount == mahnung.sales_invoices[idx].outstanding_amount:
                key_words.append({
                    'key_word': '%%Jahresrechnung_Jahr%%', 'value': 'Rechnung vom ' + frappe.utils.get_datetime(mahnung.sales_invoices[idx].posting_date).strftime('%d.%m.%Y')
                })
            else:
                key_words.append({
                    'key_word': '%%Jahresrechnung_Jahr%%', 'value': 'Rechnung vom ' + frappe.utils.get_datetime(mahnung.sales_invoices[idx].posting_date).strftime('%d.%m.%Y') + ' (Restbetrag)'
                })
    for key_word in key_words:
        txt = txt.replace(key_word['key_word'], key_word['value'])
    
    return txt
