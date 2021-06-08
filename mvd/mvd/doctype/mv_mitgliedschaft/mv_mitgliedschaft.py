# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class MVMitgliedschaft(Document):
    pass

@frappe.whitelist()
def get_address_overview(mvd):
    try:
        self = frappe.get_doc("MV Mitgliedschaft", mvd)
        # Korrespondenz Adresse
        korrespondenz_adresse = ''
        if self.kundentyp == 'Einzelperson' and self.postfach != 1:
            # Adressformat (Korrespondenz, Einzelperson, kein Postfach):
            '''
                "Anrede" "Vorname" "Nachname"
                "Adress Zusatz"
                "Strasse" "Nummer" "Nummer Zusatz"
                "PLZ" "Ort"
                "---"
                "Tel P"
                "Tel M"
                "Tel G"
                "Email"
            '''
            korrespondenz_adresse += self.anrede_c + " "
            korrespondenz_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
            if self.zusatz_adresse:
                korrespondenz_adresse += self.zusatz_adresse + "<br>"
            korrespondenz_adresse += self.strasse + " "
            if self.nummer:
                korrespondenz_adresse += str(self.nummer)
            if self.nummer_zu:
                korrespondenz_adresse += self.nummer_zu
            korrespondenz_adresse += "<br>"
            korrespondenz_adresse += str(self.plz) + " " + self.ort
        
        if self.kundentyp == 'Unternehmen' and self.postfach != 1:
            # Adressformat (Korrespondenz, Unternehmen, kein Postfach):
            '''
                "Firma"
                "Firma Zusatz"
                "Anrede" "Vorname" "Nachname"
                "Adress Zusatz"
                "Strasse" "Nummer" "Nummer Zusatz"
                "PLZ" "Ort"
                "---"
                "Tel P"
                "Tel M"
                "Tel G"
                "Email"
            '''
            korrespondenz_adresse += self.firma + "<br>"
            if self.zusatz_firma:
                korrespondenz_adresse += self.zusatz_firma + "<br>"
            korrespondenz_adresse += self.anrede_c + " "
            korrespondenz_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
            if self.zusatz_adresse:
                korrespondenz_adresse += self.zusatz_adresse + "<br>"
            korrespondenz_adresse += self.strasse + " "
            if self.nummer:
                korrespondenz_adresse += str(self.nummer)
            if self.nummer_zu:
                korrespondenz_adresse += self.nummer_zu
            korrespondenz_adresse += "<br>"
            korrespondenz_adresse += str(self.plz) + " " + self.ort
        
        if self.kundentyp == 'Einzelperson' and self.postfach == 1:
            # Adressformat (Korrespondenz, Einzelperson, Postfach):
            '''
                "Anrede" "Vorname" "Nachname"
                "Adress Zusatz"
                "Postfach" "Postfach Nummer"
                "PLZ" "Ort"
                "---"
                "Tel P"
                "Tel M"
                "Tel G"
                "Email"
            '''
            korrespondenz_adresse += self.anrede_c + " "
            korrespondenz_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
            korrespondenz_adresse += "Postfach "
            if self.postfach_nummer > 0:
                korrespondenz_adresse += str(self.postfach_nummer)
            korrespondenz_adresse += "<br>"
            korrespondenz_adresse += str(self.plz) + " " + self.ort
        
        if self.kundentyp == 'Unternehmen' and self.postfach == 1:
            # Adressformat (Korrespondenz, Unternehmen, Postfach):
            '''
                "Firma"
                "Firma Zusatz"
                "Anrede" "Vorname" "Nachname"
                "Adress Zusatz"
                "Postfach" "Postfach Nummer"
                "PLZ" "Ort"
                "---"
                "Tel P"
                "Tel M"
                "Tel G"
                "Email"
            '''
            korrespondenz_adresse += self.firma + "<br>"
            if self.zusatz_firma:
                korrespondenz_adresse += self.zusatz_firma + "<br>"
            korrespondenz_adresse += self.anrede_c + " "
            korrespondenz_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
            korrespondenz_adresse += "Postfach "
            if self.postfach_nummer > 0:
                korrespondenz_adresse += str(self.postfach_nummer)
            korrespondenz_adresse += "<br>"
            korrespondenz_adresse += str(self.plz) + " " + self.ort
            
        # Objekt Adresse
        '''
            "Strasse" "Nummer" "Nummer Zusatz"
            "PLZ" "Ort"
        '''
        if self.postfach != 1:
            objekt_adresse = False
        else:
            if self.objekt_zusatz_adresse:
                objekt_adresse = self.objekt_zusatz_adresse + "<br>"
                objekt_adresse += self.objekt_strasse
            else:
                objekt_adresse = self.objekt_strasse
            if self.objekt_hausnummer:
                objekt_adresse += " " + str(self.objekt_hausnummer)
            if self.objekt_nummer_zu:
                objekt_adresse += self.objekt_nummer_zu
            objekt_adresse += "<br>"
            objekt_adresse += str(self.objekt_plz) + " " + self.objekt_ort
            
            
        # Rechnungsadresse
        if self.abweichende_rechnungsadresse == 1:
            rechnungs_adresse = ''
            if self.unabhaengiger_debitor == 1:
                if self.rg_kundentyp == 'Einzelperson' and self.rg_postfach != 1:
                    # Adressformat (Rechnungsadresse, Einzelperson, kein Postfach):
                    '''
                        "Anrede" "Vorname" "Nachname"
                        "Adress Zusatz"
                        "Strasse" "Nummer" "Nummer Zusatz"
                        "PLZ" "Ort"
                        "---"
                        "Tel P"
                        "Tel M"
                        "Tel G"
                        "Email"
                    '''
                    rechnungs_adresse += self.rg_anrede + " "
                    rechnungs_adresse += self.rg_vorname + " " + self.rg_nachname + "<br>"
                    if self.rg_zusatz_adresse:
                        rechnungs_adresse += self.rg_zusatz_adresse + "<br>"
                    rechnungs_adresse += self.rg_strasse + " "
                    if self.rg_nummer:
                        rechnungs_adresse += str(self.rg_nummer)
                    if self.rg_nummer_zu:
                        rechnungs_adresse += self.rg_nummer_zu
                    rechnungs_adresse += "<br>"
                    rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
                
                if self.rg_kundentyp == 'Unternehmen' and self.rg_postfach != 1:
                    # Adressformat (Rechnungsadresse, Unternehmen, kein Postfach):
                    '''
                        "Firma"
                        "Firma Zusatz"
                        "Anrede" "Vorname" "Nachname"
                        "Adress Zusatz"
                        "Strasse" "Nummer" "Nummer Zusatz"
                        "PLZ" "Ort"
                        "---"
                        "Tel P"
                        "Tel M"
                        "Tel G"
                        "Email"
                    '''
                    rechnungs_adresse += self.rg_firma + "<br>"
                    if self.rg_zusatz_firma:
                        rechnungs_adresse += self.rg_zusatz_firma + "<br>"
                    rechnungs_adresse += self.rg_anrede + " "
                    rechnungs_adresse += self.rg_vorname + " " + self.rg_nachname + "<br>"
                    if self.rg_zusatz_adresse:
                        rechnungs_adresse += self.rg_zusatz_adresse + "<br>"
                    rechnungs_adresse += self.rg_strasse + " "
                    if self.rg_nummer:
                        rechnungs_adresse += str(self.rg_nummer)
                    if self.rg_nummer_zu:
                        rechnungs_adresse += self.rg_nummer_zu
                    rechnungs_adresse += "<br>"
                    rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
                
                if self.rg_kundentyp == 'Einzelperson' and self.rg_postfach == 1:
                    # Adressformat (Rechnungsadresse, Einzelperson, Postfach):
                    '''
                        "Anrede" "Vorname" "Nachname"
                        "Adress Zusatz"
                        "Postfach" "Postfach Nummer"
                        "PLZ" "Ort"
                        "---"
                        "Tel P"
                        "Tel M"
                        "Tel G"
                        "Email"
                    '''
                    rechnungs_adresse += self.rg_anrede + " "
                    rechnungs_adresse += self.rg_vorname + " " + self.rg_nachname + "<br>"
                    rechnungs_adresse += "Postfach "
                    if self.rg_postfach_nummer > 0:
                        rechnungs_adresse += str(self.rg_postfach_nummer)
                    rechnungs_adresse += "<br>"
                    rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
                
                if self.rg_kundentyp == 'Unternehmen' and self.rg_postfach == 1:
                    # Adressformat (Rechnungsadresse, Unternehmen, Postfach):
                    '''
                        "Firma"
                        "Firma Zusatz"
                        "Anrede" "Vorname" "Nachname"
                        "Adress Zusatz"
                        "Postfach" "Postfach Nummer"
                        "PLZ" "Ort"
                        "---"
                        "Tel P"
                        "Tel M"
                        "Tel G"
                        "Email"
                    '''
                    rechnungs_adresse += self.rg_firma + "<br>"
                    if self.rg_zusatz_firma:
                        rechnungs_adresse += self.rg_zusatz_firma + "<br>"
                    rechnungs_adresse += self.rg_anrede + " "
                    rechnungs_adresse += self.rg_vorname + " " + self.rg_nachname + "<br>"
                    rechnungs_adresse += "Postfach "
                    if self.rg_postfach_nummer > 0:
                        rechnungs_adresse += str(self.rg_postfach_nummer)
                    rechnungs_adresse += "<br>"
                    rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
            else:
                if self.kundentyp == 'Einzelperson':
                    # Einzelperson
                    if self.rg_postfach != 1:
                        # kein Postfach
                        rechnungs_adresse += self.anrede_c + " "
                        rechnungs_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
                        if self.rg_zusatz_adresse:
                            rechnungs_adresse += self.rg_zusatz_adresse + "<br>"
                        rechnungs_adresse += self.rg_strasse + " "
                        if self.rg_nummer:
                            rechnungs_adresse += str(self.rg_nummer)
                        if self.rg_nummer_zu:
                            rechnungs_adresse += self.rg_nummer_zu
                        rechnungs_adresse += "<br>"
                        rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
                    else:
                        # Postfach
                        rechnungs_adresse += self.anrede_c + " "
                        rechnungs_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
                        rechnungs_adresse += "Postfach "
                        if self.rg_postfach_nummer > 0:
                            rechnungs_adresse += str(self.rg_postfach_nummer)
                        rechnungs_adresse += "<br>"
                        rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
                else:
                    # Unternehmen
                    if self.rg_postfach != 1:
                        # kein Postfach
                        rechnungs_adresse += self.firma + "<br>"
                        if self.zusatz_firma:
                            rechnungs_adresse += self.zusatz_firma + "<br>"
                        rechnungs_adresse += self.anrede_c + " "
                        rechnungs_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
                        if self.rg_zusatz_adresse:
                            rechnungs_adresse += self.rg_zusatz_adresse + "<br>"
                        rechnungs_adresse += self.rg_strasse + " "
                        if self.nummer:
                            rechnungs_adresse += str(self.rg_nummer)
                        if self.rg_nummer_zu:
                            rechnungs_adresse += self.rg_nummer_zu
                        rechnungs_adresse += "<br>"
                        rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
                    else:
                        # Postfach
                        rechnungs_adresse += self.firma + "<br>"
                        if self.zusatz_firma:
                            rechnungs_adresse += self.zusatz_firma + "<br>"
                        rechnungs_adresse += self.anrede_c + " "
                        rechnungs_adresse += self.vorname_1 + " " + self.nachname_1 + "<br>"
                        rechnungs_adresse += "Postfach "
                        if self.rg_postfach_nummer > 0:
                            rechnungs_adresse += str(self.rg_postfach_nummer)
                        rechnungs_adresse += "<br>"
                        rechnungs_adresse += str(self.rg_plz) + " " + self.rg_ort
        else:
            rechnungs_adresse = False
            
        # Solidaritäts Adresse
        if self.nachname_2:
            soli_adresse = ''
            soli_adresse += self.anrede_2 + " " + self.vorname_2 + " " + self.nachname_2 + "<br>"
            if self.postfach != 1:
                # kein Postfach
                if self.zusatz_adresse:
                    soli_adresse += self.zusatz_adresse + "<br>"
                soli_adresse += self.strasse + " "
                if self.nummer:
                    soli_adresse += str(self.nummer)
                if self.nummer_zu:
                    soli_adresse += self.nummer_zu
                soli_adresse += "<br>"
                soli_adresse += str(self.plz) + " " + self.ort
            else:
                # Postfach
                if self.objekt_zusatz_adresse:
                    soli_adresse += self.objekt_zusatz_adresse + "<br>"
                soli_adresse += self.objekt_strasse
                if self.objekt_hausnummer:
                    soli_adresse += " " + str(self.objekt_hausnummer)
                if self.objekt_nummer_zu:
                    soli_adresse += self.objekt_nummer_zu
                soli_adresse += "<br>"
                soli_adresse += str(self.objekt_plz) + " " + self.objekt_ort
        else:
            soli_adresse = False
            
        return {
                'korrespondenz_adresse': korrespondenz_adresse,
                'objekt_adresse': objekt_adresse,
                'rechnungs_adresse': rechnungs_adresse,
                'soli_adresse': soli_adresse
            }
    except:
        return {}

@frappe.whitelist()
def get_timeline_data(doctype, name):
    '''returns timeline data for the past one year'''
    from frappe.desk.form.load import get_communication_data
    from frappe.utils import add_years, now, add_days, getdate, get_timestamp

    
    out = {}
    fields = 'DATE(`creation`) AS `date`, COUNT(`name`) AS `qty`'
    after = add_years(None, -1).strftime('%Y-%m-%d')
    group_by='GROUP BY DATE(`creation`)'

    # fetch and append data from Version Log
    timeline_items = frappe.db.sql("""SELECT {fields}
        FROM `tabVersion`
        WHERE `ref_doctype` = "{doctype}" AND `docname` = "{name}"
        AND `creation` > '{after}'
        {group_by} ORDER BY `creation` DESC
        """.format(doctype=doctype, name=name, fields=fields,
            group_by=group_by, after=after), as_dict=True)

    for timeline_item in timeline_items:
        timestamp = get_timestamp(timeline_item.date)
        out.update({ timestamp: timeline_item.qty })
    return out
