# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import getdate

class RetourenMW(Document):
    def validate(self):
        if self.status == 'Offen':
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", self.mv_mitgliedschaft)
            mitgliedschaft.m_w_retouren_offen = 1
            mitgliedschaft.save()
        elif self.status == 'In Bearbeitung':
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", self.mv_mitgliedschaft)
            mitgliedschaft.m_w_retouren_in_bearbeitung = 1
            mitgliedschaft.save()
        else:
            anz_offen = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabRetouren MW` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}' AND `status` = 'Offen'""".format(mitgliedschaft=self.mv_mitgliedschaft), as_dict=True)[0].qty
            anz_in_bearbeitung = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabRetouren MW` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}' AND `status` = 'In Bearbeitung'""".format(mitgliedschaft=self.mv_mitgliedschaft), as_dict=True)[0].qty
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
                mitgliedschaft.save()
            else:
                mitgliedschaft.m_w_retouren_offen = 0
                mitgliedschaft.m_w_retouren_in_bearbeitung = 0
                mitgliedschaft.save()
    def onload(self):
        if int(self.onload_frei) == 1:
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", self.mv_mitgliedschaft)
            adresse = frappe.get_doc("Address", mitgliedschaft.adresse_mitglied)
            datum_adressexport = frappe.db.sql("""SELECT `datum_adressexport` FROM `tabMW` WHERE `laufnummer` = '{retoure_mw_sequence_number}' LIMIT 1""".format(retoure_mw_sequence_number=self.retoure_mw_sequence_number), as_dict=True)[0].datum_adressexport
            if getdate(adresse.creation) > getdate(datum_adressexport):
                self.adresse_geaendert = 1
            else: self.adresse_geaendert = 0

def create_post_retouren(data):
    try:
        ausgabe_kurz = frappe.db.sql("""SELECT `ausgabe_kurz` FROM `tabMW` WHERE `laufnummer` = '{retoure_mw_sequence_number}' LIMIT 1""".format(retoure_mw_sequence_number=data['retoureMuWSequenceNumber']), as_dict=True)[0].ausgabe_kurz
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", data['mitgliedId'])
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
            'onload_frei': 1
        })
        
        post_retoure.insert(ignore_permissions=True)
        frappe.db.commit()
        return 1
    except Exception as err:
        return err

@frappe.whitelist()
def close_open_retouren(mitgliedschaft):
    retouren = frappe.db.sql("""SELECT `name` FROM `tabRetouren MW` WHERE `status` != 'Abgeschlossen' AND `mv_mitgliedschaft` = '{mitgliedschaft}'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)
    if len(retouren) > 0:
        for retoure in retouren:
            update = frappe.db.sql("""UPDATE `tabRetouren MW` SET `status` = 'Abgeschlossen' WHERE `name` = '{retoure}'""".format(retoure=retoure.name), as_list=True)
        frappe.db.commit()
