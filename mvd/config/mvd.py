from __future__ import unicode_literals
from frappe import _

def get_data():
    return [
        {
            "label": _("Mitgliederverwaltung"),
            "icon": "fa fa-cog",
            "items": [
                {
                   "type": "page",
                   "name": "mvd-suchmaske",
                   "label": _("Mitgliedschaftssuche"),
                   "description": _("Mitgliedschaftssuche")
               },
               {
                    "type": "doctype",
                    "name": "MV Mitgliedschaft",
                    "label": _("MV Mitgliedschaft"),
                    "description": _("MV Mitgliedschaft")
                },
                {
                    "type": "doctype",
                    "name": "MW Abo",
                    "label": _("M+W Abo"),
                    "description": _("M+W Abo")
                }
            ]
        },
        {
            "label": _("Werkzeuge"),
            "icon": "fa fa-cog",
            "items": [
                {
                    "type": "doctype",
                    "name": "Arbeits Backlog",
                    "label": _("Arbeits-Backlog"),
                    "description": _("Zu erledigende Aufgaben")
                },
                {
                    "type": "doctype",
                    "name": "MV Jahresversand",
                    "label": _("Jahresversand"),
                    "description": _("MV Jahresversand")
                },
                {
                    "type": "doctype",
                    "name": "CAMT Import",
                    "label": _("CAMT Importer"),
                    "description": _("CAMT Importer")
                },
                {
                    "type": "doctype",
                    "name": "MV Help Links",
                    "label": _("Hilfe Verknüpfungen"),
                    "description": _("Hilfe Verknüpfungen direkt zur MVD Wiki")
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
                }
            ]
        },
        {
            "label": _("Verbands-Stammdaten"),
            "icon": "fa fa-cog",
            "items": [
                {
                    "type": "doctype",
                    "name": "Sektion",
                    "label": _("Sektionen"),
                    "description": _("Sektions Einstellungen")
                },
                {
                    "type": "doctype",
                    "name": "Region",
                    "label": _("Regionen"),
                    "description": _("Regions Einstellungen")
                },
                {
                    "type": "doctype",
                    "name": "PLZ Sektion Zuordnung",
                    "label": _("Zuordnung PLZ <-> Sektion"),
                    "description": _("Zuordnung PLZ <-> Sektion")
                }
            ]
        }
    ]
