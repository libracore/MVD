# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint, today
import requests

class RSVMandat(Document):
    def before_save(self):
        rsv_mitglieder = frappe.db.sql(
            """
                SELECT `name`, `bfs_nr`, `sektion_id`
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
            # Setzen von sektion_id wenn leer
            if not self.sektion_id and rsv_mitglied.sektion_id:
                self.sektion_id = rsv_mitglied.sektion_id

        # Vergeben an VA
        found_va_assignment = False
        for va in self.va_vergabe:
            if cint(va.assigned) == 1:
                self.datum_vergabe = today()
                self.anwalt = get_va_from_user(va.va_user)
                found_va_assignment = True
        if found_va_assignment:
            if not self.anwalt: frappe.throw("Der VA konnte nicht gefunden werden.")
            for rsv_mitglied in rsv_mitglieder:
                wrong_status = []
                if frappe.db.get_value("RSVMitglied", rsv_mitglied.name, "status") == 'Geprüft':
                    frappe.db.set_value("RSVMitglied", rsv_mitglied.name, "status", "Eingereicht")
                else:
                    wrong_status.append(rsv_mitglied.name)
            if len(wrong_status) > 0:
                frappe.msgprint(
                    msg="Durch die Vergabe des RSV-Mandats hat das System bei allen zugehörigen RSV-Mitgliedern den Status von Geprüft auf Eingereicht geändert, ausser bei nachfolgenden da deren Status widererwartend nicht Geprüft war:{0}".format("<br>".join(wrong_status)),
                    title="RSV-Mitglieder mit unerwarteten Statis",
                    indicator="orange"
                )
    
    def reset_status(self):
        # Wird via "Speichern" von RSVMitglied getriggert
        if not self.set_type_manually:
            refs = frappe.db.count("RSVMitglied", {'rsvmandat': self.name}, ['name'])
            if cint(refs) < 2 and self.typ != 'EM':
                self.typ = 'EM'
            elif cint(refs) >= 2 and cint(refs) <= 9 and self.typ != 'KGM':
                self.typ = 'KGM'
            elif cint(refs) > 9 and self.typ != 'GGM':
                self.typ = 'GGM'

def get_va_from_user(va_user):
    va = frappe.db.sql(
            """
                SELECT `parent`
                FROM `tabTermin Kontaktperson Multi User`
                WHERE `user` = '{0}'
                AND `parent` IN (
                    SELECT `name`
                    FROM `tabTermin Kontaktperson`
                    WHERE `ist_vertrauensanwaeltin` = '1'
                )
            """.format(va_user),
            as_dict=True
        )
    if len(va) > 0:
        return va[0].parent
    return ''

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