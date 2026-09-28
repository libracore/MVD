# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe

angezeigte_status = [
    'Provisorisch EM',
    'Provisorisch GM',
    'Vorprüfung',
    'Geprüft',
    'manuelle Vergabe',
    'Eingereicht'
]

@frappe.whitelist()
def get_rsvmitglied_status_counts():
    rows = frappe.db.sql(
        """
            SELECT
                `status` AS `status`,
                COUNT(`name`) AS `count`
            FROM `tabRSVMitglied`
            WHERE `status` IN ({angez_status})
            GROUP BY `status`
        """.format(angez_status=', '.join(['%s'] * len(angezeigte_status))),
        tuple(angezeigte_status),
        as_dict=True
    )

    counts = {}
    for row in rows:
        counts[row.status] = row.count

    # alle angezeigten Status in fixer Reihenfolge zurückgeben, auch mit Anzahl 0
    status_counts = []
    for status in angezeigte_status:
        status_counts.append({
            'status': status,
            'count': counts.get(status, 0)
        })

    neue_rsvmitglieder = frappe.db.sql(
        """
            SELECT COUNT(`name`) AS `count`
            FROM `tabRSVMitglied`
            WHERE `status` IN ('Provisorisch EM','Provisorisch GM')
            AND `rsvmandat` IS NULL
        """,
        as_dict=True
    )

    return {
        'status_counts': status_counts,
        'neue_rsvmitglieder': neue_rsvmitglieder[0].count
    }
