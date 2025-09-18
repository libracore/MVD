from __future__ import unicode_literals

from frappe import _


def get_data():
    return {
        'fieldname': 'mrj',
        'transactions': [
            {
                'label': _('Sektionsdaten'),
                'items': ['MRJ Sektions Selektion']
            }
        ]
    }
