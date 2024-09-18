# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import getdate
import json
from frappe.utils import cint

class Retouren(Document):
    def onload(self):
        if self.mv_mitgliedschaft:
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", self.mv_mitgliedschaft)
            self.adressblock = mitgliedschaft.adressblock
    
    def validate(self):
        if self.status == 'Offen':
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", self.mv_mitgliedschaft)
            mitgliedschaft.m_w_retouren_offen = 1
            anz_offen, anz_in_bearbeitung = get_retouren_qty(self.mv_mitgliedschaft, self)
            
            if anz_in_bearbeitung < 1:
                mitgliedschaft.m_w_retouren_in_bearbeitung = 0
            
            mitgliedschaft.m_w_anzahl = anz_offen + anz_in_bearbeitung
            mitgliedschaft.letzte_bearbeitung_von = 'SP'
            
            mitgliedschaft.retoure_in_folge = self.retoure_in_folge
            
            mitgliedschaft.save()
            
        elif self.status == 'In Bearbeitung':
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", self.mv_mitgliedschaft)
            mitgliedschaft.m_w_retouren_in_bearbeitung = 1
            anz_offen, anz_in_bearbeitung = get_retouren_qty(self.mv_mitgliedschaft, self)
            
            if anz_offen < 1:
                mitgliedschaft.m_w_retouren_offen = 0
            
            mitgliedschaft.m_w_anzahl = anz_offen + anz_in_bearbeitung
            mitgliedschaft.letzte_bearbeitung_von = 'SP'
            
            mitgliedschaft.retoure_in_folge = self.retoure_in_folge
            
            mitgliedschaft.save()
            
        else:
            anz_offen, anz_in_bearbeitung = get_retouren_qty(self.mv_mitgliedschaft, self)
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", self.mv_mitgliedschaft)
            
            if anz_offen > 0 or anz_in_bearbeitung > 0:
                if anz_offen > 0:
                    mitgliedschaft.m_w_retouren_offen = 1
                else:
                    mitgliedschaft.m_w_retouren_offen = 0
                if anz_in_bearbeitung > 0:
                    mitgliedschaft.m_w_retouren_in_bearbeitung = 1
                else:
                    mitgliedschaft.m_w_retouren_in_bearbeitung = 0
                mitgliedschaft.m_w_anzahl = anz_offen + anz_in_bearbeitung
                mitgliedschaft.letzte_bearbeitung_von = 'SP'
                
                mitgliedschaft.retoure_in_folge = self.retoure_in_folge
                
                mitgliedschaft.save()
            else:
                mitgliedschaft.m_w_retouren_offen = 0
                mitgliedschaft.m_w_retouren_in_bearbeitung = 0
                mitgliedschaft.m_w_anzahl = anz_offen + anz_in_bearbeitung
                mitgliedschaft.letzte_bearbeitung_von = 'SP'
                
                mitgliedschaft.retoure_in_folge = self.retoure_in_folge
                
                mitgliedschaft.save()
        
        if self.adresse_geaendert != 1:
            adresse = frappe.db.sql("""SELECT `adresse_mitglied` FROM `tabMitgliedschaft` WHERE `name` = '{mitgliedschaft}'""".format(mitgliedschaft=self.mv_mitgliedschaft), as_dict=True)
            if len(adresse) > 0:
                if adresse[0].adresse_mitglied and adresse[0].adresse_mitglied != 'None':
                    adresse = adresse[0].adresse_mitglied
                    
                    datum_adressexport = frappe.db.sql("""SELECT `datum_adressexport` FROM `tabMW` WHERE `laufnummer` = '{retoure_mw_sequence_number}' LIMIT 1""".format(retoure_mw_sequence_number=self.retoure_mw_sequence_number), as_dict=True)
                    if len(datum_adressexport) > 0:
                        datum_adressexport = datum_adressexport[0].datum_adressexport
                        self.adresse_geaendert = adresse_geaendert_check(adr=adresse, datum_adressexport=datum_adressexport)

def get_retouren_qty(mitgliedschaft, self):
    anz_offen = frappe.db.sql("""SELECT
                                    COUNT(`name`) AS `qty`
                                FROM `tabRetouren`
                                WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'
                                AND `status` = 'Offen'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)[0].qty
    anz_in_bearbeitung = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabRetouren`
                                        WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'
                                        AND `status` = 'In Bearbeitung'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)[0].qty
    
    old_status = frappe.db.sql("""SELECT `status` FROM `tabRetouren` WHERE `name` = '{retoure}'""".format(retoure=self.name), as_dict=True)
    if len(old_status) > 0:
        if old_status[0].status != self.status:
            if old_status[0].status == 'Offen':
                anz_offen -= 1
            elif old_status[0].status == 'In Bearbeitung':
                anz_in_bearbeitung -= 1
            
            if self.status == 'Offen':
                anz_offen += 1
            elif self.status == 'In Bearbeitung':
                anz_in_bearbeitung += 1
    else:
        if self.status == 'Offen':
            anz_offen += 1
        elif self.status == 'In Bearbeitung':
            anz_in_bearbeitung += 1
    
    return anz_offen, anz_in_bearbeitung

def create_post_retouren(data):
    try:
        ausgabe_kurz = frappe.db.sql("""SELECT `ausgabe_kurz` FROM `tabMW` WHERE `laufnummer` = '{retoure_mw_sequence_number}' LIMIT 1""".format(retoure_mw_sequence_number=data.retoureMuWSequenceNumber), as_dict=True)[0].ausgabe_kurz
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", data.mitgliedId)
        
        if mitgliedschaft.adresse_mitglied and mitgliedschaft.adresse_mitglied != 'None':
            datum_adressexport = frappe.db.sql("""SELECT `datum_adressexport` FROM `tabMW` WHERE `laufnummer` = '{retoure_mw_sequence_number}' LIMIT 1""".format(retoure_mw_sequence_number=data.retoureMuWSequenceNumber), as_dict=True)[0].datum_adressexport
            adresse_geaendert = adresse_geaendert_check(adr=mitgliedschaft.adresse_mitglied, datum_adressexport=datum_adressexport)
        else:
            adresse_geaendert = 0
        
        if data.neueAdresse:
            neue_adresse_json = json.dumps(data.neueAdresse.__dict__)
            neue_adresse = """"""
            try:
                gueltig_ab = data.neueAdresse.validFrom.split(" ")[0].split("/")[2] + "-" + data.neueAdresse.validFrom.split(" ")[0].split("/")[0] + "-" + data.neueAdresse.validFrom.split(" ")[0].split("/")[1]
            except:
                gueltig_ab = None
            if data.neueAdresse.validTo:
                neue_adresse += """\nGültig bis {0}""".format(data.neueAdresse.validTo)
            if data.neueAdresse.adresszusatz:
                neue_adresse += """\n{0}""".format(data.neueAdresse.adresszusatz)
            if data.neueAdresse.postfach:
                neue_adresse += """\n{0}""".format(data.neueAdresse.postfach)
                if data.neueAdresse.postfachNummer:
                    neue_adresse += """ {0}""".format(data.neueAdresse.postfachNummer)
            if data.neueAdresse.strasse:
                neue_adresse += """\n{0}""".format(data.neueAdresse.strasse)
                if data.neueAdresse.hausnummer:
                    neue_adresse += """ {0}""".format(data.neueAdresse.hausnummer)
                if data.neueAdresse.hausnummerZusatz:
                    neue_adresse += """{0}""".format(data.neueAdresse.hausnummerZusatz)
            if data.neueAdresse.postleitzahl:
                neue_adresse += """\n{0} {1}""".format(data.neueAdresse.postleitzahl, data.neueAdresse.ort)
            
        else:
            neue_adresse_json = None
            neue_adresse = None
            gueltig_ab = None
        
        post_retoure = frappe.get_doc({
            'doctype': 'Retouren',
            'mv_mitgliedschaft': data.mitgliedId,
            'sektion_id': mitgliedschaft.sektion_id,
            'adressblock': mitgliedschaft.adressblock,
            'ausgabe': ausgabe_kurz,
            'legacy_kategorie_code': data.legacyKategorieCode,
            'legacy_notiz': data.legacyNotiz,
            'grund_code': data.grundCode,
            'grund_bezeichnung': data.grundBezeichnung,
            'retoure_mw_sequence_number': data.retoureMuWSequenceNumber,
            'retoure_dmc': data.retoureDMC,
            'retoureSendungsbild': data.retoureSendungsbild,
            'datum_erfasst_post': data.datumErfasstPost,
            'adresse_geaendert': adresse_geaendert,
            'retoure_in_folge': check_retoure_in_folge(data.retoureMuWSequenceNumber, data.mitgliedId),
            'neue_adresse_json': str(neue_adresse_json),
            'neue_adresse': neue_adresse,
            'neue_adresse_gueltig_ab': gueltig_ab,
            'raw_data': data.rawData
        })
        
        post_retoure.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return 1, cint(post_retoure.retoure_in_folge)
        
    except Exception as err:
        return "{0}\n\n{1}".format(err, data.rawData), 0

@frappe.whitelist()
def close_open_retouren(mitgliedschaft):
    retouren = frappe.db.sql("""SELECT
                                    `name`
                                FROM `tabRetouren`
                                WHERE `status` != 'Abgeschlossen'
                                AND `mv_mitgliedschaft` = '{mitgliedschaft}'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)
    if len(retouren) > 0:
        for retoure in retouren:
            r = frappe.get_doc("Retouren", retoure.name)
            r.status = 'Abgeschlossen'
            r.save()

def check_dates(adresse, event):
    changed = adresse_geaendert_check(adr=adresse.name, adresse_fuer_vergleich=adresse)
    if changed == 1:
        mitgliedschaften = frappe.db.sql("""SELECT
                                                `name`
                                            FROM `tabMitgliedschaft`
                                            WHERE `adresse_mitglied` = '{adresse}' LIMIT 1""".format(adresse=adresse.name), as_dict=True)
        if len(mitgliedschaften) > 0:
            mitgliedschaft = mitgliedschaften[0].name
            retouren = frappe.db.sql("""SELECT
                                            `name`
                                        FROM `tabRetouren`
                                        WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)
            for retoure in retouren:
                retoure = frappe.get_doc("Retouren", retoure.name)
                if retoure.adresse_geaendert != 1:
                    datum_adressexport = frappe.db.sql("""SELECT
                                                                `datum_adressexport`
                                                            FROM `tabMW`
                                                            WHERE `laufnummer` = '{retoure_mw_sequence_number}' LIMIT 1""".format(retoure_mw_sequence_number=retoure.retoure_mw_sequence_number), as_dict=True)
                    if len(datum_adressexport) > 0:
                        adresse_geaendert = adresse_geaendert_check(adr=adresse.name, adresse_fuer_vergleich=adresse)
                        frappe.db.sql("""UPDATE `tabRetouren` SET `adresse_geaendert` = {adresse_geaendert} WHERE `name` = '{name}'""".format(adresse_geaendert=adresse_geaendert, name=retoure.name), as_list=True)

@frappe.whitelist()
def get_mail_data(mitgliedschaft, retoure, grund_bezeichnung):
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    if mitgliedschaft.e_mail_1:
        email_body = '{0}%0d%0a%0d%0aDie Post konnte Ihnen unsere Verbandszeitschrift M+W nicht zustellen. Sie wurde retourniert mit dem Vermerk «{1}».%0d%0aBitte teilen Sie uns Ihre aktuelle Wohnadresse mit, damit wir Ihnen auch weiterhin unsere Post zustellen können.%0d%0a%0d%0aSie sind in unserer Mitgliederdatei unter nachfolgender Adresse geführt:%0d%0a{2}%0d%0a%0d%0a%0d%0a%0d%0a'.format(mitgliedschaft.briefanrede, grund_bezeichnung.split(" (")[0], mitgliedschaft.adressblock.replace("\n", "%0d%0a"))
        if mitgliedschaft.language == 'fr':
            email_body = "Cher Monsieur / Chère Madame,%0d%0a%0d%0aLa poste n'a pas pu vous livrer notre journal de l’Asloca M+W à l’adresse indiquée. Il a été retourné avec la remarque «{0}».%0d%0aVeuillez nous communiquer votre adresse résidentielle actuelle afin que nous puissions continuer à vous livrer notre courrier.%0d%0a%0d%0aDans notre fichier votre adresse est enregistrée comme suit :%0d%0a{1}%0d%0a%0d%0a%0d%0a%0d%0a".format(grund_bezeichnung.split(" (")[0], mitgliedschaft.adressblock.replace("\n", "%0d%0a"))
        
        return {
            'email': mitgliedschaft.e_mail_1,
            'cc': 'mv+Mitgliedschaft+{0}@libracore.io;mv+Retouren+{1}@libracore.io'.format(mitgliedschaft.name, retoure),
            'subject': 'Ihre Mitgliedschaft ({0}): Neue Adresse?'.format(mitgliedschaft.mitglied_nr),
            'email_body': email_body
        }
    else:
        return None

def adresse_geaendert_check(adr=None, datum_adressexport=None, adresse_fuer_vergleich=False):
    if adr:
        if not adresse_fuer_vergleich:
            adresse_geaendert = frappe.db.sql("""SELECT 
                                                        `creation`
                                                    FROM `tabVersion`
                                                    WHERE `docname` = '{adr}'
                                                    AND `ref_doctype` = 'Address'
                                                    AND (
                                                        `data` LIKE '%zusatz%'
                                                        or `data` LIKE '%strasse%'
                                                        or `data` LIKE '%postfach%'
                                                        or `data` LIKE '%postfach_nummer%'
                                                        or `data` LIKE '%plz%'
                                                        or `data` LIKE '%city%'
                                                        or `data` LIKE '%address_line2%'
                                                    )
                                                    ORDER BY `creation` DESC
                                                    LIMIT 1""".format(adr=adr), as_dict=True)
            if len(adresse_geaendert) > 0:
                if datum_adressexport:
                    adresse_geaendert = getdate(adresse_geaendert[0].creation)
                    datum_adressexport = getdate(datum_adressexport)
                    frappe.log_error("adresse_geaendert: {0}\ndatum_adressexport: {1}".format(adresse_geaendert, datum_adressexport), "adresse_geaendert_check: {0}".format(adr))
                    if adresse_geaendert >= datum_adressexport:
                        return 1
                    else:
                        return 0
                else:
                    return 1
            else:
                return 0
        else:
            try:
                latest_adress = adresse_fuer_vergleich._doc_before_save
                if latest_adress.zusatz != adresse_fuer_vergleich.zusatz:
                    return 1
                if latest_adress.strasse != adresse_fuer_vergleich.strasse:
                    return 1
                if latest_adress.postfach != adresse_fuer_vergleich.postfach:
                    return 1
                if latest_adress.postfach_nummer != adresse_fuer_vergleich.postfach_nummer:
                    return 1
                if latest_adress.plz != adresse_fuer_vergleich.plz:
                    return 1
                if latest_adress.city != adresse_fuer_vergleich.city:
                    return 1
                if latest_adress.address_line2 != adresse_fuer_vergleich.address_line2:
                    return 1
            except:
                # no older version avaible
                return 0
            # no changes
            return 0
        
    else:
        return 0

def check_retoure_in_folge(retoure_mw_sequence_number, mv_mitgliedschaft):
    retoure_mw_sequence_number = int(retoure_mw_sequence_number) - 1
    qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabRetouren` WHERE `retoure_mw_sequence_number` = '{retoure_mw_sequence_number}' AND `mv_mitgliedschaft` = '{mv_mitgliedschaft}'""".format(retoure_mw_sequence_number=retoure_mw_sequence_number, mv_mitgliedschaft=mv_mitgliedschaft), as_dict=True)[0].qty
    if qty > 0:
        return 1
    else:
        return 0
