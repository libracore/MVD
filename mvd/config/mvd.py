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
                    "name": "Mitgliedschaft",
                    "label": _("Mitgliedschaft"),
                    "description": _("Mitgliedschaft")
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
                    "name": "Massenlauf Inaktivierung",
                    "label": _("Massenlauf Inaktivierung"),
                    "description": _("Massenlauf Inaktivierung")
                },
                {
                    "type": "doctype",
                    "name": "CAMT Import",
                    "label": _("CAMT Importer"),
                    "description": _("CAMT Importer")
                },
                {
                    "type": "doctype",
                    "name": "Mahnung",
                    "label": _("Mahnungen"),
                    "description": _("Mahnungen")
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
            "label": _("Faktura Kunden"),
            "icon": "fa fa-cog",
            "items": [
                {
                   "type": "page",
                   "name": "mvd-suchmaske",
                   "label": _("Kundensuche"),
                   "description": _("Kundensuche")
                },
                {
                    "type": "doctype",
                    "name": "Kunden",
                    "label": _("Kunden"),
                    "description": _("Kunden")
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
                }
            ]
        },
        {
            "label": _("Adresspflege"),
            "icon": "fa fa-cog",
            "items": [
                {
                    "type": "doctype",
                    "name": "Retouren",
                    "label": _("Retouren"),
                    "description": _("Retouren")
                },
                {
                    "type": "doctype",
                    "name": "MW",
                    "label": _("MW"),
                    "description": _("MW")
                }
            ]
        }
    ]
