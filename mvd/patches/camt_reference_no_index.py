# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe


def execute():
    for row in frappe.db.sql('SHOW INDEX FROM `tabPayment Entry`', as_dict=True):
        if int(row.Seq_in_index) == 1 and row.Column_name == 'reference_no':
            return
    frappe.db.add_index('Payment Entry', ['reference_no'], 'idx_camt_reference_no')
