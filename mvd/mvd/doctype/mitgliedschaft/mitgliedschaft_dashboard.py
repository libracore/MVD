from __future__ import unicode_literals

from frappe import _
import frappe


def get_data():
    return {
        'heatmap': True,
        'heatmap_message': _('Diese Heatmap zeigt alle Interaktionen mit dieser Mitgliedschaft im vergangenen Jahr'),
        'fieldname': 'mv_mitgliedschaft',
        "non_standard_fieldnames": {
			'Kampagne': 'mitglied',
            'PayrexxWebhooks': 'mitglied_id',
		},
        'transactions': [
            {
                'label': _('Termine / Beratungen'),
                'items': ['Beratung', 'Wohnungsabgabe', 'Termin'],
            },
            {
                'label': _('Externe Korrespondenz'),
                'items': ['Korrespondenz']
            },
            {
                'label': _('Rechnungswesen'),
                'items': ['Sales Invoice', 
                          'Fakultative Rechnung', 
                          'Mahnung', 
                          'Payment Entry', 
                          'PayrexxWebhooks'
                          ]
            },
            {
                'label': _('Zu erledigen'),
                'items': ['Arbeits Backlog']
            },
            {
                'label': _('Adresspflege'),
                'items': ['Retouren']
            },
            {
                'label': _('Kampagnen'),
                'items': ['Kampagne']
            },
        ]
    }
