# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PLZSektionZuordnung(Document):
    def validate(self):
        if self.plz_bis == 0:
            # case 1: plz wurde bereits erfasst (einzeln)
            case_1 = frappe.db.sql("""SELECT
                                        COUNT(`name`) AS `qty`
                                    FROM `tabPLZ Sektion Zuordnung`
                                    WHERE `plz` = '{plz}'""".format(plz=self.plz), as_dict=True)[0].qty
            if case_1 > 0:
                frappe.throw("Die eingetragene PLZ ({plz}) wird bereits durch eine andere Sektion verwendet.".format(plz=self.plz))
            
            # case 2: plz kommt bereits in einem range vor
            case_2 = frappe.db.sql("""SELECT
                                        COUNT(`name`) AS `qty`
                                    FROM `tabPLZ Sektion Zuordnung`
                                    WHERE `plz` <= '{plz}'
                                    AND `plz_bis` >= '{plz}'""".format(plz=self.plz), as_dict=True)[0].qty
            if case_2 > 0:
                frappe.throw("Die eingetragene PLZ ({plz}) wird bereits durch eine andere Sektion verwendet.".format(plz=self.plz))
            
            return
        else:
            # case 3: eine plz aus dem erfassten range kommt bereits in einer anderen zuordnung vor
            used_plz = []
            for plz in range(self.plz, self.plz_bis + 1):
                case_3 = frappe.db.sql("""SELECT
                                            COUNT(`name`) AS `qty`
                                        FROM `tabPLZ Sektion Zuordnung`
                                        WHERE (`plz` <= '{plz}'
                                        AND `plz_bis` >= '{plz}')
                                        OR `plz` = '{plz}'""".format(plz=plz), as_dict=True)[0].qty
                if case_3 > 0:
                    used_plz.append(str(plz))
            if len(used_plz) > 0:
                frappe.throw("Nachfolgende PLZ werden bereits durch eine andere Sektion verwendet:<br>{used_plz}".format(plz=self.plz, used_plz=("<br>").join(used_plz)))
            
            return
