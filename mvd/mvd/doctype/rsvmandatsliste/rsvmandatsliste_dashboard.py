from __future__ import unicode_literals

from frappe import _


def get_data():
    return {
        'fieldname': 'rsvmandatsliste',
        'transactions': [
            {
                'label': _('Verknüpfungen'),
                'items': ['RSVMandat']
            }
        ]
    }
