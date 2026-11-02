# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.data import now_datetime

TYP_SPALTEN = {
    'Rechtsschutzversicherung': 'rsv',
    'Solidaritätsfonds': 's'
}

@frappe.whitelist()
def get_status_uebersicht():
    # Eine Abfrage; Sektionstrennung über User Permissions (get_list)
    anzahl = {}
    for row in frappe.get_list('Mandat', fields=['status', 'typ', 'count(`name`) as anzahl'], group_by='status, typ', order_by='status'):
        status = anzahl.setdefault(row.status or '', {'rsv': 0, 's': 0, 'ohne_typ': 0})
        status[TYP_SPALTEN.get(row.typ, 'ohne_typ')] += row.anzahl

    # Reihenfolge wie im Select-Feld, Status ohne Mandate mit 0
    status_optionen = [s.strip() for s in (frappe.get_meta('Mandat').get_field('status').options or '').split('\n') if s.strip()]
    status_reihenfolge = status_optionen + [s for s in anzahl if s not in status_optionen]  # Altdaten, leerer Status

    status_liste = []
    total = {'rsv': 0, 's': 0, 'ohne_typ': 0}
    for status in status_reihenfolge:
        werte = anzahl.get(status, {'rsv': 0, 's': 0, 'ohne_typ': 0})
        status_liste.append(dict(werte, status=status, summe=sum(werte.values())))
        for spalte in total:
            total[spalte] += werte[spalte]

    return {
        'datenstand': now_datetime().strftime("%d.%m.%Y %H:%M:%S"),
        'status_liste': status_liste,
        'total': dict(total, summe=sum(total.values())),
        'hat_ohne_typ': total['ohne_typ'] > 0
    }
