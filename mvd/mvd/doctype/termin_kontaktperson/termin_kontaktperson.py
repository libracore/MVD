# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class TerminKontaktperson(Document):
    def validate(self):
        if not self.user:
            frappe.throw("Bitte mind. einen libracore User zuweisen")
        else:
            if len(self.user) < 2:
                user = self.user[0].user
                
                # überprüfung ob der user bereits verknüpft wurde
                verknuepfungen = frappe.db.sql("""
                                                    SELECT COUNT(`name`) AS `qty` FROM `tabTermin Kontaktperson Multi User`
                                                    WHERE `user` = '{user}'
                                                """.format(user=user), as_dict=True)
                if int(verknuepfungen[0].qty) > 1:
                    vorhandene_einzel_verknuepfung = frappe.db.sql("""
                                                                    SELECT `parent` FROM (
                                                                        SELECT `parent` FROM (
                                                                            SELECT COUNT(`name`) AS `qty`, `parent` FROM `tabTermin Kontaktperson Multi User`
                                                                            GROUP BY `parent`
                                                                        ) AS `x`
                                                                        WHERE `qty` = 1
                                                                    ) AS `y`
                                                                    WHERE `parent` IN (
                                                                        SELECT `parent` FROM `tabTermin Kontaktperson Multi User`
                                                                        WHERE `user` = '{user}'
                                                                    )
                                                                """.format(user=user), as_dict=True)
                    if len(vorhandene_einzel_verknuepfung) > 0:
                        frappe.throw("""{0} ist bereits mit <a href="https://libracore.mieterverband.ch/desk#Form/Termin Kontaktperson/{1}">{1}</a> verknüpft.<br>Es dürfen keine doppel Einzelverknüpfungen existieren.""".format(user, vorhandene_einzel_verknuepfung[0].parent))
