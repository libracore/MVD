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
        {"label": _("Mandat"), "fieldname": "mandat", "fieldtype": "Link", "options": "RSVMandat"},
        {"label": _("RSVMitglied"), "fieldname": "rsv_mitglied", "fieldtype": "Link", "options": "RSVMitglied"},
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
    rsv_mitglieder = frappe.db.sql(
        """
            SELECT *
            FROM `tabRSVMitglied`
        """,
        as_dict=True
    )

    for rsv_mitglied in rsv_mitglieder:
        return_data.append({
            'mandat': rsv_mitglied.rsvmandat,
            'rsv_mitglied': rsv_mitglied.name,
            'coop_fallnummer': rsv_mitglied.fallnummer,
            'mitglied_seit': rsv_mitglied.mitglied_seit,
            'sendung_an_coop': rsv_mitglied.sendung_an_coop,
            'mitglied_nr': rsv_mitglied.mitglied_nr,
            'kostengutsprache': rsv_mitglied.kostengutsprache,
            'nachname': rsv_mitglied.nachname,
            'vorname': rsv_mitglied.vorname,
            'wohnort': "{0} {1}, {2} {3}".format(rsv_mitglied.strasse, rsv_mitglied.hausnummer, rsv_mitglied.plz, rsv_mitglied.ort),
            'vertrauensanwalt': rsv_mitglied.anwalt,
            'gruppenmandat': 1 if rsv_mitglied.rsvmandat else 0,
            'doppelversicherung': rsv_mitglied.doppelversicherung,
            'doppelversicherung_bei': rsv_mitglied.doppelversicherung_bei,
            'unterlagen_bei_ra': rsv_mitglied.unterlagen_bei_ra,
            'sachbearbeiter': "",
            'bemerkungen': rsv_mitglied.notiz
        })
    
    return return_data