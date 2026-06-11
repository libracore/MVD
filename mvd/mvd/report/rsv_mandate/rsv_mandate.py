# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data

def get_columns():
    return[
        {"label": _("Mandat Liste"), "fieldname": "mandat_liste", "fieldtype": "Link", "options": "RSVMandatsliste"},
        {"label": _("Mandat"), "fieldname": "mandat", "fieldtype": "Link", "options": "RSVMandat"},
        {"label": _("Coop Fallnr."), "fieldname": "coop_fallnummer", "fieldtype": "Data"},
        {"label": _("Mitglied seit"), "fieldname": "mitglied_seit", "fieldtype": "Date"},
        {"label": _("Sendung an Coop RSV"), "fieldname": "sendung_an_coop", "fieldtype": "Date"},
        {"label": _("Mitgliednr."), "fieldname": "mitglied_nr", "fieldtype": "Data"},
        {"label": _("Kostengutsprache"), "fieldname": "kostengutsprache", "fieldtype": "Check"},
        {"label": _("Nachnamen"), "fieldname": "nachname", "fieldtype": "Data"},
        {"label": _("Vornamen"), "fieldname": "vorname", "fieldtype": "Data"},
        {"label": _("Wohnort"), "fieldname": "wohnort", "fieldtype": "Data"},
        {"label": _("Vertrauensanwalt/in"), "fieldname": "vertrauensanwalt", "fieldtype": "Data"},
        {"label": _("Gruppenmandat"), "fieldname": "gruppenmandat", "fieldtype": "Check"},
        {"label": _("Doppelversicherung"), "fieldname": "doppelversicherung", "fieldtype": "Check"},
        {"label": _("Doppelversicherung bei"), "fieldname": "doppelversicherung_bei", "fieldtype": "Data"},
        {"label": _("Unterlagen bereits bei RA"), "fieldname": "unterlagen_bei_ra", "fieldtype": "Check"},
        {"label": _("Sachbearbeiter/in"), "fieldname": "sachbearbeiter", "fieldtype": "Data"},
        {"label": _("Bemerkungen"), "fieldname": "bemerkungen", "fieldtype": "Text"}
    ]

def get_data():
    return_data = []
    mandate = frappe.db.sql(
        """
            SELECT *
            FROM `tabRSVMandat`
        """,
        as_dict=True
    )

    for mandat in mandate:
        return_data.append({
            'mandat_liste': mandat.rsvmandatsliste,
            'mandat': mandat.name,
            'coop_fallnummer': mandat.fallnummer,
            'mitglied_seit': mandat.mitglied_seit,
            'sendung_an_coop': mandat.sendung_an_coop,
            'mitglied_nr': mandat.mitglied_nr,
            'kostengutsprache': mandat.kostengutsprache,
            'nachname': mandat.nachname,
            'vorname': mandat.vorname,
            'wohnort': "{0} {1}, {2} {3}".format(mandat.strasse, mandat.hausnummer, mandat.plz, mandat.ort),
            'vertrauensanwalt': mandat.anwalt,
            'gruppenmandat': 1 if mandat.rsvmandatsliste else 0,
            'doppelversicherung': mandat.doppelversicherung,
            'doppelversicherung_bei': mandat.doppelversicherung_bei,
            'unterlagen_bei_ra': mandat.unterlagen_bei_ra,
            'sachbearbeiter': "",
            'bemerkungen': mandat.notiz
        })
    
    return return_data