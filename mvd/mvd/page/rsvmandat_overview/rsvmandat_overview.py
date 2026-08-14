# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt
import frappe

@frappe.whitelist()
def get_rsvmandat_typ_counts():
    return frappe.db.sql(
        """
            SELECT
                IFNULL(NULLIF(`l`.`typ`, ''), 'Ohne Typ') AS `typ`,
                COUNT(DISTINCT `l`.`name`) AS `mandat_count`,
                COUNT(`m`.`name`) AS `mitglied_count`,
                GROUP_CONCAT(DISTINCT `l`.`name`) AS `listen`
            FROM `tabRSVMandat` AS `l`
            LEFT JOIN `tabRSVMitglied` AS `m` ON `m`.`rsvmandat` = `l`.`name`
            GROUP BY IFNULL(NULLIF(`l`.`typ`, ''), 'Ohne Typ')
            ORDER BY `mandat_count` DESC
        """,
        as_dict=True
    )