from __future__ import unicode_literals

from frappe import _


def get_data():
    return {
        'heatmap': True,
        'heatmap_message': _('Diese Heatmap zeigt alle Interaktionen mit dieser Mitgliedschaft im vergangenen Jahr'),
        'fieldname': 'mv_mitgliedschaft',
        # ~ 'non_standard_fieldnames': {
            # ~ 'Mahnung': 'hidden_linking'
        # ~ },
        'transactions': [
            {
                'label': _('Termine / Beratungen'),
                'items': ['Termin']
            },
            {
                'label': _('Externe Korrespondenz'),
                'items': ['Korrespondenz', 'Sales Invoice', 'Fakultative Rechnung', 'Mahnung']
            },
            {
                'label': _('Zu erledigen'),
                'items': ['Arbeits Backlog']
            }
        ]
    }
