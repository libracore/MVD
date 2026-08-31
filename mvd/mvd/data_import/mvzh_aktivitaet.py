# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd
from tqdm import tqdm
from frappe.utils.data import getdate
from frappe.utils import cint
import re

'''
    Import Aktivitäten MVZH
    -----------------
    Prod:
    sudo bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_aktivitaet.import_from_file --kwargs "{'file_name': 'xyz.csv'}"
    Test:
    sudo bench --site test-libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_aktivitaet.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'test-libracore.mieterverband.ch'}"
    Alte Dev VM (Oracle):
    bench execute mvd.mvd.data_import.mvzh_aktivitaet.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'site1.local', 'bench': 'frappe', 'create_missing_users':1}"
    Multi-Bench VM:
    bench execute mvd.mvd.data_import.mvzh_aktivitaet.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'mvd', 'bench': 'mvd'}"

    Hinweis
    --------
    Vor der ersten Nutzung Index setzen!
    ALTER TABLE `tabAktivitaet`
    ADD INDEX `idx_import_datenquelle_zeile`
    (`import_datenquelle`, `import_zeile`);
'''
def import_from_file(file_name, site_name='libracore.mieterverband.ch', bench='frappe', skip_missing_users=False, create_missing_users=False):
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench), sep=";", dtype=str, keep_default_na=False)

    # Step 1: Check if user exists
    print("Prüfe Existenz aller User...")
    missing_users = []
    createt_missing_users = []
    checked_users = []
    for index, row in tqdm(df.iterrows(), desc="Prüfe User", unit=" User", total=len(df.index)):
        if get_value(row, 'Erfasser') not in checked_users:
            checked_users.append(get_value(row, 'Erfasser'))
            if not frappe.db.exists("User", {'full_name': get_value(row, 'Erfasser')}):
                if not create_missing_users:
                    missing_users.append(get_value(row, 'Erfasser'))
                else:
                    create_user(row)
                    createt_missing_users.append(get_value(row, 'Erfasser'))

    if len(missing_users) > 0:
        print("Nachfolgende User wurden nicht gefunden:")
        print(missing_users)
        if not skip_missing_users:
            return
        else:
            print("Setze Import fort und überspringe fehlende Users...")

    if len(createt_missing_users) > 0:
        print("Nachfolgende User wurden erstellt:")
        print(createt_missing_users)

    print("Starte Import...")
    for index, row in tqdm(df.iterrows(), desc="Import Aktivität", unit=" Aktivitäten", total=len(df.index)):
        if (
            get_value(row, 'Erfasser') not in missing_users
            and not frappe.db.exists("Aktivitaet", {'import_datenquelle': file_name, 'import_zeile': cint(index) + 2})
        ):
            new_aktivitaet = frappe.new_doc("Aktivitaet")
            new_aktivitaet.datum = getdate(get_value(row, "Datum"))
            new_aktivitaet.erfasser = get_value(row, "Erfasser")
            new_aktivitaet.import_datenquelle = file_name
            new_aktivitaet.import_zeile = cint(index) + 2
            new_aktivitaet.import_verarbeitet = 0
            new_aktivitaet.typ = get_value(row, "Typ")
            new_aktivitaet.art = get_value(row, "Kontakt-Art")
            new_aktivitaet.termin = getdate(get_value(row, "Termin"))
            new_aktivitaet.prioritaet = get_value(row, "Priorität")
            new_aktivitaet.zustaendig = get_user(get_value(row, "Zuständig"))
            new_aktivitaet.erledigt = get_true_false_flag(get_value(row, "Erledigt"))
            new_aktivitaet.erledigt_datum = getdate(get_value(row, "Erledigt Datum"))
            # new_aktivitaet.mitglied_nr --> wird direkt aus verknüpfter Mitgliedschaft gefeched
            new_aktivitaet.mv_mitgliedschaft = get_value(row, "MitgliederID")
            # new_aktivitaet.sektion_id --> wird direkt aus verknüpfter Mitgliedschaft gefeched
            new_aktivitaet.titel = get_value(row, "Titel")
            new_aktivitaet.dokument_intern = get_value(row, "Dokument intern")
            new_aktivitaet.pfad_legacy = get_value(row, "Basis-Pfad")
            new_aktivitaet.dokument = get_value(row, "Dokument")
            new_aktivitaet.erfasst_datum = getdate(get_value(row, "Erfasst Datum"))
            new_aktivitaet.geaendert_datum = getdate(get_value(row, "Geändert Datum"))
            new_aktivitaet.sachverhalt = get_value(row, "Sachverhalt")
            new_aktivitaet.empfehlung = get_value(row, "Empfehlung")
            new_aktivitaet.fristbeginn = get_value(row, "Fristbeginn")
            new_aktivitaet.k_aus_der_beratung = get_value(row, "K-aus der Beratung")
            new_aktivitaet.k_anfangsmietzins = get_value(row, "K-Anfangsmietzins")
            new_aktivitaet.k_spezialkategorie = get_value(row, "K-Spezialkategorie")
            new_aktivitaet.k_mietzinssenkung = get_value(row, "K-Mietzinssenkung")
            new_aktivitaet.k_maengel = get_value(row, "K-Mängel")
            new_aktivitaet.k_nebenkosten = get_value(row, "K-Nebenkosten")
            new_aktivitaet.k_kuendigung = get_value(row, "K-Kündigung")
            new_aktivitaet.k_mietzinserhoehung = get_value(row, "K-Mietzinserhöhung")
            new_aktivitaet.k_forderung = get_value(row, "K-Forderung")
            new_aktivitaet.k_andere = get_value(row, "K-Andere")
            new_aktivitaet.fallergebnisse = get_value(row, "Fallergebnisse")

            new_aktivitaet.insert()
            frappe.db.commit()

            frappe.db.set_value("Aktivitaet", new_aktivitaet.name, 'owner', new_aktivitaet.zustaendig)
            frappe.db.set_value("Aktivitaet", new_aktivitaet.name, 'creation', new_aktivitaet.erfasst_datum)
            frappe.db.set_value("Aktivitaet", new_aktivitaet.name, 'modified', new_aktivitaet.geaendert_datum)
            frappe.db.commit()

def get_value(row, value):
    value = row[value]
    return value.strip()

def get_user(zustaendig):
    return frappe.db.exists("User", {'full_name': zustaendig, 'enabled': 1})

def get_true_false_flag(flag):
    if flag == "True": return 1
    return 0

def create_user(row):
    new_user = frappe.new_doc("User")
    new_user.enabled = 0
    new_user.email = "{0}@not.found".format(sanitize_string(get_value(row, 'Erfasser')))
    new_user.first_name = get_value(row, 'Erfasser').split(" ")[0]
    new_user.last_name = get_value(row, 'Erfasser').split(" ")[1] if len(get_value(row, 'Erfasser').split(" ")) > 1 else ''
    new_user.send_welcome_email = 0
    new_user.insert()
    frappe.db.commit()
    return

def sanitize_string(value):
    if not value:
        return ""

    replacements = {
        "ä": "ae",
        "Ä": "Ae",
        "ö": "oe",
        "Ö": "Oe",
        "ü": "ue",
        "Ü": "Ue",
        "ß": "ss",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(r"[^a-zA-Z0-9]+", "_", value)

    return value.strip("_")