# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import getdate

class RetourenMW(Document):
    def validate(self):
        if int(self.ignore_validation) != 1:
            if self.status == 'Offen':
                mitgliedschaft = frappe.get_doc("Mitgliedschaft", self.mv_mitgliedschaft)
                mitgliedschaft.m_w_retouren_offen = 1
                anz_offen, anz_in_bearbeitung = get_retouren_qty(self.mv_mitgliedschaft, self)
                
                if anz_in_bearbeitung < 1:
                    mitgliedschaft.m_w_retouren_in_bearbeitung = 0
                
                mitgliedschaft.m_w_anzahl = anz_offen + anz_in_bearbeitung
                mitgliedschaft.save()
                
            elif self.status == 'In Bearbeitung':
                mitgliedschaft = frappe.get_doc("Mitgliedschaft", self.mv_mitgliedschaft)
                mitgliedschaft.m_w_retouren_in_bearbeitung = 1
                anz_offen, anz_in_bearbeitung = get_retouren_qty(self.mv_mitgliedschaft, self)
                
                if anz_offen < 1:
                    mitgliedschaft.m_w_retouren_offen = 0
                
                mitgliedschaft.m_w_anzahl = anz_offen + anz_in_bearbeitung
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
                    mitgliedschaft.save()
                else:
                    mitgliedschaft.m_w_retouren_offen = 0
                    mitgliedschaft.m_w_retouren_in_bearbeitung = 0
                    mitgliedschaft.m_w_anzahl = anz_offen + anz_in_bearbeitung
                    mitgliedschaft.save()
            
            adresse = frappe.db.sql("""SELECT `adresse_mitglied` FROM `tabMitgliedschaft` WHERE `name` = '{mitgliedschaft}'""".format(mitgliedschaft=self.mv_mitgliedschaft), as_dict=True)[0].adresse_mitglied
            adresse = frappe.get_doc("Address", adresse)
            datum_adressexport = frappe.db.sql("""SELECT `datum_adressexport` FROM `tabMW` WHERE `laufnummer` = '{retoure_mw_sequence_number}' LIMIT 1""".format(retoure_mw_sequence_number=self.retoure_mw_sequence_number), as_dict=True)
            if len(datum_adressexport) > 0:
                datum_adressexport = datum_adressexport[0].datum_adressexport
                if getdate(adresse.modified) > getdate(datum_adressexport):
                    self.adresse_geaendert = 1

def get_retouren_qty(mitgliedschaft, self):
    anz_offen = frappe.db.sql("""SELECT
                                    COUNT(`name`) AS `qty`
                                FROM `tabRetouren MW`
                                WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'
                                AND `status` = 'Offen'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)[0].qty
    anz_in_bearbeitung = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabRetouren MW`
                                        WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'
                                        AND `status` = 'In Bearbeitung'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)[0].qty
    
    old_status = frappe.db.sql("""SELECT `status` FROM `tabRetouren MW` WHERE `name` = '{retoure}'""".format(retoure=self.name), as_dict=True)
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
        ausgabe_kurz = frappe.db.sql("""SELECT `ausgabe_kurz` FROM `tabMW` WHERE `laufnummer` = '{retoure_mw_sequence_number}' LIMIT 1""".format(retoure_mw_sequence_number=data['retoureMuWSequenceNumber']), as_dict=True)[0].ausgabe_kurz
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", data['mitgliedId'])
        adresse = frappe.get_doc("Address", mitgliedschaft.adresse_mitglied)
        datum_adressexport = frappe.db.sql("""SELECT `datum_adressexport` FROM `tabMW` WHERE `laufnummer` = '{retoure_mw_sequence_number}' LIMIT 1""".format(retoure_mw_sequence_number=data['retoureMuWSequenceNumber']), as_dict=True)[0].datum_adressexport
        if getdate(adresse.modified) > getdate(datum_adressexport):
            adresse_geaendert = 1
        else:
            adresse_geaendert = 0
        post_retoure = frappe.get_doc({
            'doctype': 'Retouren MW',
            'mv_mitgliedschaft': data['mitgliedId'],
            'sektion_id': mitgliedschaft.sektion_id,
            'ausgabe': ausgabe_kurz,
            'legacy_kategorie_code': data['legacyKategorieCode'],
            'legacy_notiz': data['legacyNotiz'],
            'grund_code': data['grundCode'],
            'grund_bezeichnung': data['grundBezeichnung'],
            'retoure_mw_sequence_number': data['retoureMuWSequenceNumber'],
            'retoure_dmc': data['retoureDMC'],
            'retoureSendungsbild': data['retoureSendungsbild'],
            'datum_erfasst_post': data['datumErfasstPost'],
            'adresse_geaendert': adresse_geaendert
        })
        
        post_retoure.insert(ignore_permissions=True)
        frappe.db.commit()
        return 1
    except Exception as err:
        return err

@frappe.whitelist()
def close_open_retouren(mitgliedschaft):
    retouren = frappe.db.sql("""SELECT
                                    `name`
                                FROM `tabRetouren MW`
                                WHERE `status` != 'Abgeschlossen'
                                AND `mv_mitgliedschaft` = '{mitgliedschaft}'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)
    if len(retouren) > 0:
        for retoure in retouren:
            r = frappe.get_doc("Retouren MW", retoure.name)
            r.status = 'Abgeschlossen'
            r.save()

def check_dates(adresse, event):
    adresse_alt = frappe.db.sql("""SELECT * FROM `tabAddress` WHERE `name` = '{adr}'""".format(adr=adresse.name), as_dict=True)
    if len(adresse_alt) > 0:
        adresse_alt = adresse_alt[0]
        changed = False
        if adresse_alt.zusatz != adresse.zusatz or \
        adresse_alt.strasse != adresse.strasse or \
        adresse_alt.postfach != adresse.postfach or \
        adresse_alt.postfach_nummer != adresse.postfach_nummer or \
        adresse_alt.plz != adresse.plz or \
        adresse_alt.city != adresse.city:
            changed = True
        
        if changed:
            mitgliedschaften = frappe.db.sql("""SELECT
                                                    `name`
                                                FROM `tabMitgliedschaft`
                                                WHERE `adresse_mitglied` = '{adresse}' LIMIT 1""".format(adresse=adresse.name), as_dict=True)
            if len(mitgliedschaften) > 0:
                mitgliedschaft = mitgliedschaften[0].name
                retouren = frappe.db.sql("""SELECT
                                                `name`
                                            FROM `tabRetouren MW`
                                            WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'
                                            AND `status` != 'Abgeschlossen'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)
                for retoure in retouren:
                    retoure = frappe.get_doc("Retouren MW", retoure.name)
                    datum_adressexport = frappe.db.sql("""SELECT
                                                                `datum_adressexport`
                                                            FROM `tabMW`
                                                            WHERE `laufnummer` = '{retoure_mw_sequence_number}' LIMIT 1""".format(retoure_mw_sequence_number=retoure.retoure_mw_sequence_number), as_dict=True)
                    if len(datum_adressexport) > 0:
                        datum_adressexport = datum_adressexport[0].datum_adressexport
                        if getdate(adresse.modified) > getdate(datum_adressexport) and retoure.adresse_geaendert != 1:
                            retoure.adresse_geaendert = 1
                            retoure.save(ignore_permissions=True)

@frappe.whitelist()
def get_mail_data(mitgliedschaft, retoure, grund_bezeichnung):
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    if mitgliedschaft.e_mail_1:
        return {
            'email': mitgliedschaft.e_mail_1,
            'cc': 'mv+Mitgliedschaft+{0}@libracore.io,mv+Retouren%20MW+{1}@libracore.io'.format(mitgliedschaft.name, retoure),
            'subject': 'Ihre Mitgliedschaft: Neue Adresse?',
            'email_body': '{0}%0d%0a%0d%0aDie Post konnte Ihnen unsere Verbandszeitschrift M+W nicht zustellen. Sie wurde retourniert mit dem Vermerk «{1}».%0d%0aBitte teilen Sie uns Ihre aktuelle Wohnadresse mit, damit wir Ihnen auch weiterhin unsere Post zustellen können.%0d%0a%0d%0aSie sind in unserer Mitgliederdatei unter nachfolgender Adresse geführt:%0d%0a{2}%0d%0a%0d%0aFreundliche Grüsse'.format(mitgliedschaft.briefanrede, grund_bezeichnung, mitgliedschaft.adressblock.replace("\n", "%0d%0a"))
        }
    else:
        return None
