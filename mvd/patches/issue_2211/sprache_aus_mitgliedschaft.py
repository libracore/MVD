# -*- coding: utf-8 -*-
# #2211: Verfahrenssprache bestehender Mandate aus der Mitgliedschaft nachtragen (nur wo leer; nur de/fr)
from __future__ import unicode_literals
import frappe


def execute():
    frappe.reload_doc("mvd", "doctype", "mandat")
    frappe.db.sql("""UPDATE `tabMandat` AS `m`
        JOIN `tabMitgliedschaft` AS `ms` ON `ms`.`name` = `m`.`mv_mitgliedschaft`
        SET `m`.`sprache` = `ms`.`language`
        WHERE IFNULL(`m`.`sprache`, '') = '' AND `ms`.`language` IN ('de', 'fr')""")
