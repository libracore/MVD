# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt
import frappe

@frappe.whitelist()
def get_rsvmitglied_status_counts():
    status_counts = frappe.db.sql(
        """
            SELECT
                IFNULL(`status`, 'Ohne Status') AS `status`,
                COUNT(`name`) AS `count`
            FROM `tabRSVMitglied`
            GROUP BY `status`
            ORDER BY FIELD(
                `status`,
                'Provisorisch EM',
                'Provisorisch GM',
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