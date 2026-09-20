# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt
"""
Korrektur-Befehl: Beratungen, die per E-Mail-Eingang angelegt wurden und dabei
das falsche Datum bekommen haben.

Hintergrund
-----------
Frappe setzt beim Anlegen des Parent-Dokuments (Email Account -> "Anhaengen an"
= Beratung) kein Datum. start_date fiel damit auf den DocType-Default "Today"
zurueck, also auf den Zeitpunkt des Postfach-Abrufs statt auf den tatsaechlichen
Eingang der Mail. Seit dem Fix in beratung.py check_communication() passiert das
nicht mehr - dieser Befehl korrigiert die Altfaelle.

Korrigiert werden:
  * start_date und der daraus gebildete titel
  * auf Wunsch der Dokumentname, der das Datum ebenfalls enthaelt
    (autoname: format:{YY}-{MM}-{DD}-{###}). Der Zaehler ist global eindeutig
    und bleibt erhalten: 26-09-20-438039 -> 26-09-19-438039

Welche Mail ist massgebend?
---------------------------
Die Mail, die die Beratung erzeugt hat - nicht die aelteste verknuepfte Mail.
Eine weitergeleitete Altkorrespondenz wuerde sonst ein falsches Datum liefern.
Erkennungsmerkmale (am Datenbestand geprueft):
  * Frappe legt erst das Parent-Dokument an, dann die Communication. Die
    erzeugende Mail hat die kleinste `creation`, und diese liegt nie vor der
    Beratung.
  * Der Mailabruf laeuft als `Administrator`.

Aufruf
------
Immer zuerst im Probelauf (schreibt nichts ausser dem Protokoll-CSV):

    bench --site site1.local execute \\
        mvd.mvd.utils.beratung_startdate.korrigiere \\
        --kwargs "{'sektion': 'MVZH', 'dry_run': True}"

Beispiele fuer Filter:

    # eine Sektion, Maildatum in einem Zeitraum
    {'sektion': 'MVBE', 'von': '2023-06-01', 'bis': '2023-12-31'}

    # mehrere Sektionen
    {'sektion': ['MVBE', 'MVLU']}

    # nur bestimmte Beratungen
    {'beratungen': ['26-09-20-438039']}

    # groesseres Zeitfenster als nur den Mitternachtsfall
    {'sektion': 'MVBE', 'min_diff': 1, 'max_diff': 5}

    # nur Datum korrigieren, nicht umbenennen
    {'sektion': 'MVBE', 'rename': False}

    # freie SQL-Bedingung, wenn die Parameter nicht reichen
    {'zusatz_bedingung': "b.`status` = 'Closed' AND c.`sender` LIKE '%@gmx.ch'"}

Scharf schalten: 'dry_run': False
"""

import csv
import os
import re

import frappe
from frappe.model.rename_doc import rename_doc
from frappe.utils import cint

# Namensmuster gemaess autoname format:{YY}-{MM}-{DD}-{###}
NAME_PATTERN = re.compile(r"^(\d{2})-(\d{2})-(\d{2})-(\d+)$")

# Sekunden zwischen Beratungs- und Communication-Erstellung, bis zu denen die
# Beratung als "durch diese Mail erzeugt" gilt.
TOLERANZ_SEKUNDEN = 120


def korrigiere(sektion=None, von=None, bis=None, start_von=None, start_bis=None,
               min_diff=1, max_diff=1, beratungen=None, nur_systembenutzer=True,
               zusatz_bedingung=None, toleranz=TOLERANZ_SEKUNDEN,
               rename=True, sp_versendete_umbenennen=False,
               dry_run=True, limit=None):
    """
    :param sektion: Sektion oder Liste von Sektionen (None = alle)
    :param von / bis: Zeitraum des Maildatums (yyyy-mm-dd)
    :param start_von / start_bis: Zeitraum des bisherigen start_date
    :param min_diff / max_diff: Abweichung in Tagen, die korrigiert wird.
        1/1 = nur der Mitternachtsfall.
    :param beratungen: Liste konkreter Beratungs-Namen
    :param nur_systembenutzer: nur Beratungen mit owner = 'Administrator', also
        die vom Mailabruf angelegten
    :param zusatz_bedingung: roher SQL-Ausdruck fuer die WHERE-Klausel.
        Aliase: b = tabBeratung, c = tabCommunication (die erzeugende Mail).
        Wird ungeprueft eingesetzt - nur fuer Administratoren gedacht.
    :param toleranz: Sekunden-Fenster fuer "durch die Mail erzeugt"
    :param rename: False = nur das Datum korrigieren, nicht umbenennen
    :param sp_versendete_umbenennen: Beratungen, die bereits an die Service
        Plattform gemeldet wurden, trotzdem umbenennen. Standard False, weil
        die SP den alten Namen als beratungId gespeichert hat.
    :param dry_run: True = nur berichten, nichts schreiben
    :param limit: nur die ersten n Beratungen bearbeiten (fuer Tranchen)
    """
    dry_run = cint(dry_run)
    kandidaten = finde(sektion=sektion, von=von, bis=bis, start_von=start_von,
                       start_bis=start_bis, min_diff=min_diff, max_diff=max_diff,
                       beratungen=beratungen,
                       nur_systembenutzer=nur_systembenutzer,
                       zusatz_bedingung=zusatz_bedingung, toleranz=toleranz,
                       limit=limit)

    print("Kandidaten: %d  (dry_run=%s, rename=%s)"
          % (len(kandidaten), bool(dry_run), bool(rename)))

    protokoll = []
    datum_ok = rename_ok = uebersprungen = fehler = 0

    for kandidat in kandidaten:
        eintrag = {
            "beratung_alt": kandidat.name,
            "beratung_neu": "",
            "start_date_alt": str(kandidat.start_date),
            "start_date_neu": str(kandidat.mail_datum),
            "diff_tage": (kandidat.start_date - kandidat.mail_datum).days,
            "sektion_id": kandidat.sektion_id or "",
            "communication": kandidat.communication,
            "mail_datum": str(kandidat.communication_date),
            "mail_absender": kandidat.sender or "",
            "mail_betreff": (kandidat.subject or "")[:120],
            "mail_message_id": kandidat.message_id or "",
            "email_account": kandidat.email_account or "",
            "absender_ist_raised_by": (
                "ja" if (kandidat.raised_by or "").lower()
                == (kandidat.sender or "").lower() else "nein"),
            "an_sp_gemeldet": "ja" if kandidat.an_sp_gemeldet else "nein",
            "aktion": "",
            "fehler": "",
        }

        try:
            # ---- 1) Datum + Titel ------------------------------------------
            # Bewusst per db.set_value statt doc.save(): validate()/on_update()
            # wuerden Siedlungsfall-Jobs einreihen und koennten bei heute nicht
            # mehr validierenden Beratungen abbrechen. Der titel beginnt immer
            # mit dem start_date im Format YYYY-MM-DD (10 Zeichen) und wird
            # deshalb hier direkt mitgezogen.
            neuer_titel = None
            if kandidat.titel and len(kandidat.titel) >= 10:
                neuer_titel = "%s%s" % (kandidat.mail_datum.isoformat(),
                                        kandidat.titel[10:])

            if not dry_run:
                werte = {"start_date": kandidat.mail_datum}
                if neuer_titel:
                    werte["titel"] = neuer_titel
                frappe.db.set_value("Beratung", kandidat.name, werte,
                                    update_modified=False)
            datum_ok += 1
            eintrag["aktion"] = "datum"

            # ---- 2) Umbenennen ---------------------------------------------
            if not rename:
                protokoll.append(eintrag)
                continue

            if kandidat.an_sp_gemeldet and not sp_versendete_umbenennen:
                eintrag["aktion"] = "datum (rename uebersprungen: an SP gemeldet)"
                uebersprungen += 1
                protokoll.append(eintrag)
                continue

            neuer_name = _neuer_name(kandidat.name, kandidat.mail_datum)
            if not neuer_name:
                eintrag["aktion"] = "datum (rename uebersprungen: Namensmuster)"
                uebersprungen += 1
                protokoll.append(eintrag)
                continue

            if frappe.db.exists("Beratung", neuer_name):
                eintrag["aktion"] = "datum (rename uebersprungen: Name belegt)"
                uebersprungen += 1
                protokoll.append(eintrag)
                continue

            eintrag["beratung_neu"] = neuer_name

            if not dry_run:
                # force=True ist noetig, weil allow_rename im DocType nicht
                # gesetzt ist. rename_doc zieht Link-Felder, Dynamic Links,
                # Child-Tabellen, tabFile und tabVersion mit.
                rename_doc("Beratung", kandidat.name, neuer_name,
                           force=True, ignore_permissions=True)
                _update_freitext_referenzen(kandidat.name, neuer_name)

            rename_ok += 1
            eintrag["aktion"] = "datum + rename"

        except Exception as err:
            fehler += 1
            eintrag["fehler"] = str(err)[:300]
            eintrag["aktion"] = "FEHLER"
            frappe.log_error(frappe.get_traceback(),
                             "beratung_startdate: %s" % kandidat.name)

        protokoll.append(eintrag)

    if not dry_run:
        frappe.db.commit()

    pfad = _schreibe_protokoll(protokoll, dry_run)

    print("Datum korrigiert  : %d" % datum_ok)
    print("Umbenannt         : %d" % rename_ok)
    print("Rename ausgelassen: %d" % uebersprungen)
    print("Fehler            : %d" % fehler)
    print("Protokoll         : %s" % pfad)
    return {"kandidaten": len(kandidaten), "datum": datum_ok,
            "rename": rename_ok, "uebersprungen": uebersprungen,
            "fehler": fehler, "protokoll": pfad}


def zeige(**kwargs):
    """Probelauf: wie korrigiere(), schreibt aber garantiert nichts."""
    kwargs["dry_run"] = True
    return korrigiere(**kwargs)


def finde(sektion=None, von=None, bis=None, start_von=None, start_bis=None,
          min_diff=1, max_diff=1, beratungen=None, nur_systembenutzer=True,
          zusatz_bedingung=None, toleranz=TOLERANZ_SEKUNDEN, limit=None):
    """
    Liefert die Kandidaten samt der Mail, die sie erzeugt hat.

    Die erzeugende Mail ist die empfangene E-Mail-Communication mit der
    kleinsten `creation`, deren `creation` im Fenster [0 .. toleranz] nach der
    Beratung liegt. Das Datum kommt aus `communication_date` dieser Mail.
    """
    bedingungen = [
        "DATEDIFF(b.`start_date`, DATE(c.`communication_date`)) "
        "BETWEEN %(min_diff)s AND %(max_diff)s",
        "TIMESTAMPDIFF(SECOND, b.`creation`, c.`creation`) BETWEEN 0 AND %(toleranz)s",
    ]
    werte = {"min_diff": cint(min_diff), "max_diff": cint(max_diff),
             "toleranz": cint(toleranz)}

    if sektion:
        if isinstance(sektion, (list, tuple, set)):
            sektionen = list(sektion)
            platzhalter = ", ".join(
                ["%%(sektion_%d)s" % i for i in range(len(sektionen))])
            bedingungen.append("b.`sektion_id` IN (%s)" % platzhalter)
            for i, wert in enumerate(sektionen):
                werte["sektion_%d" % i] = wert
        else:
            bedingungen.append("b.`sektion_id` = %(sektion)s")
            werte["sektion"] = sektion

    if von:
        bedingungen.append("DATE(c.`communication_date`) >= %(von)s")
        werte["von"] = von
    if bis:
        bedingungen.append("DATE(c.`communication_date`) <= %(bis)s")
        werte["bis"] = bis

    if start_von:
        bedingungen.append("b.`start_date` >= %(start_von)s")
        werte["start_von"] = start_von
    if start_bis:
        bedingungen.append("b.`start_date` <= %(start_bis)s")
        werte["start_bis"] = start_bis

    if beratungen:
        namen = list(beratungen) if isinstance(
            beratungen, (list, tuple, set)) else [beratungen]
        platzhalter = ", ".join(["%%(ber_%d)s" % i for i in range(len(namen))])
        bedingungen.append("b.`name` IN (%s)" % platzhalter)
        for i, wert in enumerate(namen):
            werte["ber_%d" % i] = wert

    if nur_systembenutzer:
        # Der Mailabruf laeuft als Administrator, siehe set_sektion() in
        # beratung.py. Von Hand angelegte Beratungen sind nicht gemeint.
        bedingungen.append("b.`owner` = 'Administrator'")

    if zusatz_bedingung:
        # Bewusste Hintertuer fuer Faelle, die die Parameter nicht abdecken.
        # Wird ungeprueft uebernommen - nur ueber die Bench aufrufbar.
        # Das Prozentzeichen wird verdoppelt, weil die fertige Abfrage von
        # pymysql nochmals durch die %-Formatierung laeuft. In der Bedingung
        # also ganz normal ein einzelnes % schreiben: LIKE '%@gmail.com'
        bedingungen.append("(%s)" % zusatz_bedingung.replace("%", "%%"))

    sql = """
        SELECT
            b.`name`,
            b.`sektion_id`,
            b.`start_date`,
            b.`titel`,
            b.`raised_by`,
            c.`name`               AS `communication`,
            c.`communication_date`,
            c.`sender`,
            c.`subject`,
            c.`message_id`,
            c.`email_account`,
            DATE(c.`communication_date`) AS `mail_datum`
        FROM `tabBeratung` b
        INNER JOIN (
            SELECT `reference_name`, MIN(`creation`) AS `erste_creation`
            FROM `tabCommunication`
            WHERE `sent_or_received` = 'Received'
              AND `reference_doctype` = 'Beratung'
              AND `communication_medium` = 'Email'
            GROUP BY `reference_name`
        ) f ON f.`reference_name` = b.`name`
        INNER JOIN `tabCommunication` c
            ON  c.`reference_name` = b.`name`
            AND c.`creation` = f.`erste_creation`
            AND c.`reference_doctype` = 'Beratung'
            AND c.`sent_or_received` = 'Received'
            AND c.`communication_medium` = 'Email'
        WHERE {bedingungen}
        ORDER BY b.`start_date`, b.`name`
    """.format(bedingungen=" AND ".join(bedingungen))

    if limit:
        sql += " LIMIT %d" % cint(limit)

    kandidaten = frappe.db.sql(sql, werte, as_dict=True)

    # Kennzeichnen, welche Beratungen bereits an die Service Plattform
    # gemeldet wurden. Bewusst als eine einzelne Abfrage und nicht als
    # korrelierte Unterabfrage: `tabBeratungs Log` hat keinen Index auf
    # `beratung`, ein EXISTS pro Kandidat scannt die ganze Tabelle.
    gemeldet = _sp_gemeldete([k.name for k in kandidaten])
    for kandidat in kandidaten:
        kandidat.an_sp_gemeldet = kandidat.name in gemeldet

    return kandidaten


def _sp_gemeldete(namen):
    """Namen der Beratungen, zu denen ein SP-Versand protokolliert ist."""
    if not namen:
        return set()

    gemeldet = set()
    schrittweite = 5000
    for i in range(0, len(namen), schrittweite):
        teil = namen[i:i + schrittweite]
        platzhalter = ", ".join(["%s"] * len(teil))
        rows = frappe.db.sql("""
            SELECT DISTINCT `beratung` FROM `tabBeratungs Log`
            WHERE `method` = 'send_to_sp' AND `beratung` IN ({0})
        """.format(platzhalter), tuple(teil))
        gemeldet.update(r[0] for r in rows)
    return gemeldet


def _neuer_name(alter_name, neues_datum):
    """
    26-09-20-438039 + 2026-09-19 -> 26-09-19-438039

    Der Zaehler bleibt unveraendert, er ist global eindeutig. Gibt None
    zurueck, wenn der Name nicht dem erwarteten Muster entspricht.
    """
    treffer = NAME_PATTERN.match(alter_name or "")
    if not treffer:
        return None
    return "%s-%s" % (neues_datum.strftime("%y-%m-%d"), treffer.group(4))


# Tabellen, die eine Beratung ueber ein `Data`-Feld referenzieren statt ueber
# einen Dynamic Link. rename_doc() baut seine Ersetzungsliste aus
# get_dynamic_link_map() und laesst diese deshalb unberuehrt.
#   (Tabelle, Spalte mit dem DocType, Spalte mit dem Namen)
DATA_REFERENZEN = [
    ("tabEmail Queue", "reference_doctype", "reference_name"),
    ("tabEnergy Point Log", "reference_doctype", "reference_name"),
    ("tabMilestone", "reference_type", "reference_name"),
]


def _update_freitext_referenzen(alter_name, neuer_name):
    """
    Referenzen, die rename_doc nicht kennt, weil sie nicht als Link oder
    Dynamic Link modelliert sind:
      - Kommentar-Texte mit hartem '#Form/Beratung/<name>'-Link
      - 'Beratungs Log'.beratung ist ein Data-Feld, kein Link
      - die Tabellen aus DATA_REFERENZEN, allen voran Email Queue
    """
    for tabelle, doctype_spalte, name_spalte in DATA_REFERENZEN:
        try:
            frappe.db.sql("""
                UPDATE `{tabelle}` SET `{name_spalte}` = %(neu)s
                WHERE `{doctype_spalte}` = 'Beratung' AND `{name_spalte}` = %(alt)s
            """.format(tabelle=tabelle, name_spalte=name_spalte,
                       doctype_spalte=doctype_spalte),
                {"alt": alter_name, "neu": neuer_name})
        except Exception:
            # Tabelle gibt es in dieser Installation nicht - kein Grund,
            # die Korrektur abzubrechen.
            frappe.log_error(frappe.get_traceback(),
                             "beratung_startdate: %s" % tabelle)

    frappe.db.sql("""
        UPDATE `tabComment`
        SET `content` = REPLACE(`content`, %(alt)s, %(neu)s)
        WHERE `content` LIKE %(suchmuster)s
    """, {
        "alt": alter_name,
        "neu": neuer_name,
        "suchmuster": "%#Form/Beratung/" + alter_name + "%",
    })

    frappe.db.sql("""
        UPDATE `tabBeratungs Log` SET `beratung` = %(neu)s WHERE `beratung` = %(alt)s
    """, {"alt": alter_name, "neu": neuer_name})


def _schreibe_protokoll(protokoll, dry_run):
    """Schreibt das Protokoll als CSV in die privaten Dateien der Site."""
    dateiname = "beratung_startdate_%s_%s.csv" % (
        "probelauf" if dry_run else "ausgefuehrt",
        frappe.utils.now().replace(" ", "_").replace(":", "").split(".")[0],
    )
    ordner = frappe.get_site_path("private", "files")
    if not os.path.exists(ordner):
        os.makedirs(ordner)
    pfad = os.path.join(ordner, dateiname)

    felder = ["beratung_alt", "beratung_neu", "start_date_alt", "start_date_neu",
              "diff_tage", "sektion_id", "communication", "mail_datum",
              "mail_absender", "mail_betreff", "mail_message_id",
              "email_account", "absender_ist_raised_by", "an_sp_gemeldet",
              "aktion", "fehler"]
    with open(pfad, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=felder, delimiter=";")
        writer.writeheader()
        writer.writerows(protokoll)
    return pfad
