from __future__ import unicode_literals

from frappe import _


def get_data():
    return {
        'heatmap': True,
        'heatmap_message': _('Diese Heatmap zeigt alle Interaktionen mit dieser Mitgliedschaft im vergangenen Jahr'),
        'fieldname': 'mv_mitgliedschaft',
        'transactions': [
            {
                'label': _('Beratung'),
                'items': ['MV Beratung']
            },
            {
                'label': _('Externe Korrespondenz'),
                'items': ['MV Korrespondenz']
            }
        ]
    }
