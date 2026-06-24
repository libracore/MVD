# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint

class RSVMandatsliste(Document):
    def validate(self):
        mandate = frappe.db.sql(
            """
                SELECT `name`
                FROM `tabRSVMandat`
                WHERE `rsvmandatsliste` = '{0}'
            """.format(self.name),
            as_dict=True
        )
        for mandat in mandate:
            # Setzen Werte aus RSVMandatliste in RSVMandat
            frappe.db.set_value("RSVMandat", mandat.name, "fallnummer", self.fallnummer)
            frappe.db.set_value("RSVMandat", mandat.name, "vermieterin", self.vermieterin)
            frappe.db.set_value("RSVMandat", mandat.name, "verwaltung", self.verwaltung)
            frappe.db.set_value("RSVMandat", mandat.name, "bezirk", self.bezirk)
            # Übernehmen aller Themen aus RSVMandat in RSVMandatliste
            themen = frappe.db.sql(
                """
                    SELECT `thema`
                    FROM `tabRSV Thema MultiTable`
                    WHERE `parent` = '{0}'
                """.format(mandat.name),
                as_dict=True
            )
            for thema in themen:
                if not frappe.db.exists({
                    "doctype": "RSV Thema MultiTable",
                    "parent": self.name,
                    "thema": thema.thema
                }):
                    self.append("thema", {'thema': thema.thema})

def update_rsvmandatlise(rsvmandat, rsvmandatsliste):
    # Übernehmen aller Themen aus RSVMandat in RSVMandatliste
    themen = frappe.db.sql(
        """
            SELECT `thema`
            FROM `tabRSV Thema MultiTable`
            WHERE `parent` = '{0}'
        """.format(rsvmandat),
        as_dict=True
    )
    if len(themen) > 0:
        rsvml = frappe.get_doc("RSVMandatsliste", rsvmandatsliste)
    
    for thema in themen:
        if not frappe.db.exists({
            "doctype": "RSV Thema MultiTable",
            "parent": rsvmandatsliste,
            "thema": thema.thema
        }):
            rsvml.append("thema", {'thema': thema.thema})
    
    if len(themen) > 0:
        rsvml.save()
    
    # Update Status
    reset_status(rsvmandatsliste)


def reset_status(rsvmandatsliste):
    rsvml = frappe.get_doc("RSVMandatsliste", rsvmandatsliste)
    refs = frappe.db.count("RSVMandat", {'rsvmandatsliste': rsvml.name}, ['name'])
    if cint(refs) < 2 and rsvml.typ != 'EM':
        frappe.db.set_value("RSVMandatsliste", rsvml.name, "typ", "EM")
    elif cint(refs) >= 2 and cint(refs) <= 9 and rsvml.typ != 'KGM':
        frappe.db.set_value("RSVMandatsliste", rsvml.name, "typ", "KGM")
    elif cint(refs) > 9 and rsvml.typ != 'GGM':
        frappe.db.set_value("RSVMandatsliste", rsvml.name, "typ", "GGM")
