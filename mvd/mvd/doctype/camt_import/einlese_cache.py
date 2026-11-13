# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from contextlib import contextmanager
import frappe

"""
    Cache Methoden zum Kontodetails für ungebuchte CAMT-Zahlungen innerhalb einer Transaktion wiederzuverwenden
"""

@contextmanager
def einlese_cache(camt_import):
    previous = frappe.flags.get('camt_einlese_cache')
    if previous:
        if previous['camt_import'] != camt_import:
            frappe.throw('Zwei CAMT-Importe dürfen nicht im selben Einleseschritt vermischt werden.')
        yield
        return
    
    frappe.flags.camt_einlese_cache = {'camt_import': camt_import, 'konten': {}, 'debitoren': {}}

    try:
        yield
    finally:
        frappe.flags.camt_einlese_cache = previous

def leere_einlese_cache(camt_import):
    cache = frappe.flags.get('camt_einlese_cache')
    if cache and cache['camt_import'] == camt_import:
        cache['konten'].clear()
        cache['debitoren'].clear()

def befuelle_kontodetails(payment, camt_import):
    cache = frappe.flags.get('camt_einlese_cache')
    if not cache or cache['camt_import'] != camt_import:
        return
    
    from erpnext.accounts.party import get_party_account
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_account_details

    party_key = (payment.company, payment.party_type, payment.party)
    if party_key not in cache['debitoren']:
        cache['debitoren'][party_key] = get_party_account(payment.party_type, payment.party, payment.company)
    
    payment.paid_from = cache['debitoren'][party_key]

    for field in ('paid_from', 'paid_to'):
        account = payment.get(field)
        key = (payment.company, account, str(payment.posting_date), payment.get('cost_center'))
        if key not in cache['konten']:
            cache['konten'][key] = get_account_details(account, payment.posting_date, payment.get('cost_center'))
        
        details = cache['konten'][key]
        payment.set(field + '_account_currency', details.account_currency)
        payment.set(field + '_account_balance', details.account_balance)

def vor_validierung(payment, event=None):
    if (payment.get('__islocal') and payment.docstatus == 0 and payment.payment_type == 'Receive' and payment.party_type == 'Customer' and not payment.get('references') and not payment.get('deductions')):
        befuelle_kontodetails(payment, payment.get('camt_import'))
