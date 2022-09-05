from __future__ import unicode_literals

from frappe import _


def get_data():
    return {
        'heatmap': True,
        'heatmap_message': _('Diese Heatmap zeigt alle Interaktionen mit diesem Kunden im vergangenen Jahr'),
        'fieldname': 'mv_kunde',
        'transactions': [
            {
                'label': _('Rechnungswesen'),
                'items': ['Sales Invoice', 'Mahnung', 'Payment Entry']
            }
        ]
    }
