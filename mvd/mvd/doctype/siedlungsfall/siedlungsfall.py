# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import datetime
from frappe.utils.data import today

class Siedlungsfall(Document):
    def before_insert(self):
        if not self.flags.from_import:
            self.get_mitgliedschaften()
            self.creation_date = today()
    
    def get_mitgliedschaften(self, manually=False):
        if not self.siedlung: return

        if manually: self.mitgliedschaften = []

        affected_adr_egaids = frappe.db.sql(
            """
                SELECT `adr_egaid`
                FROM `tabZugehoerige Gebaeude`
                WHERE `parent` = '{siedlung}'
            """.format(siedlung=self.siedlung),
            as_dict=True
        )

        for affected_adr_egaid in affected_adr_egaids:
            mitgliedschaften = frappe.db.sql(
                """
                    SELECT
                        `name`,
                        `mitglied_nr`,
                        `eintrittsdatum`,
                        `vorname_1`,
                        `nachname_1`
                    FROM `tabMitgliedschaft`
                    WHERE `adr_egaid` = '{adr_egaid}'
                """.format(adr_egaid=affected_adr_egaid.adr_egaid),
                as_dict=True
            )

            for mitgliedschaft in mitgliedschaften:
                mitgl_row = self.append("mitgliedschaften", {})
                mitgl_row.mv_mitgliedschaft = mitgliedschaft.name
                mitgl_row.mitglied_nr = mitgliedschaft.mitglied_nr
                mitgl_row.mitglied_name = "{0} {1}".format(mitgliedschaft.vorname_1, mitgliedschaft.nachname_1)
                mitgl_row.letzte_beratung = get_letzte_beratung(mitgliedschaft.name)
                mitgl_row.letztes_mandat = get_letztes_mandat(mitgliedschaft.name)
                mitgl_row.eintrittsdatum = mitgliedschaft.eintrittsdatum

        if manually:
            self.save()

def get_letzte_beratung(mitglied):
    beratungen = frappe.db.sql(
        """
            SELECT
                `start_date`,
                `beratungskategorie`
            FROM `tabBeratung`
            WHERE `mv_mitgliedschaft` = '{0}'
            ORDER BY `start_date` DESC
            LIMIT 1
        """.format(mitglied),
        as_dict=True
    )

    if len(beratungen) > 0:
        return "{0}, {1}".format(format_date(str(beratungen[0].start_date)), beratungen[0].beratungskategorie or '-')
    
    return ""

def get_letztes_mandat(mitglied):
    mandate = frappe.db.sql(
            """
                SELECT
                    `name`,
                    `creation`,
                    `status`
                FROM `tabRSVMitglied`
                WHERE `mv_mitgliedschaft` = '{0}'
                ORDER BY `creation` DESC
                LIMIT 1
            """.format(mitglied),
            as_dict=True
        )
    
    if len(mandate) > 0:
        themen = frappe.db.sql(
            """
                SELECT `thema`
                FROM `tabRSV Thema MultiTable`
                WHERE `parent` = '{0}'
            """.format(mandate[0].name),
            as_dict=True
        )
        thema = '-'
        if len(themen):
            thema = themen[0].thema
        
        return "{0}, {1}, {2}".format(format_date(str(mandate[0].creation)), thema, mandate[0].status)
    
    return ""

def format_date(date_string):
    return datetime.fromisoformat(date_string).strftime("%d.%m.%Y")

def update_mitglied_in_siedlungsfall(mitglied):
    affected_rows = frappe.db.sql(
        """
            SELECT `name`
            FROM `tabSiedlungsfall Mitgliedschaften`
            WHERE `mv_mitgliedschaft` = '{0}'
        """.format(mitglied),
        as_dict=True
    )

    if len(affected_rows) > 0:
        letzte_beratung_string = get_letzte_beratung(mitglied)
        letztes_mandat_string = get_letztes_mandat(mitglied)

        for affected_row in affected_rows:
            frappe.db.sql(
                """
                    UPDATE `tabSiedlungsfall Mitgliedschaften`
                    SET
                        `letzte_beratung` = '{letzte_beratung}',
                        `letztes_mandat` = '{letztes_mandat}'
                    WHERE `name` = '{id}'
                """.format(
                    id=affected_row.name,
                    letzte_beratung=letzte_beratung_string,
                    letztes_mandat=letztes_mandat_string
                )
            )
        frappe.db.commit()
    return