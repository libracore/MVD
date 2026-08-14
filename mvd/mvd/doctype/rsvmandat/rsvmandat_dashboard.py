from __future__ import unicode_literals

from frappe import _


def get_data():
    return {
        'fieldname': 'rsvmandat',
        'transactions': [
            {
                'label': _('Verknüpfungen'),
                'items': ['RSVMitglied']
            }
        ]
    }
