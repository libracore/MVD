# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd
from tqdm import tqdm
from datetime import datetime
from frappe.utils import get_datetime

'''
    Import Beratungstermine MVZH
    -----------------
    Prod:
    sudo bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_one.mvzh_beratungstermine.import_from_file --kwargs "{'file_name': 'xyz.csv'}"
    Test:
    sudo bench --site test-libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_one.mvzh_beratungstermine.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'test-libracore.mieterverband.ch'}"
    Alte Dev VM (Oracle):
    bench execute mvd.mvd.data_import.mvzh_one.mvzh_beratungstermine.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'site1.local', 'bench': 'frappe'}"
    Multi-Bench VM:
    bench execute mvd.mvd.data_import.mvzh_one.mvzh_beratungstermine.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'mvd', 'bench': 'mvd'}"
'''
def import_from_file(file_name, site_name='libracore.mieterverband.ch', bench='frappe'):
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench), sep=",", dtype=str, keep_default_na=False)

    print("Starte Import...")
    failed = []
    erfasst = {}
    for index, row in tqdm(df.iterrows(), desc="Import Beratungstermin", unit=" Termine", total=len(df.index)):
        beratungskanal = get_value(row, "beratungskanal")
        berater_in = get_berater_in(get_value(row, "kontaktperson"))
        if not berater_in:
            failed.append([str(row), "Berater_In nicht gefunden"])
            continue

        abp_referenz = get_termin_referenz(row)
        if not abp_referenz:
            failed.append([str(row), "abp_referenz nicht gefunden"])
            continue

        if get_value(row, "Kunde-ID") in erfasst:
            beratung = frappe.get_doc("Beratung", erfasst[get_value(row, "Kunde-ID")])
        else:
            beratung = frappe.get_doc({
                "doctype": "Beratung",
                "sektion_id": "MVZH",
                "mv_mitgliedschaft": get_value(row, "mv_mitgliedschaft"),
                "faktura_kunde": None,
                "kontaktperson": berater_in,
                "notiz": "Terminnotiz:<br>{0}".format(get_value(row, "notiz")),
                "beratungskanal": beratungskanal
            })
            beratung.insert()
            erfasst[get_value(row, "Kunde-ID")] = beratung.name

        termin_row = beratung.append('termin', {})
        termin_row.von = get_value(row, "von")
        termin_row.bis = get_value(row, "bis")
        termin_row.art = beratungskanal if beratungskanal != "Telefon" else "telefonisch"
        termin_row.ort = get_value(row, "ort")
        termin_row.berater_in = berater_in
        termin_row.telefonnummer = None
        termin_row.abp_referenz = abp_referenz
        termin_row.notiz = get_value(row, "notiz")
        termin_row.wunsch_berater_in = None
        termin_row.fachskill = None
        termin_row.language = 'de'
        termin_row.beratungstyp = get_value(row, "typ")
        
        beratung.save()
        frappe.db.commit()

    if len(failed) > 0:
        print(str(failed))
        frappe.log_error(str(failed), "mvzh_beratungstermine fails")

def get_value(row, value):
    value = row[value]
    return value.strip()

def parse_csv_datetime(value):
    if not value:
        return None

    value = value.strip()

    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    raise ValueError("Ungültiges Datumsformat: {0}".format(value))

def get_berater_in(value):
    return frappe.db.exists("Termin Kontaktperson", {'kontakt': value})

def get_termin_referenz(row):
    art_ort = "{0} (MVZH)".format(get_value(row, "ort"))
    from_dt = get_datetime(get_value(row, "von"))
    date = from_dt.strftime("%Y-%m-%d")
    from_time = from_dt.strftime("%H:%M:%S")
    to_dt = get_datetime(get_value(row, "bis"))
    to_time = to_dt.strftime("%H:%M:%S")
    beratungsperson = get_berater_in(get_value(row, "kontaktperson"))
    query = """
                SELECT `name`
                FROM `tabAPB Zuweisung`
                WHERE `art_ort` = '{0}'
                AND `date` = '{1}'
                AND `from_time` LIKE '{2}%'
                AND `to_time` LIKE '{3}%'
                AND `beratungsperson` = '{4}'
    """.format(
        art_ort,
        date,
        from_time,
        to_time,
        beratungsperson
    )
    
    referenzen = frappe.db.sql(
        query,
        as_dict=True
    )

    if len(referenzen) > 0:
        return referenzen[0].name

    return False