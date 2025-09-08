# -*- coding: utf-8 -*-
# Copyright (c) 2021-2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from PyPDF2 import PdfFileWriter
import datetime
import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.pdf import get_file_data_from_writer
from frappe.utils.data import getdate, add_days, now, today

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

def get_sektion_id(sektion_c):
    sektionen = frappe.db.sql("""SELECT `name` FROM `tabSektion` WHERE `sektion_c` = '{sektion_c}'""".format(sektion_c=sektion_c), as_dict=True)
    if len(sektionen) > 0:
        return sektionen[0].name
    else:
        return False

def get_status_c(status_c):
    mapper = {
        'Anmeldung': 'Anmeldung',
        'OnlineAnmeldung': 'Online-Anmeldung',
        'OnlineBeitritt': 'Online-Beitritt',
        'OnlineKuendigung': 'Online-Kündigung',
        'Zuzug': 'Zuzug',
        'Regulaer': 'Regulär',
        'Gestorben': 'Gestorben',
        'Kuendigung': 'Kündigung',
        'Wegzug': 'Wegzug',
        'Ausschluss': 'Ausschluss',
        'Inaktiv': 'Inaktiv',
        'InteressentIn': 'Interessent*in'
    }
    if status_c in mapper:
        return mapper[status_c]
    else:
        return False

def get_mitgliedtyp_c(mitgliedtyp_c):
    mapper = {
        'privat': 'Privat',
        'kollektiv': 'Kollektiv',
        'geschaeft': 'Geschäft',
        'Privat': 'Privat',
        'Kollektiv': 'Kollektiv',
        'Geschaeft': 'Geschäft'
    }
    if mitgliedtyp_c.lower() in mapper:
        return mapper[mitgliedtyp_c.lower()]
    else:
        return False

def get_inkl_hv(inkl_hv):
    curr_year = cint(getdate().strftime("%Y"))
    if inkl_hv:
        if cint(inkl_hv) >= curr_year:
            return 1
        else:
            return 0
    else:
        return 0

def get_sprache_abk(language='Deutsch'):
    language = frappe.db.sql("""SELECT `name` AS `lang` FROM `tabLanguage` WHERE `language_name` = '{language}'""".format(language=language), as_dict=True)
    if len(language) > 0:
        return language[0].lang
    else:
        return 'de'

def get_anredekonvention(mitgliedschaft=None, self=None, rg=False):
    if self:
        mitgliedschaft = self
    else:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    
    if mitgliedschaft.doctype == 'Kunden':
        if cint(mitgliedschaft.unabhaengiger_debitor) == 1:
            # Rechnungs Anrede
            if mitgliedschaft.rg_anrede == 'Herr':
                return _('Sehr geehrter Herr {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.rg_nachname)
            elif mitgliedschaft.rg_anrede == 'Frau':
                return _('Sehr geehrte Frau {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.rg_nachname)
            else:
                return _('Guten Tag {vorname} {nachname}', mitgliedschaft.language or 'de').format(vorname=mitgliedschaft.rg_vorname or '', nachname=mitgliedschaft.rg_nachname)
        else:
            if mitgliedschaft.anrede == 'Herr':
                return _('Sehr geehrter Herr {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.nachname)
            elif mitgliedschaft.anrede == 'Frau':
                return _('Sehr geehrte Frau {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.nachname)
            else:
                return _('Guten Tag {vorname} {nachname}', mitgliedschaft.language or 'de').format(vorname=mitgliedschaft.vorname or '', nachname=mitgliedschaft.nachname)
    
    if mitgliedschaft.hat_solidarmitglied and not rg:
        # mit Solidarmitglied
        if mitgliedschaft.anrede_c not in ('Herr', 'Frau') or mitgliedschaft.anrede_2 not in ('Herr', 'Frau'):
            # enthält neutrale Anrede
            if mitgliedschaft.nachname_1 == mitgliedschaft.nachname_2 and mitgliedschaft.vorname_1 == mitgliedschaft.vorname_2:
                # gleiche Namen Fallback
                return _('Guten Tag', mitgliedschaft.language or 'de')
            else:
                return _('Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
        else:
            if mitgliedschaft.anrede_c == mitgliedschaft.anrede_2:
                # selbes Geschlecht
                if mitgliedschaft.nachname_1 == mitgliedschaft.nachname_2:
                    # gleiche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return _('Sehr geehrter Herr {vorname_1} {nachname_1}, sehr geehrter Herr {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return _('Sehr geehrte Frau {vorname_1} {nachname_1}, sehr geehrte Frau {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return _('Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                else:
                    # unterschiedliche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return _('Sehr geehrter Herr {nachname_1}, sehr geehrter Herr {nachname_2}', mitgliedschaft.language or 'de').format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return _('Sehr geehrte Frau {nachname_1}, sehr geehrte Frau {nachname_2}', mitgliedschaft.language or 'de').format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return _('Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
            else:
                # unterschiedliches Geschlecht
                if mitgliedschaft.nachname_1 == mitgliedschaft.nachname_2:
                    # gleiche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return _('Sehr geehrte Herr und Frau {nachname_1}', mitgliedschaft.language or 'de').format(nachname_1=mitgliedschaft.nachname_1)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return _('Sehr geehrte Frau und Herr {nachname_1}', mitgliedschaft.language or 'de').format(nachname_1=mitgliedschaft.nachname_1)
                    else:
                        # Fallback
                        return _('Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                else:
                    # unterschiedliche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return _('Sehr geehrter Herr {nachname_1}, sehr geehrte Frau {nachname_2}', mitgliedschaft.language or 'de').format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return _('Sehr geehrte Frau {nachname_1}, sehr geehrter Herr {nachname_2}', mitgliedschaft.language or 'de').format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return _('Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
        
    else:
        if not rg:
            # ohne Solidarmitglied
            if mitgliedschaft.anrede_c == 'Herr':
                return _('Sehr geehrter Herr {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.nachname_1)
            elif mitgliedschaft.anrede_c == 'Frau':
                return _('Sehr geehrte Frau {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.nachname_1)
            else:
                return _('Guten Tag {vorname} {nachname}', mitgliedschaft.language or 'de').format(vorname=mitgliedschaft.vorname_1 or '', nachname=mitgliedschaft.nachname_1)
        else:
            if cint(mitgliedschaft.unabhaengiger_debitor) == 1:
                # Rechnungs Anrede
                if mitgliedschaft.rg_anrede == 'Herr':
                    return _('Sehr geehrter Herr {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.rg_nachname)
                elif mitgliedschaft.rg_anrede == 'Frau':
                    return _('Sehr geehrte Frau {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.rg_nachname)
                else:
                    return _('Guten Tag {vorname} {nachname}', mitgliedschaft.language or 'de').format(vorname=mitgliedschaft.rg_vorname or '', nachname=mitgliedschaft.rg_nachname)
            else:
                return get_anredekonvention(self=mitgliedschaft)

def get_adressblock(mitgliedschaft):
    adressblock = ''
    
    if mitgliedschaft.doctype == 'Mitgliedschaft':
        if mitgliedschaft.kundentyp == 'Unternehmen':
            if mitgliedschaft.firma:
                adressblock += mitgliedschaft.firma
                adressblock += ' '
            if mitgliedschaft.zusatz_firma:
                adressblock += mitgliedschaft.zusatz_firma
            if mitgliedschaft.firma or mitgliedschaft.zusatz_firma:
                adressblock += '\n'
        
        if mitgliedschaft.vorname_1:
            adressblock += mitgliedschaft.vorname_1
            adressblock += ' '
        if mitgliedschaft.nachname_1:
            adressblock += mitgliedschaft.nachname_1
        if mitgliedschaft.vorname_1 or mitgliedschaft.nachname_1:
            adressblock += '\n'
        
        if mitgliedschaft.hat_solidarmitglied:
            if mitgliedschaft.vorname_2:
                adressblock += mitgliedschaft.vorname_2
                adressblock += ' '
            if mitgliedschaft.nachname_2:
                adressblock += mitgliedschaft.nachname_2
            if  mitgliedschaft.vorname_2 or mitgliedschaft.nachname_2:
                adressblock += '\n'
        
        if mitgliedschaft.zusatz_adresse:
            adressblock += mitgliedschaft.zusatz_adresse
            adressblock += '\n'
        
        if mitgliedschaft.strasse and mitgliedschaft.strasse != '':
            adressblock += mitgliedschaft.strasse
            if mitgliedschaft.nummer:
                adressblock += ' '
                adressblock += str(mitgliedschaft.nummer)
                if mitgliedschaft.nummer_zu:
                    adressblock += str(mitgliedschaft.nummer_zu)
            adressblock += '\n'
        
        if cint(mitgliedschaft.postfach) == 1:
            adressblock += 'Postfach '
            if mitgliedschaft.postfach_nummer:
                adressblock += str(mitgliedschaft.postfach_nummer)
            adressblock += '\n'
        
        if mitgliedschaft.land and mitgliedschaft.land != 'Schweiz':
            laender_code = frappe.get_value("Country", mitgliedschaft.land, "code").upper() + "-"
        else:
            laender_code = ''
        if mitgliedschaft.plz:
            plz = str(mitgliedschaft.plz)
        else:
            plz = ''
        ort = mitgliedschaft.ort or ''
        adressblock += laender_code + plz + ' ' + ort
        
        return adressblock
    else:
        if mitgliedschaft.kundentyp == 'Unternehmen':
            if mitgliedschaft.firma:
                adressblock += mitgliedschaft.firma
                adressblock += '\n'
            if mitgliedschaft.zusatz_firma:
                adressblock += mitgliedschaft.zusatz_firma
                adressblock += '\n'
        
        if mitgliedschaft.vorname:
            adressblock += mitgliedschaft.vorname
            adressblock += ' '
        if mitgliedschaft.nachname:
            adressblock += mitgliedschaft.nachname
        if mitgliedschaft.vorname or mitgliedschaft.nachname:
            adressblock += '\n'
        
        if mitgliedschaft.zusatz_adresse:
            adressblock += mitgliedschaft.zusatz_adresse
            adressblock += '\n'
        
        if mitgliedschaft.strasse:
            adressblock += mitgliedschaft.strasse
            if mitgliedschaft.nummer:
                adressblock += ' '
                adressblock += str(mitgliedschaft.nummer)
                if mitgliedschaft.nummer_zu:
                    adressblock += str(mitgliedschaft.nummer_zu)
            adressblock += '\n'
        
        if cint(mitgliedschaft.postfach) == 1:
            adressblock += 'Postfach '
            if mitgliedschaft.postfach_nummer:
                adressblock += str(mitgliedschaft.postfach_nummer)
            adressblock += '\n'
        
        if mitgliedschaft.land and mitgliedschaft.land != 'Schweiz':
            laender_code = frappe.get_value("Country", mitgliedschaft.land, "code").upper() + "-"
        else:
            laender_code = ''
        if mitgliedschaft.plz:
            plz = str(mitgliedschaft.plz)
        else:
            plz = ''
        ort = mitgliedschaft.ort or ''
        adressblock += laender_code + plz + ' ' + ort
        
        return adressblock

def get_rg_adressblock(mitgliedschaft):
    adressblock = ''
    if mitgliedschaft.doctype == 'Mitgliedschaft':
        if cint(mitgliedschaft.abweichende_rechnungsadresse) != 1:
            return get_adressblock(mitgliedschaft)
        
        if cint(mitgliedschaft.unabhaengiger_debitor) != 1:
            if mitgliedschaft.kundentyp == 'Unternehmen':
                if mitgliedschaft.firma:
                    adressblock += mitgliedschaft.firma
                    adressblock += ' '
                if mitgliedschaft.zusatz_firma:
                    adressblock += mitgliedschaft.zusatz_firma
                if mitgliedschaft.firma or mitgliedschaft.zusatz_firma:
                    adressblock += '\n'
            
            if mitgliedschaft.vorname_1:
                adressblock += mitgliedschaft.vorname_1
                adressblock += ' '
            if mitgliedschaft.nachname_1:
                adressblock += mitgliedschaft.nachname_1
            if mitgliedschaft.vorname_1 or mitgliedschaft.nachname_1:
                adressblock += '\n'
            
            if mitgliedschaft.hat_solidarmitglied:
                if mitgliedschaft.vorname_2:
                    adressblock += mitgliedschaft.vorname_2
                    adressblock += ' '
                if mitgliedschaft.nachname_2:
                    adressblock += mitgliedschaft.nachname_2
                if  mitgliedschaft.vorname_2 or mitgliedschaft.nachname_2:
                    adressblock += '\n'
        else:
            if mitgliedschaft.rg_kundentyp == 'Unternehmen':
                if mitgliedschaft.rg_firma:
                    adressblock += mitgliedschaft.rg_firma
                    adressblock += ' '
                if mitgliedschaft.rg_zusatz_firma:
                    adressblock += mitgliedschaft.rg_zusatz_firma
                if mitgliedschaft.rg_firma or mitgliedschaft.rg_zusatz_firma:
                    adressblock += '\n'
            
            if mitgliedschaft.rg_vorname:
                adressblock += mitgliedschaft.rg_vorname
                adressblock += ' '
            if mitgliedschaft.rg_nachname:
                adressblock += mitgliedschaft.rg_nachname
            if mitgliedschaft.rg_vorname or mitgliedschaft.rg_nachname:
                adressblock += '\n'
        
        if mitgliedschaft.rg_zusatz_adresse:
            adressblock += mitgliedschaft.rg_zusatz_adresse
            adressblock += '\n'
        
        adressblock += mitgliedschaft.rg_strasse or ''
        if mitgliedschaft.rg_nummer:
            adressblock += ' '
            adressblock += str(mitgliedschaft.rg_nummer)
            if mitgliedschaft.rg_nummer_zu:
                adressblock += str(mitgliedschaft.rg_nummer_zu)
        adressblock += '\n'
        
        if cint(mitgliedschaft.rg_postfach) == 1:
            adressblock += 'Postfach '
            if mitgliedschaft.rg_postfach_nummer:
                adressblock += str(mitgliedschaft.rg_postfach_nummer)
            adressblock += '\n'

        if mitgliedschaft.rg_land and mitgliedschaft.rg_land != 'Schweiz':
            laender_code = frappe.get_value("Country", mitgliedschaft.rg_land, "code").upper() + "-"
        else:
            laender_code = ''
        if mitgliedschaft.rg_plz:
            plz = str(mitgliedschaft.rg_plz)
        else:
            plz = ''
        ort = mitgliedschaft.rg_ort or ''
        adressblock += laender_code + plz + ' ' + ort

        return adressblock
    elif mitgliedschaft.doctype == 'Kunden':
        if cint(mitgliedschaft.abweichende_rechnungsadresse) != 1:
            return get_adressblock(mitgliedschaft)
        
        if cint(mitgliedschaft.unabhaengiger_debitor) != 1:
            if mitgliedschaft.kundentyp == 'Unternehmen':
                if mitgliedschaft.firma:
                    adressblock += mitgliedschaft.firma
                    adressblock += ' '
                if mitgliedschaft.zusatz_firma:
                    adressblock += mitgliedschaft.zusatz_firma
                if mitgliedschaft.firma or mitgliedschaft.zusatz_firma:
                    adressblock += '\n'
            
            if mitgliedschaft.vorname:
                adressblock += mitgliedschaft.vorname
                adressblock += ' '
            if mitgliedschaft.nachname:
                adressblock += mitgliedschaft.nachname
            if mitgliedschaft.vorname or mitgliedschaft.nachname:
                adressblock += '\n'
        else:
            if mitgliedschaft.rg_kundentyp == 'Unternehmen':
                if mitgliedschaft.rg_firma:
                    adressblock += mitgliedschaft.rg_firma
                    adressblock += ' '
                if mitgliedschaft.rg_zusatz_firma:
                    adressblock += mitgliedschaft.rg_zusatz_firma
                if mitgliedschaft.rg_firma or mitgliedschaft.rg_zusatz_firma:
                    adressblock += '\n'

            if mitgliedschaft.rg_vorname:
                adressblock += mitgliedschaft.rg_vorname
                adressblock += ' '
            if mitgliedschaft.rg_nachname:
                adressblock += mitgliedschaft.rg_nachname
            if mitgliedschaft.rg_vorname or mitgliedschaft.rg_nachname:
                adressblock += '\n'
        
        if mitgliedschaft.rg_zusatz_adresse:
            adressblock += mitgliedschaft.rg_zusatz_adresse
            adressblock += '\n'
        
        adressblock += mitgliedschaft.rg_strasse or ''
        if mitgliedschaft.rg_nummer:
            adressblock += ' '
            adressblock += str(mitgliedschaft.rg_nummer)
            if mitgliedschaft.rg_nummer_zu:
                adressblock += str(mitgliedschaft.rg_nummer_zu)
        adressblock += '\n'
        
        if cint(mitgliedschaft.rg_postfach) == 1:
            adressblock += 'Postfach '
            if mitgliedschaft.rg_postfach_nummer:
                adressblock += str(mitgliedschaft.rg_postfach_nummer)
            adressblock += '\n'

        if mitgliedschaft.rg_land and mitgliedschaft.rg_land != 'Schweiz':
            laender_code = frappe.get_value("Country", mitgliedschaft.rg_land, "code").upper() + "-"
        else:
            laender_code = ''
        if mitgliedschaft.rg_plz:
            plz = str(mitgliedschaft.rg_plz)
        else:
            plz = ''
        ort = mitgliedschaft.rg_ort or ''
        adressblock += laender_code + plz + ' ' + ort

        return adressblock
    else:
        return 'Fehler!<br>Weder Mitgliedschaft noch Kunde'

def get_ampelfarbe(mitgliedschaft):
    ''' mögliche Ampelfarben:
        - Grün: ampelgruen --> Mitglied kann alle Dienstleistungen beziehen (keine Karenzfristen, keine überfälligen oder offen Rechnungen)
        - Gelb: ampelgelb --> Karenzfristen oder offene Rechnungen
        - Rot: ampelrot --> überfällige offene Rechnungen
        
        MVZH Ausnahme:
        - Grün --> Jahr bezahlt >= aktuelles Jahr
        - Rot --> Jahr bezahlt < aktuelles Jahr
    '''
    
    if mitgliedschaft.status_c in ('Gestorben', 'Wegzug', 'Ausschluss', 'Inaktiv', 'Interessent*in'):
        ampelfarbe = 'ampelrot'
    else:
        
        # MVZH Ausnahme Start
        if mitgliedschaft.sektion_id == 'MVZH':
            if cint(mitgliedschaft.bezahltes_mitgliedschaftsjahr) < cint(datetime.date.today().year):
                return 'ampelrot'
            else:
                return 'ampelgruen'
        # MVZH Ausnahme Ende
        
        ueberfaellige_rechnungen = 0
        offene_rechnungen = 0
        
        sektion = frappe.get_doc("Sektion", mitgliedschaft.sektion_id)
        karenzfrist_in_d = sektion.karenzfrist
        ablauf_karenzfrist = add_days(getdate(mitgliedschaft.eintrittsdatum), karenzfrist_in_d)
        
        if getdate() < ablauf_karenzfrist:
            karenzfrist = False
        else:
            karenzfrist = True
        
        # musste mit v8.5.9 umgeschrieben werden, da negative Werte ebenfalls == True ergeben. (Beispiel: (1 + 2015 - 2023) == True)
        # ~ aktuelles_jahr_bezahlt = bool( 1 + cint(mitgliedschaft.bezahltes_mitgliedschaftsjahr) - cint(now().split("-")[0]) )
        aktuelles_jahr_bezahlt = False if ( 1 + cint(mitgliedschaft.bezahltes_mitgliedschaftsjahr) - cint(now().split("-")[0]) ) <= 0 else True
        
        if not aktuelles_jahr_bezahlt:
            ueberfaellige_rechnungen = frappe.db.sql("""SELECT IFNULL(SUM(`outstanding_amount`), 0) AS `open_amount`
                                                        FROM `tabSales Invoice` 
                                                        WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'
                                                        AND `ist_mitgliedschaftsrechnung` = 1
                                                        AND `due_date` < CURDATE()
                                                        AND `docstatus` = 1""".format(mitgliedschaft=mitgliedschaft.name), as_dict=True)[0].open_amount
        else:
            ueberfaellige_rechnungen = 0
        
        if ueberfaellige_rechnungen > 0:
            ampelfarbe = 'ampelrot'
        else:
            if not aktuelles_jahr_bezahlt:
                offene_rechnungen = frappe.db.sql("""SELECT IFNULL(SUM(`outstanding_amount`), 0) AS `open_amount`
                                                    FROM `tabSales Invoice` 
                                                    WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'
                                                    AND `ist_mitgliedschaftsrechnung` = 1
                                                    AND `due_date` >= CURDATE()
                                                    AND `docstatus` = 1""".format(mitgliedschaft=mitgliedschaft.name), as_dict=True)[0].open_amount
            else:
                offene_rechnungen = 0
            
            if offene_rechnungen > 0:
                ampelfarbe = 'ampelgelb'
            else:
                if not karenzfrist:
                    ampelfarbe = 'ampelgelb'
                else:
                    ampelfarbe = 'ampelgruen'
    
    return ampelfarbe

def get_naechstes_jahr_geschuldet(mitglied_id, live_data=False, datum_via_api=False):
    # naechstes_jahr_geschuldet bezieht sich immer auf die Basis=Bezahltes_Mitgliedschaftsjahr!
    if not live_data:
        bezahltes_mitgliedschafsjahr = cint(frappe.db.get_value("Mitgliedschaft", mitglied_id, 'bezahltes_mitgliedschaftsjahr'))
        sektion = frappe.db.get_value("Mitgliedschaft", mitglied_id, 'sektion_id')
    else:
        bezahltes_mitgliedschafsjahr = cint(live_data.bezahltes_mitgliedschaftsjahr)
        sektion = live_data.sektion_id

    current_year = cint(now().split("-")[0])
    stichtag = frappe.db.get_value("Sektion", sektion, 'kuendigungs_stichtag')
    stichtag_datum = getdate("{0}-{1}-{2}".format(current_year, stichtag.strftime("%Y-%m-%d").split("-")[1], stichtag.strftime("%Y-%m-%d").split("-")[2]))

    kuendigungsfrist_verpasst = False
    if getdate(today()) > stichtag_datum:
        kuendigungsfrist_verpasst = True
    
    if datum_via_api:
        if kuendigungsfrist_verpasst:
            return "{0}-{1}".format(current_year + 1, "12-31"), kuendigungsfrist_verpasst
        else:
            return "{0}-{1}".format(current_year, "12-31"), kuendigungsfrist_verpasst

    if current_year > bezahltes_mitgliedschafsjahr:
        return True
    elif current_year < bezahltes_mitgliedschafsjahr:
        return False
    else:
        if kuendigungsfrist_verpasst:
            return True
        else:
            return False

def mahnstopp(mitgliedschaft, mahnstopp):
    SQL_SAFE_UPDATES_false = frappe.db.sql("""SET SQL_SAFE_UPDATES=0""", as_list=True)
    frappe.db.sql("""UPDATE `tabSales Invoice` SET `exclude_from_payment_reminder_until` = '{mahnstopp}' WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'""".format(mitgliedschaft=mitgliedschaft, mahnstopp=mahnstopp), as_list=True)
    SQL_SAFE_UPDATES_true = frappe.db.sql("""SET SQL_SAFE_UPDATES=1""", as_list=True)
    frappe.db.commit()

def sp_updater(mitgliedschaft):
    # sende neuanlage/update an sp wenn letzter bearbeiter nich SP
    if mitgliedschaft.letzte_bearbeitung_von == 'User':
        if mitgliedschaft.creation == mitgliedschaft.modified:
            # sende neuanlage an SP
            send_mvm_to_sp(mitgliedschaft, False)
        else:
            # sende update an SP
            send_mvm_to_sp(mitgliedschaft, True)
            # special case sektionswechsel nach ZH
            if mitgliedschaft.wegzug_zu == 'MVZH' and mitgliedschaft.status_c == 'Wegzug':
                send_mvm_sektionswechsel(mitgliedschaft)

def send_mvm_to_sp(mitgliedschaft, update):
    if str(get_sektion_code(mitgliedschaft.sektion_id)) not in ('ZH', 'M+W-Abo'):
        if not cint(frappe.db.get_single_value('Service Plattform API', 'queue')) == 1:
            from mvd.mvd.service_plattform.api import update_mvm
            prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
            update_status = update_mvm(prepared_mvm, update)
            return update_status
        else:
            create_sp_queue(mitgliedschaft, update)

def send_mvm_sektionswechsel(mitgliedschaft):
    from mvd.mvd.service_plattform.api import sektionswechsel
    prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
    neue_sektion = ''
    if mitgliedschaft.wegzug_zu == 'MVZH':
        neue_sektion = 'ZH'
    sektionswechsel(prepared_mvm, neue_sektion)
    frappe.log_error(str(prepared_mvm), "MVZH Sektionswechsel an SP gesendet")

def get_sektion_code(sektion):
    sektionen = frappe.db.sql("""SELECT `sektion_c` FROM `tabSektion` WHERE `name` = '{sektion}'""".format(sektion=sektion), as_dict=True)
    if len(sektionen) > 0:
        return sektionen[0].sektion_c
    else:
        return False

def prepare_mvm_for_sp(mitgliedschaft):
    adressen = get_adressen_for_sp(mitgliedschaft)
    
    typ_mapper = {
        'Kollektiv': 'Kollektiv',
        'Privat': 'Privat',
        'Geschäft': 'Geschaeft'
    }
    
    status_mapper = {
        'Anmeldung': 'Anmeldung',
        'Online-Anmeldung': 'OnlineAnmeldung',
        'Online-Beitritt': 'OnlineBeitritt',
        'Online-Kündigung': 'OnlineKuendigung',
        'Zuzug': 'Zuzug',
        'Regulär': 'Regulaer',
        'Gestorben': 'Gestorben',
        'Kündigung': 'Kuendigung',
        'Wegzug': 'Wegzug',
        'Ausschluss': 'Ausschluss',
        'Inaktiv': 'Inaktiv',
        'Interessent*in': 'InteressentIn'
    }
    
    kuendigungsgrund = None
    
    if mitgliedschaft.kuendigung:
        kuendigungsgrund = frappe.db.sql("""SELECT
                                                `grund`
                                            FROM `tabStatus Change`
                                            WHERE `status_neu` = 'Regulär &dagger;'
                                            AND `parent` = '{mitgliedschaft}'
                                            ORDER BY `idx` DESC""".format(mitgliedschaft=mitgliedschaft.name), as_dict=True)
        if len(kuendigungsgrund) > 0:
            kuendigungsgrund = kuendigungsgrund[0].grund or None
        else:
            kuendigungsgrund = None
        
    
    # Bei Wegzügen muss gem. SP-API der Key alteSektionCode leer sein
    if mitgliedschaft.status_c == 'Wegzug':
        alteSektionCode = ''
    else:
        alteSektionCode = str(get_sektion_code(mitgliedschaft.zuzug_von)) if mitgliedschaft.zuzug_von else None
    
    prepared_mvm = {
        "mitgliedNummer": str(mitgliedschaft.mitglied_nr).strip() if str(mitgliedschaft.mitglied_nr) != 'MV' else None,
        "mitgliedId": cint(mitgliedschaft.mitglied_id),
        "sektionCode": str(get_sektion_code(mitgliedschaft.sektion_id)).strip(),
        "regionCode": frappe.get_value("Region", mitgliedschaft.region, "region_c") if mitgliedschaft.region else None,
        "regionManuell": True if mitgliedschaft.region_manuell else False,
        "typ": str(typ_mapper[mitgliedschaft.mitgliedtyp_c]),
        "status": str(status_mapper[mitgliedschaft.status_c]) if mitgliedschaft.status_c != 'Online-Mutation' else str(status_mapper[mitgliedschaft.status_vor_onl_mutation]),
        "sprache": get_sprache(language=mitgliedschaft.language) if mitgliedschaft.language else 'Deutsch',
        "istTemporaeresMitglied": False,
        "fuerBewirtschaftungGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
        "erfassungsdatum": str(mitgliedschaft.creation).replace(" ", "T"),
        "eintrittsdatum": str(mitgliedschaft.eintrittsdatum).replace(" ", "T") + "T00:00:00" if mitgliedschaft.eintrittsdatum else None,
        "austrittsdatum": str(mitgliedschaft.austritt).replace(" ", "T") + "T00:00:00" if mitgliedschaft.austritt else None,
        "alteSektionCode": alteSektionCode,
        "zuzugsdatum": str(mitgliedschaft.zuzug).replace(" ", "T") + "T00:00:00" if mitgliedschaft.zuzug else None,
        "neueSektionCode": str(get_sektion_code(mitgliedschaft.wegzug_zu)) if mitgliedschaft.wegzug_zu else None,
        "wegzugsdatum": str(mitgliedschaft.wegzug).replace(" ", "T") + "T00:00:00" if mitgliedschaft.wegzug else None,
        "kuendigungPer": str(mitgliedschaft.kuendigung).replace(" ", "T") + "T00:00:00" if mitgliedschaft.kuendigung else None,
        "jahrBezahltMitgliedschaft": mitgliedschaft.bezahltes_mitgliedschaftsjahr or 0,
        "betragBezahltMitgliedschaft": None,
        "jahrBezahltHaftpflicht": mitgliedschaft.zahlung_hv,
        "betragBezahltHaftpflicht": None,
        "bemerkungen": str(mitgliedschaft.wichtig) if mitgliedschaft.wichtig else None,
        "anzahlZeitungen": cint(mitgliedschaft.m_und_w),
        "zeitungAlsPdf": True if mitgliedschaft.m_und_w_pdf else False,
        "isKollektiv": True if cint(mitgliedschaft.ist_kollektiv) == 1 else False,
        "isGeschenkmitgliedschaft": True if cint(mitgliedschaft.ist_geschenkmitgliedschaft) == 1 else False,
        "isEinmaligeSchenkung": True if cint(mitgliedschaft.ist_einmalige_schenkung) == 1 else False,
        "schenkerHasGeschenkunterlagen": True if cint(mitgliedschaft.geschenkunterlagen_an_schenker) == 1 else False,
        "datumBezahltHaftpflicht": str(mitgliedschaft.datum_hv_zahlung).replace(" ", "T") + "T00:00:00" if mitgliedschaft.datum_hv_zahlung else None,
        "adressen": adressen,
        "onlineHaftpflicht": 1 if mitgliedschaft.online_haftpflicht and mitgliedschaft.online_haftpflicht != '' else 0,
        "onlineGutschrift": mitgliedschaft.online_gutschrift if mitgliedschaft.online_gutschrift and mitgliedschaft.online_gutschrift != '' else None,
        "onlineBetrag": mitgliedschaft.online_betrag if mitgliedschaft.online_betrag and mitgliedschaft.online_betrag != '' else None,
        "datumOnlineVerbucht": mitgliedschaft.datum_online_verbucht if mitgliedschaft.datum_online_verbucht and mitgliedschaft.datum_online_verbucht != '' else None,
        "datumOnlineGutschrift": mitgliedschaft.datum_online_gutschrift if mitgliedschaft.datum_online_gutschrift and mitgliedschaft.datum_online_gutschrift != '' else None,
        "onlinePaymentMethod": mitgliedschaft.online_payment_method if mitgliedschaft.online_payment_method and mitgliedschaft.online_payment_method != '' else None,
        "onlinePaymentId": mitgliedschaft.online_payment_id if mitgliedschaft.online_payment_id and mitgliedschaft.online_payment_id != '' else None,
        "kuendigungsgrund": kuendigungsgrund,
        "mvbTyp":  mitgliedschaft.mvb_typ if mitgliedschaft.mvb_typ and mitgliedschaft.mvb_typ != '' else None,
        "MitgliedHash": mitgliedschaft.mitglied_hash if mitgliedschaft.mitglied_hash else None
    }
    
    return prepared_mvm

def create_sp_queue(mitgliedschaft, update):
    existing_queue = frappe.db.sql("""SELECT COUNT(`name`) as `qty` FROM `tabService Platform Queue` WHERE `status` = 'Open' AND `mv_mitgliedschaft` = '{mitgliedschaft}'""".format(mitgliedschaft=mitgliedschaft.mitglied_id), as_dict=True)[0].qty
    if existing_queue > 0 and update:
        return
    else:
        if mitgliedschaft.status_c not in ('Online-Beitritt', 'Online-Mutation'):
            queue = frappe.get_doc({
                "doctype": "Service Platform Queue",
                "status": "Open",
                "mv_mitgliedschaft": mitgliedschaft.mitglied_id,
                "sektion_id": mitgliedschaft.sektion_id,
                "update": 1 if update else 0
            })
            
            queue.insert(ignore_permissions=True, ignore_links=True)
        
        return

def get_adressen_for_sp(mitgliedschaft):
    adressen = []
    mitglied = {
        "typ": "Mitglied",
        "strasse": str(mitgliedschaft.strasse).strip() if mitgliedschaft.strasse else None,
        "hausnummer": str(mitgliedschaft.nummer).strip() if mitgliedschaft.nummer else None,
        "hausnummerZusatz": str(mitgliedschaft.nummer_zu).strip() if mitgliedschaft.nummer_zu else None,
        "postleitzahl": str(mitgliedschaft.plz).strip() if mitgliedschaft.plz else None,
        "ort": str(mitgliedschaft.ort).strip() if mitgliedschaft.ort else None,
        "adresszusatz": str(mitgliedschaft.zusatz_adresse).strip() if mitgliedschaft.zusatz_adresse else None,
        "postfach": True if mitgliedschaft.postfach else False,
        "postfachNummer": str(mitgliedschaft.postfach_nummer).strip() if mitgliedschaft.postfach_nummer and mitgliedschaft.postfach else None,
        "fuerKorrespondenzGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
        "kontakte": [
            {
                "anrede": str(mitgliedschaft.anrede_c) if mitgliedschaft.anrede_c else "Unbekannt",
                "istHauptkontakt": True,
                "vorname": str(mitgliedschaft.vorname_1).strip() if mitgliedschaft.vorname_1 else None,
                "nachname": str(mitgliedschaft.nachname_1).strip() if mitgliedschaft.nachname_1 else None,
                "email": str(mitgliedschaft.e_mail_1).strip() if mitgliedschaft.e_mail_1 and mitgliedschaft.e_mail_1 != "None" else None,
                "telefon": str(mitgliedschaft.tel_p_1).strip() if mitgliedschaft.tel_p_1 else None,
                "mobile": str(mitgliedschaft.tel_m_1).strip() if mitgliedschaft.tel_m_1 else None,
                "telefonGeschaeft": str(mitgliedschaft.tel_g_1).strip() if mitgliedschaft.tel_g_1 else None,
                "firma": str(mitgliedschaft.firma).strip() if mitgliedschaft.kundentyp == 'Unternehmen' else None,
                "firmaZusatz": str(mitgliedschaft.zusatz_firma).strip() if mitgliedschaft.kundentyp == 'Unternehmen' else None
            }
        ]
    }
    
    if cint(mitgliedschaft.hat_solidarmitglied) == 1:
        solidarmitglied = {
            "anrede": str(mitgliedschaft.anrede_2) if mitgliedschaft.anrede_2 else "Unbekannt",
            "istHauptkontakt": False,
            "vorname": str(mitgliedschaft.vorname_2).strip() if mitgliedschaft.vorname_2 else None,
            "nachname": str(mitgliedschaft.nachname_2).strip() if mitgliedschaft.nachname_2 else None,
            "email": str(mitgliedschaft.e_mail_2).strip() if mitgliedschaft.e_mail_2 and mitgliedschaft.e_mail_2 != "None" else None,
            "telefon": str(mitgliedschaft.tel_p_2).strip() if mitgliedschaft.tel_p_2 else None,
            "mobile": str(mitgliedschaft.tel_m_2).strip() if mitgliedschaft.tel_m_2 else None,
            "telefonGeschaeft": str(mitgliedschaft.tel_g_2).strip() if mitgliedschaft.tel_g_2 else None,
            "firma": '',
            "firmaZusatz": ''
        }
        mitglied['kontakte'].append(solidarmitglied)
    
    adressen.append(mitglied)
    
    if cint(mitgliedschaft.abweichende_objektadresse) == 1:
        objekt = {
            "typ": "Objekt",
            "strasse": str(mitgliedschaft.objekt_strasse).strip() if mitgliedschaft.objekt_strasse else None,
            "hausnummer": str(mitgliedschaft.objekt_hausnummer).strip() if mitgliedschaft.objekt_hausnummer else None,
            "hausnummerZusatz": str(mitgliedschaft.objekt_nummer_zu).strip() if mitgliedschaft.objekt_nummer_zu else None,
            "postleitzahl": str(mitgliedschaft.objekt_plz).strip() if mitgliedschaft.objekt_plz else None,
            "ort": str(mitgliedschaft.objekt_ort).strip() if mitgliedschaft.objekt_ort else None,
            "adresszusatz": str(mitgliedschaft.objekt_zusatz_adresse).strip() if mitgliedschaft.objekt_zusatz_adresse else None,
            "postfach": False,
            "postfachNummer": "",
            "fuerKorrespondenzGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
            "kontakte": []
        }
        adressen.append(objekt)
    
    if cint(mitgliedschaft.abweichende_rechnungsadresse) == 1:
        rechnung = {
            "typ": "Rechnung",
            "strasse": str(mitgliedschaft.rg_strasse).strip() if mitgliedschaft.rg_strasse else None,
            "hausnummer": str(mitgliedschaft.rg_nummer).strip() if mitgliedschaft.rg_nummer else None,
            "hausnummerZusatz": str(mitgliedschaft.rg_nummer_zu).strip() if mitgliedschaft.rg_nummer_zu else None,
            "postleitzahl": str(mitgliedschaft.rg_plz).strip() if mitgliedschaft.rg_plz else None,
            "ort": str(mitgliedschaft.rg_ort).strip() if mitgliedschaft.rg_ort else None,
            "adresszusatz": str(mitgliedschaft.rg_zusatz_adresse).strip() if mitgliedschaft.rg_zusatz_adresse else None,
            "postfach": True if mitgliedschaft.rg_postfach else False,
            "postfachNummer": str(mitgliedschaft.rg_postfach_nummer).strip() if mitgliedschaft.rg_postfach_nummer else None,
            "fuerKorrespondenzGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
            "kontakte": []
        }
        
        if cint(mitgliedschaft.unabhaengiger_debitor) == 1:
            rechnungskontakt = {
                "anrede": str(mitgliedschaft.rg_anrede) if mitgliedschaft.rg_anrede else "Unbekannt",
                "istHauptkontakt": True,
                "vorname": str(mitgliedschaft.rg_vorname).strip() if mitgliedschaft.rg_vorname else None,
                "nachname": str(mitgliedschaft.rg_nachname).strip() if mitgliedschaft.rg_nachname else None,
                "email": str(mitgliedschaft.rg_e_mail).strip() if mitgliedschaft.rg_e_mail and mitgliedschaft.rg_e_mail != "None" else None,
                "telefon": str(mitgliedschaft.rg_tel_p).strip() if mitgliedschaft.rg_tel_p else None,
                "mobile": str(mitgliedschaft.rg_tel_m).strip() if mitgliedschaft.rg_tel_m else None,
                "telefonGeschaeft": str(mitgliedschaft.rg_tel_g).strip() if mitgliedschaft.rg_tel_g else None,
                "firma": str(mitgliedschaft.rg_firma).strip() if mitgliedschaft.rg_firma else None,
                "firmaZusatz": str(mitgliedschaft.rg_zusatz_firma).strip() if mitgliedschaft.rg_zusatz_firma else None,
            }
            rechnung['kontakte'].append(rechnungskontakt)
        else:
            rechnungskontakt = {
                "anrede": str(mitgliedschaft.anrede_c) if mitgliedschaft.anrede_c else "Unbekannt",
                "istHauptkontakt": True,
                "vorname": str(mitgliedschaft.vorname_1).strip() if mitgliedschaft.vorname_1 else None,
                "nachname": str(mitgliedschaft.nachname_1).strip() if mitgliedschaft.nachname_1 else None,
                "email": str(mitgliedschaft.e_mail_1).strip() if mitgliedschaft.e_mail_1 and mitgliedschaft.e_mail_1 != "None" else None,
                "telefon": str(mitgliedschaft.tel_p_1).strip() if mitgliedschaft.tel_p_1 else None,
                "mobile": str(mitgliedschaft.tel_m_1).strip() if mitgliedschaft.tel_m_1 else None,
                "telefonGeschaeft": str(mitgliedschaft.tel_g_1).strip() if mitgliedschaft.tel_g_1 else None,
                "firma": str(mitgliedschaft.firma).strip() if mitgliedschaft.kundentyp == 'Unternehmen' else None,
                "firmaZusatz": str(mitgliedschaft.zusatz_firma).strip() if mitgliedschaft.kundentyp == 'Unternehmen' else None
            }
            rechnung['kontakte'].append(rechnungskontakt)
        
        adressen.append(rechnung)
    
    return adressen

def get_sprache(language='de'):
    language = frappe.db.sql("""SELECT `language_name` FROM `tabLanguage` WHERE `name` = '{language}'""".format(language=language), as_list=True)
    if len(language) > 0:
        return language[0][0]
    else:
        return 'Deutsch'

def create_web_login_user(mitglied_nr):
    if "MV" in mitglied_nr and len(mitglied_nr) > 2:
        user_id = "{0}@login.ch".format(mitglied_nr)
        if not frappe.db.exists("User", user_id):
            try:
                web_login_user = frappe.get_doc({
                    "doctype": "User",
                    "email": user_id,
                    "first_name": user_id.replace("@login.ch", ""),
                    "last_name": "WebLogin",
                    "send_welcome_email": 0
                })
                web_login_user.insert(ignore_permissions=True)
            except Exception as err:
                frappe.log_error("{0}\n\n{1}".format(user_id.replace("@login.ch", ""), str(err)), 'create_web_login_user')
    return

def mark_for_massenlauf(sinv=None, mitgliedschaft=None):
    if not sinv or not mitgliedschaft:
        return
    frappe.db.sql("""
                  UPDATE `tabMitgliedschaft`
                  SET
                    `rg_massendruck` = '{sinv}',
                    `rg_massendruck_vormerkung` = 1
                  WHERE `name` = '{mitgliedschaft}'""".format(sinv=sinv, mitgliedschaft=mitgliedschaft), as_list=True)
    frappe.db.commit()

@frappe.whitelist()
def suche_massenkuendigung(mietobjekt):
    matches = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabKuendigung` WHERE `mietobjekt` = '{0}'""".format(mietobjekt), as_dict=True)[0].qty
    return matches