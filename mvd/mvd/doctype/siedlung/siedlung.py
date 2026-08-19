# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import re

class Siedlung(Document):
    def after_insert(self):
        if self.zugehoerige_gebaeude and not self.bezeichnung:
            self.bezeichnung = "{0} {1}, {2} {3}".format(
                self.zugehoerige_gebaeude[0].plz,
                self.zugehoerige_gebaeude[0].wohnort,
                self.zugehoerige_gebaeude[0].stn_label,
                self.zugehoerige_gebaeude[0].adr_number
            )
            self.save()

    def before_save(self):
        self.sortierung_zugehoerige_gebaeude()

    def validate(self):
        self.duplikat_kontrolle()

    def sortierung_zugehoerige_gebaeude(self):
        self.zugehoerige_gebaeude.sort(
            key=lambda row: (
                natural_sort_key(row.stn_label),
                natural_sort_key(row.adr_number),
                natural_sort_key(row.plz)
            )
        )

        # idx entsprechend der neuen Reihenfolge setzen
        for idx, row in enumerate(self.zugehoerige_gebaeude, start=1):
            row.idx = idx

    def duplikat_kontrolle(self):
        entries = []
        duplikate = []
        for zugehoeriges_gebaeude in self.zugehoerige_gebaeude:
            if zugehoeriges_gebaeude.adr_egaid:
                if zugehoeriges_gebaeude.adr_egaid not in entries:
                    entries.append(zugehoeriges_gebaeude.adr_egaid)
                else:
                    duplikate.append("Zeile {0} ({1})".format(zugehoeriges_gebaeude.idx, zugehoeriges_gebaeude.adr_egaid))
        if len(duplikate) > 0:
            frappe.msgprint(
                msg="Diese Siedlung enthält doppelte Adress-Einträge, siehe nachfolgende Liste:<br>{0}".format("<br>".join(duplikate)),
                title="Siedlung enthält doppelte Adress-Einträge",
                indicator="orange"
            )

def natural_sort_key(value):
    """
    Erzeugt einen Sortierschlüssel für natürliche Sortierung.

    Beispiel:
    1, 2, 3, 10, 10a, 10b, 20
    statt:
    1, 10, 10a, 10b, 2, 20, 3
    """
    value = str(value or "").lower()

    return [
        int(part) if part.isdigit() else part
        for part in re.split(r"(\d+)", value)
    ]



