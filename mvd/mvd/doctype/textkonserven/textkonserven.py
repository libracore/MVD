# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Textkonserven(Document):
    def validate(self):
        self.check_duplikat()
    
    def check_duplikat(self):
        qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabTextkonserven`
                                WHERE `sektion_id` = '{sektion_id}'
                                AND `rechnungstyp` = '{rechnungstyp}'
                                AND `mitgliedtyp_c` = '{mitgliedtyp_c}'
                                AND `reduzierte_mitgliedschaft` = '{reduzierte_mitgliedschaft}'
                                AND `name` != '{name}'""".format(name=self.name, sektion_id=self.sektion_id, rechnungstyp=self.rechnungstyp, mitgliedtyp_c=self.mitgliedtyp_c, reduzierte_mitgliedschaft=self.reduzierte_mitgliedschaft), as_dict=True)[0].qty
        if qty > 0:
            frappe.throw("Es existiert bereits eine Vorlage mit den selben Atributen")
