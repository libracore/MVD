# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe


def execute():
    columns = ['camt_import', 'docstatus', 'camt_status']
    indexes = {}
    for row in frappe.db.sql('SHOW INDEX FROM `tabPayment Entry`', as_dict=True):
        indexes.setdefault(row.Key_name, {})[int(row.Seq_in_index)] = row.Column_name
    
    if any([parts.get(position + 1) for position in range(len(columns))] == columns
           for parts in indexes.values()):
        return
    frappe.db.add_index('Payment Entry', columns, 'idx_camt_import_status')
