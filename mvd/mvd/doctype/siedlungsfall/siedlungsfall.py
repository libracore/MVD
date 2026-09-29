# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import datetime
from frappe.utils.data import today
from frappe.utils import escape_html

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
            WHERE `mv_mitgliedschaft` = %s
            ORDER BY `start_date` DESC
            LIMIT 1
        """,
        (mitglied,),
        as_dict=True
    )

    if beratungen:
        beratung = beratungen[0]

        datum = (
            beratung.start_date.strftime("%d.%m.%Y")
            if beratung.start_date
            else "-"
        )

        return "{0}, {1}".format(
            datum,
            beratung.beratungskategorie or "-"
        )

    return ""

def get_letztes_mandat(mitglied):
    rsv_mitglieder = frappe.db.sql(
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
    
    if len(rsv_mitglieder) > 0:
        themen = frappe.db.sql(
            """
                SELECT `thema`
                FROM `tabRSV Thema MultiTable`
                WHERE `parent` = '{0}'
            """.format(rsv_mitglieder[0].name),
            as_dict=True
        )
        thema = '-'
        if len(themen):
            thema = themen[0].thema
        
        return "{0}, {1}, {2}".format(format_date(rsv_mitglieder[0].creation), thema, rsv_mitglieder[0].status)
    
    return ""

def format_date(value):
    """Gibt ein Datum/einen Zeitstempel als dd.mm.yyyy zurück.

    Ohne datetime.fromisoformat: >= py 3.7,
    
    Akzeptiert date/datetime oder einen ISO-String (YYYY-MM-DD...).
    KEIN dateutil/getdate auf Strings: "01.09.2026" = als 9. Januar,
    weil dateutil Monat-zuerst interpretiert ?!!?
    """
    if not value:
        return "-"
    if isinstance(value, (datetime.date, datetime.datetime)):
        date = value
    else:
        try:
            date = datetime.datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except ValueError:
            return "-"
    if date.year < 1900:
        # 0001-01-01 = "leeres" Datum in MariaDB/Frappe
        return "-"
    return date.strftime("%d.%m.%Y")

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

@frappe.whitelist()
def get_siedlungsadressen_html(siedlung):
    """Adressliste einer Siedlung als klickbare Zeilen (siehe .mvd-list in mvd.css)."""
    siedlung_doc = frappe.get_doc("Siedlung", siedlung)

    # Gleicher Zeilenaufbau wie die RSV-Mitglieder-Liste: Schluessel, Haupt-
    # angabe, Zusatz. Ohne ADR_EGAID gibt es kein Ziel - dann keine Zeile,
    # die faelschlich nach Link aussieht.
    row_template = """
            <{tag} class="mvd-list-row"{href}>
                <span class="mvd-list-cell mvd-list-id">{adr_egaid}</span>
                <span class="mvd-list-cell mvd-list-main" title="{strasse}">{strasse}</span>
                <span class="mvd-list-cell mvd-list-sub" title="{ort}">{ort}</span>
            </{tag}>
    """

    rows = []

    for siedlungsadresse in siedlung_doc.zugehoerige_gebaeude:
        adr_egaid = siedlungsadresse.get("adr_egaid") or ""

        strasse = " ".join([p for p in [siedlungsadresse.get("stn_label"),
                                        siedlungsadresse.get("adr_number")] if p]) or "-"
        ort = " ".join([p for p in [siedlungsadresse.get("plz"),
                                    siedlungsadresse.get("wohnort")] if p]) or "-"

        rows.append(
            row_template.format(
                tag="a" if adr_egaid else "div",
                href=' href="/desk#Form/Amtliches Gebaeudeverzeichnis/{0}"'.format(
                    escape_html(adr_egaid)) if adr_egaid else "",
                adr_egaid=escape_html(adr_egaid or "-"),
                strasse=escape_html(strasse),
                ort=escape_html(ort)
            )
        )

    if not rows:
        rows.append("""<div class="mvd-list-empty">Keine Adressen hinterlegt.</div>""")

    return """
        <div class="mvd-list">
        {rows}
        </div>
    """.format(rows="".join(rows))