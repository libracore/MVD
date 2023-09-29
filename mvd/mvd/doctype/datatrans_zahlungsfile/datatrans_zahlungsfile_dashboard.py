from __future__ import unicode_literals

from frappe import _
import frappe


def get_data():
    return {
        'fieldname': 'datatrans_zahlungsfile',
        'transactions': [
            {
                'label': _('Reports'),
                'items': ['Datatrans Report']
            }
        ]
    }
