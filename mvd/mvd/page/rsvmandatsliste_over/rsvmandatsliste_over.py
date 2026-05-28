# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt
import frappe

@frappe.whitelist()
def get_rsvmandatsliste_typ_counts():
    return frappe.db.sql(
        """
            SELECT
                IFNULL(NULLIF(`l`.`typ`, ''), 'Ohne Typ') AS `typ`,
                COUNT(DISTINCT `l`.`name`) AS `listen_count`,
                COUNT(`m`.`name`) AS `mandat_count`,
                GROUP_CONCAT(DISTINCT `l`.`name`) AS `listen`
            FROM `tabRSVMandatsliste` AS `l`
            LEFT JOIN `tabRSVMandat` AS `m` ON `m`.`rsvmandatsliste` = `l`.`name`
            GROUP BY IFNULL(NULLIF(`l`.`typ`, ''), 'Ohne Typ')
            ORDER BY `listen_count` DESC
        """,
        as_dict=True
    )