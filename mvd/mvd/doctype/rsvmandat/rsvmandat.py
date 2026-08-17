# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint
import requests

class RSVMandat(Document):
    def before_save(self):
        rsv_mitglieder = frappe.db.sql(
            """
                SELECT `name`, `bfs_nr`
                FROM `tabRSVMitglied`
                WHERE `rsvmandat` = '{0}'
            """.format(self.name),
            as_dict=True
        )

        for rsv_mitglied in rsv_mitglieder:
            frappe.db.set_value("RSVMitglied", rsv_mitglied.name, "fallnummer", self.fallnummer)
            # Setzen von Schlichtungsbehörde wenn leer
            if not self.schlichtungsbehoerde and rsv_mitglied.bfs_nr:
                self.schlichtungsbehoerde = get_schlichtungsbehoerde(rsv_mitglied.bfs_nr)
    
    def reset_status(self):
        # Wird via "Speichern" von RSVMitglied getriggert
        refs = frappe.db.count("RSVMitglied", {'rsvmandat': self.name}, ['name'])
        if cint(refs) < 2 and self.typ != 'EM':
            self.typ = 'EM'
        elif cint(refs) >= 2 and cint(refs) <= 9 and self.typ != 'KGM':
            self.typ = 'KGM'
        elif cint(refs) > 9 and self.typ != 'GGM':
            self.typ = 'GGM'

def update_rsvmandat(rsvmitglied, rsvmandat):
    rsvml = frappe.get_doc("RSVMandat", rsvmandat)
    rsvml.reset_status()
    rsvml.before_save()
    rsvml.save()
    return

def get_rsv_mandat_languages(rsv_mandat):
    sprachen = frappe.db.sql(
        """
            SELECT `sprache`
            FROM `tabRSV Sprache MultiTable`
            WHERE `parent` = '{0}'
        """.format(rsv_mandat),
        as_dict=True
    )

    if len(sprachen) < 1: return ''

    return ", ".join(sprache["sprache"] for sprache in sprachen)

def get_schlichtungsbehoerde(bfs_nr):
    # --- EXTERNER API CALL AN MP ---
    api_url = "https://mp.libracore.ch/api/method/mietrechtspraxis.api.get_arbitration_authority_from_bfs"
    try:
        response = requests.get(api_url, params={"bfs_nr": bfs_nr}, timeout=5)
        if response.status_code == 200:
            response_json = response.json()
            aa_data = response_json.get("message") if response_json else None
            
            if aa_data and aa_data.get("titel"):
                return aa_data.get("titel")
        else:
            return None
            
    except Exception as e:
        return None
    
    return None