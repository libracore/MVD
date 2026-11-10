# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import frappe

# #2205: Status-Konzept Mandat
# 1. Mandate ohne Typ -> «Rechtsschutzversicherung»
# 2. «Gutsprache» -> «Laufend (RSV)» bzw. «Laufend (Solifonds)», dazu «Kostengutsprache am»
# 3. Statusverlauf aus der Änderungshistorie (Versionen) und den Kommentaren der E-Mail-Automatik nachfüllen
#
# Wiederholbar: Schritt 3 nur für Mandate ohne Statusverlauf. Ohne try/except und ohne eigenen commit:
# Frappe rollt bei einem Fehler zurück, der Patch läuft beim nächsten migrate erneut.

RSV = "Rechtsschutzversicherung"
SOLIFONDS = "Solidaritätsfonds"
MIGRATION = "Migration"

def execute():
    frappe.reload_doc("mvd", "doctype", "statusaenderung")
    frappe.reload_doc("mvd", "doctype", "mandat")

    frappe.db.sql("""UPDATE `tabMandat` SET `typ` = %s WHERE IFNULL(`typ`, '') = ''""", RSV)

    # Kostengutsprache am: Solifonds aus dem Entscheiddatum, RSV aus der Änderungshistorie (weiter unten)
    frappe.db.sql("""UPDATE `tabMandat` SET `kostengutsprache_am` = `entscheid_datum`
        WHERE `status` = 'Gutsprache' AND `typ` = %s AND `kostengutsprache_am` IS NULL""", SOLIFONDS)

    for mandat in frappe.db.sql("""SELECT `name`, `status`, `typ`, `owner`, `creation`, `kostengutsprache_am`
            FROM `tabMandat`""", as_dict=True):
        hat_verlauf = frappe.db.count("Statusaenderung", {"parent": mandat.name, "parenttype": "Mandat"})
        zeilen = [] if hat_verlauf else verlauf_aus_historie(mandat)

        neuer_status = mandat.status
        if mandat.status == "Gutsprache":
            neuer_status = "Laufend (Solifonds)" if mandat.typ == SOLIFONDS else "Laufend (RSV)"
            if not mandat.kostengutsprache_am:
                gutsprache = [z for z in zeilen if z["nach_status"] == "Gutsprache"]
                if gutsprache:
                    frappe.db.set_value("Mandat", mandat.name, "kostengutsprache_am", gutsprache[-1]["datum"],
                        update_modified=False)
            frappe.db.set_value("Mandat", mandat.name, "status", neuer_status, update_modified=False)
            if hat_verlauf:
                zeilen.append(zeile(frappe.utils.now_datetime(), "Gutsprache", neuer_status, "Administrator",
                    "Umbenennung «Gutsprache» (#2205)"))

        if not hat_verlauf:
            letzter = zeilen[-1]["nach_status"] if zeilen else None
            if letzter != neuer_status:
                bemerkung = "Umbenennung «Gutsprache» (#2205)" if letzter == "Gutsprache" else "Ausgangsstatus (Migration)"
                zeilen.append(zeile(frappe.utils.now_datetime(), letzter, neuer_status, "Administrator", bemerkung))

        start = frappe.db.sql("""SELECT IFNULL(MAX(`idx`), 0) FROM `tabStatusaenderung`
            WHERE `parent` = %s AND `parenttype` = 'Mandat'""", mandat.name)[0][0]
        for i, z in enumerate(zeilen):
            doc = frappe.get_doc(dict(z, doctype="Statusaenderung", parent=mandat.name, parenttype="Mandat",
                parentfield="statusverlauf", idx=start + i + 1, quelle=MIGRATION))
            doc.db_insert()


def zeile(datum, von, nach, benutzer, bemerkung):
    return {"datum": datum, "von_status": von, "nach_status": nach, "benutzer": benutzer, "bemerkung": bemerkung}


def verlauf_aus_historie(mandat):
    ereignisse = []
    for v in frappe.db.sql("""SELECT `owner`, `creation`, `data` FROM `tabVersion`
            WHERE `ref_doctype` = 'Mandat' AND `docname` = %s ORDER BY `creation`""", mandat.name, as_dict=True):
        try:
            daten = json.loads(v.data or "{}")
        except ValueError:
            continue
        for feld in daten.get("changed") or []:
            if feld and feld[0] == "status":
                ereignisse.append((v.creation, feld[1], feld[2], v.owner, "aus der Änderungshistorie"))

    # Erste eingehende E-Mail setzte den Status per db.set_value (ohne Version), nur der Kommentar zeigt es
    for c in frappe.db.sql("""SELECT `creation` FROM `tabComment`
            WHERE `reference_doctype` = 'Mandat' AND `reference_name` = %s
            AND `content` LIKE 'Status automatisch auf %%Gesuch eingereicht%%'""", mandat.name, as_dict=True):
        ereignisse.append((c.creation, None, "Gesuch eingereicht", "Administrator", "Erste E-Mail eingegangen (aus Kommentar)"))

    ereignisse.sort(key=lambda e: e[0])
    zeilen = []
    # Erste Zeile: Anlage mit dem ersten bekannten Status
    # (beginnt die Historie mit dem E-Mail-Kommentar, war das Mandat vorher «Vorgemerkt»)
    if not ereignisse:
        erster = mandat.status
    else:
        erster = ereignisse[0][1] or "Vorgemerkt"
    zeilen.append(zeile(mandat.creation, None, erster, mandat.owner, "Mandat erstellt (Migration)"))
    for datum, von, nach, benutzer, bemerkung in ereignisse:
        von = von or zeilen[-1]["nach_status"]
        if von == nach or nach == zeilen[-1]["nach_status"]:
            continue
        zeilen.append(zeile(datum, von, nach, benutzer, bemerkung))
    return zeilen
