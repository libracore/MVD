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
from datetime import datetime

'''
    Import RSVMitglieder MVZH
    -----------------
    Prod:
    sudo bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_one.mvzh_rsvmitglieder.import_from_file --kwargs "{'file_name': 'xyz.csv'}"
    Test:
    sudo bench --site test-libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_one.mvzh_rsvmitglieder.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'test-libracore.mieterverband.ch'}"
    Alte Dev VM (Oracle):
    bench execute mvd.mvd.data_import.mvzh_one.mvzh_rsvmitglieder.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'site1.local', 'bench': 'frappe'}"
    Multi-Bench VM:
    bench execute mvd.mvd.data_import.mvzh_one.mvzh_rsvmitglieder.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'mvd', 'bench': 'mvd'}"
'''
def import_from_file(file_name, site_name='libracore.mieterverband.ch', bench='frappe'):
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench), sep=",", dtype=str, keep_default_na=False)

    print("Starte Import...")
    failed = []
    for index, row in tqdm(df.iterrows(), desc="Import RSVMitglieder", unit=" RSVMitglied", total=len(df.index)):
        existing = frappe.db.exists("RSVMitglied", {"vertec_id_mandat": get_value(row, 'vertec_id_mandat')})
        if existing:
            rsvm = frappe.get_doc("RSVMitglied", existing)
        else:
            rsvm = frappe.new_doc("RSVMitglied")
        
        rsvm.status = get_value(row, 'status')
        rsvm.abschluss_datum = parse_csv_datetime(get_value(row, 'abschluss_datum'))
        rsvm.abgelehnt_datum = parse_csv_datetime(get_value(row, 'abgelehnt_datum'))
        rsvm.fallnummer = get_value(row, 'fallnummer')
        rsvm.gescannte_dokumente = get_value(row, 'gescannte_dokumente')
        rsvm.rsvmandat = get_value(row, 'rsvmandat')
        rsvm.strasse = get_value(row, 'strasse')
        rsvm.hausnummer = get_value(row, 'hausnummer')
        rsvm.plz = get_value(row, 'plz')
        rsvm.faktura_kunde = get_value(row, 'faktura_kunde')
        rsvm.faktura_kunde_name = get_value(row, 'faktura_kunde_name')
        rsvm.mv_mitgliedschaft = get_value(row, 'mv_mitgliedschaft')
        rsvm.mitglied_seit = get_value(row, 'mitglied_seit')
        rsvm.mitglied_nr = get_value(row, 'mitglied_nr')
        rsvm.nachname = get_value(row, 'nachname')
        rsvm.vorname = get_value(row, 'vorname')
        rsvm.language = get_value(row, 'language')
        rsvm.sektion_id = get_value(row, 'sektion_id')
        rsvm.zusatz_adresse = get_value(row, 'zusatz_adresse')
        rsvm.nr_zusatz = get_value(row, 'nr_zusatz')
        rsvm.ort = get_value(row, 'ort')
        rsvm.beschreibung = get_value(row, 'beschreibung')
        rsvm.notiz = get_value(row, 'notiz')
        rsvm.speicherpfad_dokumente = get_value(row, 'speicherpfad_dokumente')
        rsvm.vermieterin = get_value(row, 'vermieterin')
        rsvm.verwaltung = get_value(row, 'verwaltung')
        rsvm.bezirk = get_value(row, 'bezirk')
        rsvm.datum_pruefung = parse_csv_datetime(get_value(row, 'datum_pruefung'))
        rsvm.doppelversicherung = get_value(row, 'doppelversicherung')
        rsvm.doppelversicherung_bei = get_value(row, 'doppelversicherung_bei')
        rsvm.unterlagen_bei_ra = get_value(row, 'unterlagen_bei_ra')
        rsvm.sendung_an_coop = get_value(row, 'sendung_an_coop')
        rsvm.kostengutsprache = get_value(row, 'kostengutsprache')
        rsvm.kostengutsprache_datum = parse_csv_datetime(get_value(row, 'kostengutsprache_datum'))
        rsvm.adr_egaid = get_value(row, 'adr_egaid')
        rsvm.bfs_nr = get_value(row, 'bfs_nr')
        rsvm.import_verantwortlich = get_value(row, 'import_verantwortlich')
        rsvm.anwalt = get_value(row, 'anwalt')
        rsvm.vertec_id_mandat = get_value(row, 'vertec_id_mandat')
        rsvm.import_vers_adresse = get_value(row, 'import_vers_adresse')
        rsvm.thema = get_value(row, 'thema')
        rsvm.formal_gepr = get_value(row, 'formal_gepr')
        rsvm.inhalt_gepr = get_value(row, 'inhalt_gepr')
        rsvm.dokument = get_value(row, 'dokument')
        rsvm.file_upload = get_value(row, 'file_upload')

        try:
            if existing:
                rsvm.save()
            else:
                rsvm.insert()
            frappe.db.commit()
        except Exception as err:
            failed.append([get_value(row, 'vertec_id_mandat'), str(err)])

    if len(failed) > 0:
        print(failed)
        frappe.log_error(str(failed), "mvzh_rsvmitglieder Import Fails")

def get_value(row, value):
    value = row[value]
    return value.strip()

def parse_csv_datetime(value):
    return getdate(value)