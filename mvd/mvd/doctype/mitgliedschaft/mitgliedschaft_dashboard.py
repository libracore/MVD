from __future__ import unicode_literals

from frappe import _
import frappe


def get_data():
    bootinfo = frappe.sessions.get()
    termine_beratungen = ['Termin', 'Wohnungsabgabe']
    if bootinfo.default_sektion == "MVBE":
        termine_beratungen = ['Beratung', 'Wohnungsabgabe']
    return {
        'heatmap': True,
        'heatmap_message': _('Diese Heatmap zeigt alle Interaktionen mit dieser Mitgliedschaft im vergangenen Jahr'),
        'fieldname': 'mv_mitgliedschaft',
        'transactions': [
            {
                'label': _('Termine / Beratungen'),
                'items': termine_beratungen,
            },
            {
                'label': _('Externe Korrespondenz'),
                'items': ['Korrespondenz']
            },
            {
                'label': _('Rechnungswesen'),
                'items': ['Sales Invoice', 'Fakultative Rechnung', 'Mahnung', 'Payment Entry']
            },
            {
                'label': _('Zu erledigen'),
                'items': ['Arbeits Backlog']
            },
            {
                'label': _('Service Plattform'),
                'items': ['Service Platform Queue', 'Service Plattform Log']
            },
            {
                'label': _('Adresspflege'),
                'items': ['Retouren']
            }
        ]
    }
