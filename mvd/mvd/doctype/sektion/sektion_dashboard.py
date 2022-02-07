from __future__ import unicode_literals

from frappe import _


def get_data():
    return {
        'fieldname': 'sektion_id',
        'transactions': [
            {
                'label': _('Vorlagen'),
                'items': ['Terminkategorie', 'Druckvorlage']
            }
        ]
    }
