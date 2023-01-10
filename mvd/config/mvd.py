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
                    "type": "report",
                    "name": "Mitgliederstatistik",
                    "label": _("Mitgliederstatistik"),
                    "description": _("Mitgliederstatistik"),
                    "doctype": "Mitgliedschaft",
                    "is_query_report": True
                }
            ]
        },
        {
            "label": _("Beratung"),
            "icon": "fa fa-cog",
            "items": [
                {
                    "type": "doctype",
                    "name": "Termin",
                    "label": _("Termin"),
                    "description": _("Termin")
                },
                {
                    "type": "doctype",
                    "name": "Wohnungsabgabe",
                    "label": _("Wohnungsabgabe"),
                    "description": _("Wohnungsabgabe")
                },
                {
                    "type": "doctype",
                    "name": "Onlineberatung",
                    "label": _("Onlineberatung"),
                    "description": _("Onlineberatung")
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
                    "name": "Rechnungs Jahresversand",
                    "label": _("Rechnungs Jahresversand"),
                    "description": _("Rechnungs Jahresversand")
                },
                {
                    "type": "doctype",
                    "name": "Spendenversand",
                    "label": _("Spendenversand"),
                    "description": _("Spendenversand")
                },
                {
                    "type": "doctype",
                    "name": "Massenlauf Inaktivierung",
                    "label": _("Massenlauf Inaktivierung"),
                    "description": _("Massenlauf Inaktivierung")
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
                    "type": "doctype",
                    "name": "Kunden",
                    "label": _("Kunden"),
                    "description": _("Kunden")
                }
            ]
        },
        {
            "label": _("M + W"),
            "icon": "fa fa-cog",
            "items": [
                {
                    "type": "doctype",
                    "name": "MW Abo",
                    "label": _("M+W Abo"),
                    "description": _("M+W Abo")
                },
                {
                    "type": "doctype",
                    "name": "MW Export",
                    "label": _("M+W Export"),
                    "description": _("M+W Export")
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
        },
        {
            "label": _("Finanzen"),
            "icon": "fa fa-cog",
            "items": [
                {
                    "type": "doctype",
                    "name": "CAMT Import",
                    "label": _("CAMT Importer"),
                    "description": _("CAMT Importer")
                },
                {
                    "type": "doctype",
                    "name": "Fakultative Rechnung",
                    "label": _("Fakultative Rechnungen"),
                    "description": _("Fakultative Rechnungen")
                },
                {
                    "type": "doctype",
                    "name": "Sales Invoice",
                    "label": _("Rechnungen"),
                    "description": _("Rechnungen")
                },
                {
                    "type": "doctype",
                    "name": "Payment Entry",
                    "label": _("Zahlungen"),
                    "description": _("Zahlungen")
                },
                {
                    "type": "doctype",
                    "name": "Mahnung",
                    "label": _("Mahnungen"),
                    "description": _("Mahnungen")
                },
                {
                    "type": "report",
                    "name": "Mitgliederbeitraege",
                    "label": _("Mitgliederbeitraege"),
                    "description": _("Mitgliederbeitraege"),
                    "doctype": "Mitgliedschaft",
                    "is_query_report": True
                },
                {
                    "type": "report",
                    "name": "Spendenuebersicht",
                    "label": _("Spendenuebersicht"),
                    "description": _("Spendenuebersicht"),
                    "doctype": "Fakultative Rechnung",
                    "is_query_report": True
                },
                {
                    "type": "report",
                    "name": "Guthaben",
                    "label": _("Guthabenübersicht"),
                    "description": _("Guthabenübersicht"),
                    "doctype": "Mitgliedschaft",
                    "is_query_report": True
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
                    "name": "InteressentIn Typ",
                    "label": _("Interessent*in Typ"),
                    "description": _("Interessent*in Typ")
                }
            ]
        }
    ]
