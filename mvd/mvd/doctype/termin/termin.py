# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Termin(Document):
    def validate(self):
        # check if default Sektion = MVBE
        default_sektion = frappe.db.sql("""SELECT `for_value` FROM `tabUser Permission` WHERE `allow` = 'Sektion' AND `user` = '{user}' AND `is_default` = 1""".format(user=frappe.session.user), as_dict=True)
        if len(default_sektion) > 0:
            if default_sektion[0].for_value == 'MVBE':
                frappe.throw("Bitte nutzen Sie die Beratungen anstelle eines Termins.")
        
        if not self.mv_mitgliedschaft:
            frappe.throw("Termine müssen immer einer Mitgliedschaft zugewiesen sein")
        self.sektion_id = frappe.get_value("Mitgliedschaft", self.mv_mitgliedschaft, "sektion_id")
