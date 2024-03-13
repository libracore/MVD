# -*- coding: utf-8 -*-
# Copyright (c) 2021-2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe import _
from frappe.utils import cint
from frappe.utils.data import getdate, add_days, now, today

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
        if mitgliedschaft.anrede_c not in ('Herr', 'Frau') and mitgliedschaft.anrede_2 not in ('Herr', 'Frau'):
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
                adressblock += mitgliedschaft.firma or ''
                adressblock += ' '
            if mitgliedschaft.zusatz_firma:
                adressblock += mitgliedschaft.zusatz_firma or ''
            if mitgliedschaft.firma or mitgliedschaft.zusatz_firma:
                adressblock += '\n'
        
        if mitgliedschaft.vorname_1:
            adressblock += mitgliedschaft.vorname_1 or ''
            adressblock += ' '
        adressblock += mitgliedschaft.nachname_1 or ''
        adressblock += '\n'
        
        if mitgliedschaft.hat_solidarmitglied:
            if mitgliedschaft.vorname_2:
                adressblock += mitgliedschaft.vorname_2 or ''
                adressblock += ' '
            if mitgliedschaft.nachname_2:
                adressblock += mitgliedschaft.nachname_2 or ''
            if  mitgliedschaft.vorname_2 or mitgliedschaft.nachname_2:
                adressblock += '\n'
        
        if mitgliedschaft.zusatz_adresse:
            adressblock += mitgliedschaft.zusatz_adresse or ''
            adressblock += '\n'
        
        if mitgliedschaft.strasse and mitgliedschaft.strasse != '':
            adressblock += mitgliedschaft.strasse
            if mitgliedschaft.nummer:
                adressblock += ' '
                adressblock += str(mitgliedschaft.nummer) or ''
                if mitgliedschaft.nummer_zu:
                    adressblock += str(mitgliedschaft.nummer_zu) or ''
            adressblock += '\n'
        
        if cint(mitgliedschaft.postfach) == 1:
            adressblock += 'Postfach '
            adressblock += str(mitgliedschaft.postfach_nummer) or ''
            adressblock += '\n'
        
        if mitgliedschaft.land and mitgliedschaft.land != 'Schweiz':
            laender_code = frappe.get_value("Country", mitgliedschaft.land, "code").upper() + "-"
        else:
            laender_code = ''
        adressblock += laender_code + str(mitgliedschaft.plz) or ''
        adressblock += ' '
        adressblock += mitgliedschaft.ort or ''
        
        return adressblock
    else:
        if mitgliedschaft.kundentyp == 'Unternehmen':
            if mitgliedschaft.firma:
                adressblock += mitgliedschaft.firma or ''
                adressblock += ' '
            if mitgliedschaft.zusatz_firma:
                adressblock += mitgliedschaft.zusatz_firma or ''
            if mitgliedschaft.firma or mitgliedschaft.zusatz_firma:
                adressblock += '\n'
        
        if mitgliedschaft.vorname:
            adressblock += mitgliedschaft.vorname or ''
            adressblock += ' '
        adressblock += mitgliedschaft.nachname or ''
        adressblock += '\n'
        
        if mitgliedschaft.zusatz_adresse:
            adressblock += mitgliedschaft.zusatz_adresse or ''
            adressblock += '\n'
        
        if mitgliedschaft.strasse and mitgliedschaft.strasse != '':
            adressblock += mitgliedschaft.strasse
            if mitgliedschaft.nummer:
                adressblock += ' '
                adressblock += str(mitgliedschaft.nummer) or ''
                if mitgliedschaft.nummer_zu:
                    adressblock += str(mitgliedschaft.nummer_zu) or ''
            adressblock += '\n'
        
        if cint(mitgliedschaft.postfach) == 1:
            adressblock += 'Postfach '
            adressblock += str(mitgliedschaft.postfach_nummer) or ''
            adressblock += '\n'
        
        if mitgliedschaft.land and mitgliedschaft.land != 'Schweiz':
            laender_code = frappe.get_value("Country", mitgliedschaft.land, "code").upper() + "-"
        else:
            laender_code = ''
        adressblock += laender_code + str(mitgliedschaft.plz) or ''
        adressblock += ' '
        adressblock += mitgliedschaft.ort or ''
        
        return adressblock

def get_rg_adressblock(mitgliedschaft):
    adressblock = ''
    if mitgliedschaft.doctype == 'Mitgliedschaft':
        if cint(mitgliedschaft.abweichende_rechnungsadresse) != 1:
            return get_adressblock(mitgliedschaft)
        
        if cint(mitgliedschaft.unabhaengiger_debitor) != 1:
            if mitgliedschaft.kundentyp == 'Unternehmen':
                if mitgliedschaft.firma:
                    adressblock += mitgliedschaft.firma or ''
                    adressblock += ' '
                if mitgliedschaft.zusatz_firma:
                    adressblock += mitgliedschaft.zusatz_firma or ''
                if mitgliedschaft.firma or mitgliedschaft.zusatz_firma:
                    adressblock += '\n'
            
            if mitgliedschaft.vorname_1:
                adressblock += mitgliedschaft.vorname_1 or ''
                adressblock += ' '
            adressblock += mitgliedschaft.nachname_1 or ''
            adressblock += '\n'
            
            if mitgliedschaft.hat_solidarmitglied:
                if mitgliedschaft.vorname_2:
                    adressblock += mitgliedschaft.vorname_2 or ''
                    adressblock += ' '
                if mitgliedschaft.nachname_2:
                    adressblock += mitgliedschaft.nachname_2 or ''
                if  mitgliedschaft.vorname_2 or mitgliedschaft.nachname_2:
                    adressblock += '\n'
        else:
            if mitgliedschaft.rg_kundentyp == 'Unternehmen':
                if mitgliedschaft.rg_firma:
                    adressblock += mitgliedschaft.rg_firma or ''
                    adressblock += ' '
                if mitgliedschaft.rg_zusatz_firma:
                    adressblock += mitgliedschaft.rg_zusatz_firma or ''
                if mitgliedschaft.rg_firma or mitgliedschaft.rg_zusatz_firma:
                    adressblock += '\n'
            
            if mitgliedschaft.rg_vorname:
                adressblock += mitgliedschaft.rg_vorname or ''
                adressblock += ' '
            adressblock += mitgliedschaft.rg_nachname or ''
            adressblock += '\n'
        
        if mitgliedschaft.rg_zusatz_adresse:
            adressblock += mitgliedschaft.rg_zusatz_adresse or ''
            adressblock += '\n'
        
        adressblock += mitgliedschaft.rg_strasse or ''
        if mitgliedschaft.rg_nummer:
            adressblock += ' '
            adressblock += str(mitgliedschaft.rg_nummer) or ''
            if mitgliedschaft.rg_nummer_zu:
                adressblock += str(mitgliedschaft.rg_nummer_zu) or ''
        adressblock += '\n'
        
        if cint(mitgliedschaft.rg_postfach) == 1:
            adressblock += 'Postfach '
            adressblock += str(mitgliedschaft.rg_postfach_nummer) or ''
            adressblock += '\n'
        
        if mitgliedschaft.rg_land != 'Schweiz':
            laender_code = frappe.get_value("Country", mitgliedschaft.rg_land, "code").upper() + "-"
        else:
            laender_code = ''
        adressblock += laender_code + str(mitgliedschaft.rg_plz) or ''
        adressblock += ' '
        adressblock += mitgliedschaft.rg_ort or ''
        
        return adressblock
    elif mitgliedschaft.doctype == 'Kunden':
        if cint(mitgliedschaft.abweichende_rechnungsadresse) != 1:
            return get_adressblock(mitgliedschaft)
        
        if cint(mitgliedschaft.unabhaengiger_debitor) != 1:
            if mitgliedschaft.kundentyp == 'Unternehmen':
                if mitgliedschaft.firma:
                    adressblock += mitgliedschaft.firma or ''
                    adressblock += ' '
                if mitgliedschaft.zusatz_firma:
                    adressblock += mitgliedschaft.zusatz_firma or ''
                if mitgliedschaft.firma or mitgliedschaft.zusatz_firma:
                    adressblock += '\n'
            
            if mitgliedschaft.vorname:
                adressblock += mitgliedschaft.vorname or ''
                adressblock += ' '
            adressblock += mitgliedschaft.nachname or ''
            adressblock += '\n'
        else:
            if mitgliedschaft.rg_kundentyp == 'Unternehmen':
                if mitgliedschaft.rg_firma:
                    adressblock += mitgliedschaft.rg_firma or ''
                    adressblock += ' '
                if mitgliedschaft.rg_zusatz_firma:
                    adressblock += mitgliedschaft.rg_zusatz_firma or ''
                if mitgliedschaft.rg_firma or mitgliedschaft.rg_zusatz_firma:
                    adressblock += '\n'
            
            if mitgliedschaft.rg_vorname:
                adressblock += mitgliedschaft.rg_vorname or ''
                adressblock += ' '
            adressblock += mitgliedschaft.rg_nachname or ''
            adressblock += '\n'
        
        if mitgliedschaft.rg_zusatz_adresse:
            adressblock += mitgliedschaft.rg_zusatz_adresse or ''
            adressblock += '\n'
        
        adressblock += mitgliedschaft.rg_strasse or ''
        if mitgliedschaft.rg_nummer:
            adressblock += ' '
            adressblock += str(mitgliedschaft.rg_nummer) or ''
            if mitgliedschaft.rg_nummer_zu:
                adressblock += str(mitgliedschaft.rg_nummer_zu) or ''
        adressblock += '\n'
        
        if cint(mitgliedschaft.rg_postfach) == 1:
            adressblock += 'Postfach '
            adressblock += str(mitgliedschaft.rg_postfach_nummer) or ''
            adressblock += '\n'
        
        if mitgliedschaft.rg_land != 'Schweiz':
            laender_code = frappe.get_value("Country", mitgliedschaft.rg_land, "code").upper() + "-"
        else:
            laender_code = ''
        adressblock += laender_code + str(mitgliedschaft.rg_plz) or ''
        adressblock += ' '
        adressblock += mitgliedschaft.rg_ort or ''
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

def get_naechstes_jahr_geschuldet(mitglied_id, live_data=False):
    if not live_data:
        bezahltes_mitgliedschafsjahr = cint(frappe.db.get_value("Mitgliedschaft", mitglied_id, 'bezahltes_mitgliedschaftsjahr'))
    else:
        bezahltes_mitgliedschafsjahr = cint(live_data.bezahltes_mitgliedschaftsjahr)
    current_year = cint(now().split("-")[0])

    if current_year > bezahltes_mitgliedschafsjahr:
        return True
    else:
        if not live_data:
            sektion = frappe.db.get_value("Mitgliedschaft", mitglied_id, 'sektion_id')
        else:
            sektion = live_data.sektion_id
        
        stichtag = frappe.db.get_value("Sektion", sektion, 'kuendigungs_stichtag')
        stichtag_datum = getdate("{0}-{1}-{2}".format(current_year, stichtag.strftime("%Y-%m-%d").split("-")[1], stichtag.strftime("%Y-%m-%d").split("-")[2]))
        if getdate(today()) > stichtag_datum:
            return True
        else:
            return False

def mahnstopp(mitgliedschaft, mahnstopp):
    SQL_SAFE_UPDATES_false = frappe.db.sql("""SET SQL_SAFE_UPDATES=0""", as_list=True)
    frappe.db.sql("""UPDATE `tabSales Invoice` SET `exclude_from_payment_reminder_until` = '{mahnstopp}' WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'""".format(mitgliedschaft=mitgliedschaft, mahnstopp=mahnstopp), as_list=True)
    SQL_SAFE_UPDATES_true = frappe.db.sql("""SET SQL_SAFE_UPDATES=1""", as_list=True)
    frappe.db.commit()