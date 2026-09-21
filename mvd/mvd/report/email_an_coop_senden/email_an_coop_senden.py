# Copyright (c) 2013, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {"label": _("RSV Mitglied"), "fieldname": "name", "fieldtype": "Link", "options": "RSVMitglied", "width": 180},
        { "label": _("Mitglied-Nr."), "fieldname": "mitglied_nr", "fieldtype": "Data", "width": 110},
        { "label": _("Vorname"), "fieldname": "vorname", "fieldtype": "Data", "width": 120},
        { "label": _("Nachname"), "fieldname": "nachname", "fieldtype": "Data", "width": 120},
        { "label": _("RSV Mandat"), "fieldname": "rsvmandat", "fieldtype": "Link", "options": "RSVMandat", "width": 150},
        { "label": _("Anwält*in"), "fieldname": "anwalt", "fieldtype": "Link", "options": "Termin Kontaktperson", "width": 160},
        { "label": _("Aktion"), "fieldname": "action_button", "fieldtype": "Data", "width": 180}
    ]

    data = frappe.db.sql("""
        SELECT 
            m.name,
            m.mitglied_nr,
            m.vorname,
            m.nachname,
            m.rsvmandat,
            rm.anwalt
        FROM 
            `tabRSVMitglied` m
        INNER JOIN 
            `tabRSVMandat` rm ON m.rsvmandat = rm.name
        WHERE 
            (m.sendung_an_coop = 0 OR m.sendung_an_coop IS NULL)
            AND rm.anwalt IS NOT NULL 
            AND rm.anwalt != ''
        ORDER BY 
            m.modified DESC
    """, as_dict=True)

    for row in data:
        row["action_button"] = f'''<button class="btn btn-xs btn-primary btn-send-coop-email" data-name="{row["name"]}">
            <i class="fa fa-envelope"></i> E-Mail an Coop senden
        </button>'''

    return columns, data