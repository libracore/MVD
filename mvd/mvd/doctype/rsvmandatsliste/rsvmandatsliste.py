# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint

class RSVMandatsliste(Document):
    def before_save(self):
        already_added_themen = []
        all_themen = []

        # Pre-Cleanup
        self.set("thema", [])
        self.set("sprachen", [])
        
        mandate = frappe.db.sql(
            """
                SELECT `name`
                FROM `tabRSVMandat`
                WHERE `rsvmandatsliste` = '{0}'
            """.format(self.name),
            as_dict=True
        )
        for mandat in mandate:
            # Setzen Werte aus RSVMandatliste in RSVMandat & Sync Themen
            frappe.db.set_value("RSVMandat", mandat.name, "fallnummer", self.fallnummer)
            frappe.db.set_value("RSVMandat", mandat.name, "vermieterin", self.vermieterin)
            frappe.db.set_value("RSVMandat", mandat.name, "verwaltung", self.verwaltung)
            frappe.db.set_value("RSVMandat", mandat.name, "bezirk", self.bezirk)

            all_themen, already_added_themen = self.sync_themen(mandat.name, all_themen, already_added_themen)

        self.sync_sprachen()
    
    def sync_themen(self, rsvmandat, all_themen, already_added_themen):
        # Übernehmen aller Themen aus RSVMandat in RSVMandatliste
        themen = frappe.db.sql(
            """
                SELECT `thema`
                FROM `tabRSV Thema MultiTable`
                WHERE `parent` = '{0}'
            """.format(rsvmandat),
            as_dict=True
        )
        
        # Themen hinzufügen
        for thema in themen:
            if thema.thema and thema.thema not in already_added_themen:
                already_added_themen.append(thema.thema)
                self.append("thema", {'thema': thema.thema})
            all_themen.append(thema.thema)
        
        # Alte, überflüssige Themen entfernen
        for thema in self.thema:
            if thema.thema not in all_themen:
                self.remove(thema)
        
        return all_themen, already_added_themen
    
    def sync_sprachen(self):
        already_added_sprachen = []
        all_sprachen = []
        # Übernehmen aller Sprachen aus der entsprechenden Mitgliedschaft/Kunden aus dem zugehörigen RSVMandat #1876
        sprachen = frappe.db.sql(
            """
                SELECT `language`
                FROM `tabRSVMandat`
                WHERE `rsvmandatsliste` = '{0}'
            """.format(self.name),
            as_dict=True
        )
        
        # Sprachen hinzufügen
        for sprache in sprachen:
            if sprache.language and sprache.language not in already_added_sprachen:
                self.append("sprachen", {'sprache': sprache.language})
                already_added_sprachen.append(sprache.language)
            all_sprachen.append(sprache.language)
        
        # Alte, überflüssige Sprachen entfernen
        for sprache in self.sprachen:
            if sprache.sprache not in all_sprachen:
                self.remove(sprache)
    
    def reset_status(self):
        # Wird via "Speichern" von RSVMandat getriggert
        refs = frappe.db.count("RSVMandat", {'rsvmandatsliste': self.name}, ['name'])
        if cint(refs) < 2 and self.typ != 'EM':
            self.typ = 'EM'
        elif cint(refs) >= 2 and cint(refs) <= 9 and self.typ != 'KGM':
            self.typ = 'KGM'
        elif cint(refs) > 9 and self.typ != 'GGM':
            self.typ = 'GGM'

def update_rsvmandatlise(rsvmandat, rsvmandatsliste):
    rsvml = frappe.get_doc("RSVMandatsliste", rsvmandatsliste)
    rsvml.reset_status()
    rsvml.before_save()
    rsvml.save()
    return
