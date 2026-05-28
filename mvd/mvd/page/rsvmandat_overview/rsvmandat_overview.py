# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt
import frappe

@frappe.whitelist()
def get_rsvmandat_status_counts():
    return frappe.db.sql(
        """
            SELECT
                IFNULL(`status`, 'Ohne Status') AS `status`,
                COUNT(`name`) AS `count`
            FROM `tabRSVMandat`
            GROUP BY `status`
            ORDER BY FIELD(
                `status`,
                'Provisorisch',
                'Vorprüfung',
                'Geprüft',
                'manuelle Vergabe',
                'Eingereicht',
                'Vergeben',
                'Abgelehnt',
                'Abgeschlossen',
                'Rückzug',
                'keine Antwort',
                'Doppelversicherung'
            )
        """,
        as_dict=True
    )