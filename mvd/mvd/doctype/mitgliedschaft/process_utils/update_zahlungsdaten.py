# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, getdate, now
from mvd.mvd.doctype.druckvorlage.druckvorlage import get_druckvorlagen
from mvd.mvd.doctype.mitgliedschaft.utils import create_korrespondenz

"""
    Dieses File enthält alle Funktionen damit die Zahlungsrelevanten Daten auf der Mitgliedschaft
    aktualisiert/gesetzt werden. Dies beinhaltet das Zahlungsdatum der Mitgliedschaft, 
    das Zahlungsdatum der HV sowie das höchste bezahlte Mitgliedschafts- und HV-Jahr.

    Wenn durch die Zahlung der Beitritt erfolgt, werden die Beitrittsrelevanten Daten gesetzt,
    sowie das Begrüssungsschreiben erzeugt.
    Die Beitrittsrelevanten Daten beinhalten das Beitrittsdatum sowie einen Eintrag in der Status-Historie.

    Das Zahlungsdatum (Mitgliedschaft sowie HV) ist:
    - Bei einer POS-Bezahlung das Buchungsdatum der SINV
    - Bei einer Bankzahlung das Buchungsdatum des PE

    Das Beitrittsdatum (bei einem Beitritt durch Bezahlung) entspricht dem ersten Zahlungsdatum.
"""

@frappe.whitelist()
def run(mitglied_id):
    mitgliedschaft(mitglied_id)
    hv(mitglied_id)

def mitgliedschaft(mitglied_id):
    def get_highest_mitgliedschafts_jahr_sinv():
        sinv = frappe.db.sql(
            """
                SELECT
                    `name`,
                    `is_pos`,
                    `posting_date`,
                    `mitgliedschafts_jahr`
                FROM `tabSales Invoice`
                WHERE `docstatus` = 1
                AND `ist_mitgliedschaftsrechnung` = 1
                AND `mv_mitgliedschaft` = '{mitglied_id}'
                AND `status` = 'Paid'
                ORDER BY `mitgliedschafts_jahr` DESC
                LIMIT 1
            """.format(mitglied_id=mitglied_id),
            as_dict=True
        )
        return sinv[0] if sinv else None

    def get_pe_reference_date(sinv):
        pe = frappe.db.sql(
            """
                SELECT
                    `parent`
                FROM `tabPayment Entry Reference`
                WHERE `reference_doctype` = 'Sales Invoice'
                AND `reference_name` = '{sinv}' 
                AND `docstatus` = 1
                ORDER BY `creation` DESC
                LIMIT 1
            """.format(sinv=sinv),
            as_dict=True
        )
        if not pe:
            return None

        return frappe.db.get_value("Payment Entry", pe[0].parent, 'reference_date') or None

    def create_zahlungseingang_change_log_row():
        idx = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabStatus Change` WHERE `parent` = '{0}'""".format(mitglied_id), as_dict=True)[0].qty + 1
        change_log_row = frappe.get_doc({
            "doctype": "Status Change",
            "parent": mitglied_id,
            "parentfield": "status_change",
            "parenttype": "Mitgliedschaft",
            "datum": now(),
            "status_alt": mitglieddaten.get("status_c"),
            "status_neu": 'Regulär',
            "grund": 'Zahlungseingang',
            "idx": idx
        }).insert()
        return

    def get_and_set_mitgliednr():
        from mvd.mvd.doctype.mitglied_main_naming.mitglied_main_naming import create_new_number
        try:
            mitglied_nr = create_new_number(id=mitglied_id)['nr']
            frappe.db.set_value("Mitgliedschaft", mitglied_id, 'mitglied_nr', mitglied_nr)
        except Exception as err:
            frappe.log_error("Mitgliednummer für Mitglied {0} konnte nicht bezogen werden".format(mitglied_id), 'get_and_set_mitgliednr')
            pass
        return

    def get_prozess_relevante_mitglieddaten():
        return frappe.db.get_value(
            "Mitgliedschaft",
            mitglied_id,
            [
                "bezahltes_mitgliedschaftsjahr",
                "eintrittsdatum",
                "status_c",
                "sektion_id",
                "mitgliedtyp_c",
                "language"
            ],
            as_dict=True
        )

    sinv = get_highest_mitgliedschafts_jahr_sinv()
    if not sinv:
        return

    mitglieddaten = get_prozess_relevante_mitglieddaten()

    if cint(sinv.is_pos) == 1:
        bezahltes_mitgliedschaftsjahr = cint(sinv.mitgliedschafts_jahr)
        if bezahltes_mitgliedschaftsjahr < 1:
            bezahltes_mitgliedschaftsjahr = cint(getdate(sinv.posting_date).year)
        datum_zahlung_mitgliedschaft = sinv.posting_date
    else:
        datum_zahlung_mitgliedschaft = get_pe_reference_date(sinv.name)
        if not datum_zahlung_mitgliedschaft:
            # Ist keine POS-Sinv und beseitzt kein PE
            return
        
        bezahltes_mitgliedschaftsjahr = cint(sinv.mitgliedschafts_jahr)
        if bezahltes_mitgliedschaftsjahr < 1:
            bezahltes_mitgliedschaftsjahr = cint(getdate(datum_zahlung_mitgliedschaft).year)

    # Setze datum_zahlung_mitgliedschaft in Mitgliedschaft
    frappe.db.set_value("Mitgliedschaft", mitglied_id, "datum_zahlung_mitgliedschaft", datum_zahlung_mitgliedschaft)

    # Setze bezahltes_mitgliedschaftsjahr in Mitgliedschaft wenn der DB-Wert älter ist
    if cint(mitglieddaten.get("bezahltes_mitgliedschaftsjahr")) < bezahltes_mitgliedschaftsjahr:
        frappe.db.set_value("Mitgliedschaft", mitglied_id, "bezahltes_mitgliedschaftsjahr", bezahltes_mitgliedschaftsjahr)

    # Setze Eintrittsdatum = Zahldatum wenn der Eintritt noch nicht erfolgt ist
    if not mitglieddaten.get("eintrittsdatum"):
        frappe.db.set_value("Mitgliedschaft", mitglied_id, "eintrittsdatum", datum_zahlung_mitgliedschaft)
        # Prüfe Notwendigkeit Status-Wechsel durch Eintritt
        if mitglieddaten.get("status_c") in ('Anmeldung', 'Online-Anmeldung', 'Interessent*in'):
            # Führe Status-Wechsel durch Eintritt aus
            frappe.db.set_value("Mitgliedschaft", mitglied_id, "status_c", "Regulär")
            create_zahlungseingang_change_log_row()
            # Erstelle Begrüssungsschreiben und setze zugehörige Werte in Mitgliedschaft
            druckvorlage = get_druckvorlagen(
                sektion=mitglieddaten.get("sektion_id"),
                dokument='Begrüssung mit Ausweis',
                mitgliedtyp=mitglieddaten.get("mitgliedtyp_c"),
                language=mitglieddaten.get("language")
            )['default_druckvorlage'] # type: ignore
            begruessung_massendruck_dokument = create_korrespondenz(mitglied_id, druckvorlage=druckvorlage, titel='Begrüssung (Autom.)')
            frappe.db.set_value(
                "Mitgliedschaft",
                mitglied_id,
                {
                    'begruessung_massendruck': 1,
                    'begruessung_via_zahlung': 1,
                    'begruessung_massendruck_dokument': begruessung_massendruck_dokument
                }
            )
            # Erzeugung Mitglied-Nr
            get_and_set_mitgliednr()
            return

def hv(mitglied_id):
    def get_highest_hv_jahr_sinv():
        sinv = frappe.db.sql(
            """
                SELECT
                    `name`,
                    `is_pos`,
                    `posting_date`,
                    `mitgliedschafts_jahr`
                FROM `tabSales Invoice`
                WHERE `docstatus` = 1
                AND `ist_hv_rechnung` = 1
                AND `mv_mitgliedschaft` = '{mitglied_id}'
                AND `status` = 'Paid'
                ORDER BY `posting_date` DESC
                LIMIT 1
            """.format(mitglied_id=mitglied_id),
            as_dict=True
        )
        return sinv[0] if sinv else None

    def get_pe_reference_date(sinv):
        pe = frappe.db.sql(
            """
                SELECT
                    `parent`
                FROM `tabPayment Entry Reference`
                WHERE `reference_doctype` = 'Sales Invoice'
                AND `reference_name` = '{sinv}' 
                AND `docstatus` = 1
                ORDER BY `creation` DESC
                LIMIT 1
            """.format(sinv=sinv),
            as_dict=True
        )
        if not pe:
            return None

        return frappe.db.get_value("Payment Entry", pe[0].parent, 'reference_date') or None

    sinv = get_highest_hv_jahr_sinv()
    if not sinv:
        return

    if cint(sinv.is_pos) == 1:
        zahlung_hv = cint(sinv.mitgliedschafts_jahr)
        if zahlung_hv < 1:
            zahlung_hv = cint(getdate(sinv.posting_date).year)
        datum_hv_zahlung = sinv.posting_date
    else:
        datum_hv_zahlung = get_pe_reference_date(sinv.name)
        if not datum_hv_zahlung:
            # Ist keine POS-Sinv und beseitzt kein PE
            return
        
        zahlung_hv = cint(sinv.mitgliedschafts_jahr)
        if zahlung_hv < 1:
            zahlung_hv = cint(getdate(datum_hv_zahlung).year)

    frappe.db.set_value(
        "Mitgliedschaft",
        mitglied_id,
        {
            'zahlung_hv': zahlung_hv,
            'datum_hv_zahlung': datum_hv_zahlung
        }
    )

    return