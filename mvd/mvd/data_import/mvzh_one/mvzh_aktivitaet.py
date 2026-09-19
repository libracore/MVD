# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd
from tqdm import tqdm
from frappe.utils.data import getdate
from frappe.utils import cint


BATCH_SIZE = 1000


'''
    Import Aktivitäten MVZH
    -----------------------

    ACHTUNG:
    tabAktivitaet wird vor dem Import vollständig geleert!

    Prod:
    sudo bench --site libracore.mieterverband.ch execute \
    mvd.mvd.data_import.mvzh_one.mvzh_aktivitaet.import_from_file \
    --kwargs "{'file_name': 'xyz.csv'}"

    Test:
    sudo bench --site test-libracore.mieterverband.ch execute \
    mvd.mvd.data_import.mvzh_one.mvzh_aktivitaet.import_from_file \
    --kwargs "{'file_name': 'xyz.csv', 'site_name': 'test-libracore.mieterverband.ch'}"

    VM:
    bench execute \
    mvd.mvd.data_import.mvzh_one.mvzh_aktivitaet.import_from_file \
    --kwargs "{'file_name': 'aktivitaeten_import.csv', 'site_name': 'mvd', 'bench': 'mvd'}"
'''
def import_from_file(
    file_name,
    site_name='libracore.mieterverband.ch',
    bench='frappe'
):
    # ---------------------------------------------------------
    # CSV laden
    # ---------------------------------------------------------

    file_path = (
        '/home/frappe/{bench}-bench/sites/'
        '{site_name}/private/files/{file_name}'
    ).format(
        bench=bench,
        site_name=site_name,
        file_name=file_name
    )

    print("Lese CSV...")

    df = pd.read_csv(
        file_path,
        sep=";",
        dtype=str,
        keep_default_na=False
    )

    print("CSV enthält {0} Zeilen.".format(len(df.index)))

    # ---------------------------------------------------------
    # User Mapping laden
    #
    # CSV:
    #   "Max Muster"
    #
    # DB:
    #   "max.muster@example.ch"
    # ---------------------------------------------------------

    print("Lade User-Mapping...")

    user_mapping = {}

    users = frappe.db.sql("""
        SELECT
            `name`,
            `full_name`
        FROM `tabUser`
        WHERE `enabled` = 1
    """, as_dict=True)

    for user in users:
        if user.full_name:
            user_mapping[user.full_name] = user.name

    print(
        "{0} aktive User geladen.".format(
            len(user_mapping)
        )
    )

    # ---------------------------------------------------------
    # Tabelle leeren
    # ---------------------------------------------------------

    print("Leere tabAktivitaet...")

    frappe.db.sql("""TRUNCATE TABLE `tabAktivitaet`""")

    print("tabAktivitaet wurde geleert.")

    # ---------------------------------------------------------
    # INSERT SQL
    # ---------------------------------------------------------

    sql = """
        INSERT INTO `tabAktivitaet`
        (
            `name`,
            `creation`,
            `modified`,
            `modified_by`,
            `owner`,
            `docstatus`,
            `idx`,
            `objekt_id`,
            `datum`,
            `erfasser`,
            `import_datenquelle`,
            `import_zeile`,
            `import_verarbeitet`,
            `typ`,
            `art`,
            `termin`,
            `prioritaet`,
            `zustaendig`,
            `erledigt`,
            `erledigt_datum`,
            `mv_mitgliedschaft`,
            `titel`,
            `dokument_intern`,
            `pfad_legacy`,
            `dokument`,
            `erfasst_datum`,
            `geaendert_datum`,
            `sachverhalt`,
            `empfehlung`,
            `fristbeginn`,
            `k_aus_der_beratung`,
            `k_anfangsmietzins`,
            `k_spezialkategorie`,
            `k_mietzinssenkung`,
            `k_maengel`,
            `k_nebenkosten`,
            `k_kuendigung`,
            `k_mietzinserhoehung`,
            `k_forderung`,
            `k_andere`,
            `fallergebnisse`,
            `sektion_id`,
            `zustaendig_legacy`
        )
        VALUES
        (
            %(name)s,
            %(creation)s,
            %(modified)s,
            %(modified_by)s,
            %(owner)s,
            %(docstatus)s,
            %(idx)s,
            %(objekt_id)s,
            %(datum)s,
            %(erfasser)s,
            %(import_datenquelle)s,
            %(import_zeile)s,
            %(import_verarbeitet)s,
            %(typ)s,
            %(art)s,
            %(termin)s,
            %(prioritaet)s,
            %(zustaendig)s,
            %(erledigt)s,
            %(erledigt_datum)s,
            %(mv_mitgliedschaft)s,
            %(titel)s,
            %(dokument_intern)s,
            %(pfad_legacy)s,
            %(dokument)s,
            %(erfasst_datum)s,
            %(geaendert_datum)s,
            %(sachverhalt)s,
            %(empfehlung)s,
            %(fristbeginn)s,
            %(k_aus_der_beratung)s,
            %(k_anfangsmietzins)s,
            %(k_spezialkategorie)s,
            %(k_mietzinssenkung)s,
            %(k_maengel)s,
            %(k_nebenkosten)s,
            %(k_kuendigung)s,
            %(k_mietzinserhoehung)s,
            %(k_forderung)s,
            %(k_andere)s,
            %(fallergebnisse)s,
            %(sektion_id)s,
            %(zustaendig_legacy)s
        )
    """

    # ---------------------------------------------------------
    # Import
    # ---------------------------------------------------------

    print(
        "Starte Import mit Batch Size {0}..."
        .format(BATCH_SIZE)
    )

    batch = []
    imported = 0
    skipped = 0

    for index, row in tqdm(
        df.iterrows(),
        desc="Import Aktivität",
        unit=" Aktivitäten",
        total=len(df.index)
    ):
        objekt_id = get_value(
            row,
            "Eintrag-ID-Aktitaet"
        )

        # Ohne Objekt-ID überspringen
        if not objekt_id:
            skipped += 1
            continue

        # -----------------------------------------------------
        # User auflösen
        # -----------------------------------------------------

        zustaendig_name = get_value(
            row,
            "Zuständig"
        )

        zustaendig = user_mapping.get(
            zustaendig_name
        )

        # -----------------------------------------------------
        # Datum
        # -----------------------------------------------------

        datum = parse_date(
            get_value(row, "datum")
        )

        termin = parse_date(
            get_value(row, "Termin")
        )

        erledigt_datum = parse_date(
            get_value(row, "Erledigt Datum")
        )

        erfasst_datum = parse_date(
            get_value(row, "Erfasst Datum")
        )

        geaendert_datum = parse_date(
            get_value(row, "Geändert Datum")
        )

        # -----------------------------------------------------
        # Systemfelder
        # -----------------------------------------------------

        creation = erfasst_datum

        modified = (
            geaendert_datum
            or erfasst_datum
        )

        owner = (
            zustaendig
            or "Administrator"
        )

        # -----------------------------------------------------
        # Datensatz
        # -----------------------------------------------------

        batch.append({
            "name": objekt_id,
            "creation": creation,
            "modified": modified,
            "modified_by": "Administrator",
            "owner": owner,
            "docstatus": 0,
            "idx": 0,
            "objekt_id": objekt_id,
            "datum": datum,
            "erfasser": get_value(
                row,
                "Erfasser"
            ),
            "import_datenquelle": file_name,
            "import_zeile": cint(index) + 2,
            "import_verarbeitet": 0,
            "typ": get_value(
                row,
                "Typ"
            ),
            "art": get_value(
                row,
                "Kontakt-Art"
            ),
            "termin": termin,
            "prioritaet": get_value(
                row,
                "Priorität"
            ),
            "zustaendig": zustaendig,
            "erledigt": get_true_false_flag(
                get_value(
                    row,
                    "Erledigt"
                )
            ),
            "erledigt_datum": erledigt_datum,
            "mv_mitgliedschaft": get_value(
                row,
                "mv_mitgliedschaft"
            ),
            "titel": get_value(
                row,
                "Titel"
            ),
            "dokument_intern": get_value(
                row,
                "Dokument intern"
            ),
            "pfad_legacy": get_value(
                row,
                "Basis-Pfad"
            ),
            "dokument": get_value(
                row,
                "Dokument"
            ),
            "erfasst_datum": erfasst_datum,
            "geaendert_datum": geaendert_datum,
            "sachverhalt": get_value(
                row,
                "Sachverhalt"
            ),
            "empfehlung": get_value(
                row,
                "Empfehlung"
            ),
            "fristbeginn": get_value(
                row,
                "Fristbeginn"
            ),
            "k_aus_der_beratung": get_value(
                row,
                "K-aus der Beratung"
            ),
            "k_anfangsmietzins": get_value(
                row,
                "K-Anfangsmietzins"
            ),
            "k_spezialkategorie": get_value(
                row,
                "K-Spezialkategorie"
            ),
            "k_mietzinssenkung": get_value(
                row,
                "K-Mietzinssenkung"
            ),
            "k_maengel": get_value(
                row,
                "K-Mängel"
            ),
            "k_nebenkosten": get_value(
                row,
                "K-Nebenkosten"
            ),
            "k_kuendigung": get_value(
                row,
                "K-Kündigung"
            ),
            "k_mietzinserhoehung": get_value(
                row,
                "K-Mietzinserhöhung"
            ),
            "k_forderung": get_value(
                row,
                "K-Forderung"
            ),
            "k_andere": get_value(
                row,
                "K-Andere"
            ),
            "fallergebnisse": get_value(
                row,
                "Fallergebnisse"
            ),
            "sektion_id": "MVZH",
            "zustaendig_legacy": get_value(
                row,
                "Zuständig"
            )
        })

        # -----------------------------------------------------
        # Batch schreiben
        # -----------------------------------------------------

        if len(batch) >= BATCH_SIZE:
            insert_batch(sql, batch)

            imported += len(batch)
            batch = []

    # ---------------------------------------------------------
    # Restlicher Batch
    # ---------------------------------------------------------

    if batch:
        insert_batch(sql, batch)

        imported += len(batch)

    frappe.db.commit()

    # ---------------------------------------------------------
    # Ergebnis
    # ---------------------------------------------------------

    print("===================================")
    print("Import abgeschlossen")
    print("===================================")
    print(
        "CSV Zeilen:   {0}".format(
            len(df.index)
        )
    )
    print(
        "Importiert:   {0}".format(
            imported
        )
    )
    print(
        "Übersprungen: {0}".format(
            skipped
        )
    )
    print("===================================")


def insert_batch(sql, batch):
    frappe.db._cursor.executemany(
        sql,
        batch
    )

    frappe.db.commit()


def get_value(row, field):
    value = row[field]

    if value is None:
        return ""

    return value.strip()


def parse_date(value):
    if not value:
        return None

    value = value.strip()

    if not value:
        return None

    return getdate(value)


def get_true_false_flag(flag):
    if flag == "True":
        return 1

    return 0