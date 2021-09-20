from __future__ import unicode_literals
from frappe import _

def get_data():
    return [
        {
            "label": _("Mitgliederverwaltung"),
            "icon": "fa fa-cog",
            "items": [
                {
                    "type": "doctype",
                    "name": "MV Mitgliedschaft",
                    "label": _("MV Mitgliedschaft"),
                    "description": _("MV Mitgliedschaft")
                }
            ]
        },
        {
            "label": _("Stammdaten"),
            "icon": "fa fa-cog",
            "items": [
                {
                    "type": "doctype",
                    "name": "Customer",
                    "label": _("Kunden"),
                    "description": _("Customers")
                },
                {
                    "type": "doctype",
                    "name": "Address",
                    "label": _("Adressen"),
                    "description": _("Adressen")
                },
                {
                    "type": "doctype",
                    "name": "Contact",
                    "label": _("Contact"),
                    "description": _("Kontaktpersonen")
                },
                {
                    "type": "doctype",
                    "name": "Sektion",
                    "label": _("Sektions Einstellungen"),
                    "description": _("Sektions Einstellungen")
                }
            ]
        }
    ]
