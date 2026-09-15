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
    sudo bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_one.mvzh_debitoren_miveba.import_from_file --kwargs "{'file_name': 'xyz.csv'}"
    Test:
    sudo bench --site test-libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_one.mvzh_debitoren_miveba.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'test-libracore.mieterverband.ch'}"
    Alte Dev VM (Oracle):
    bench execute mvd.mvd.data_import.mvzh_one.mvzh_debitoren_miveba.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'site1.local', 'bench': 'frappe'}"
    Multi-Bench VM:
    bench execute mvd.mvd.data_import.mvzh_one.mvzh_debitoren_miveba.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'mvd', 'bench': 'mvd'}"
'''
def import_from_file(file_name, site_name='libracore.mieterverband.ch', bench='frappe'):
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench), sep=",", dtype=str, keep_default_na=False)

    skipped_miveba_entry = []
    print("Starte Import...")
    for index, row in tqdm(df.iterrows(), desc="Import Miveba Zahlungen", unit=" Zahlungen", total=len(df.index)):
        if not get_value(row, 'mitglied_id') or get_value(row, 'mitglied_id') == '':
            skipped_miveba_entry.append(row)
            continue

        if frappe.db.exists("Mitgliedschaft", get_value(row, 'mitglied_id')):
            frappe.db.set_value("Mitgliedschaft", get_value(row, 'mitglied_id'), "miveba_buchungen", get_value(row, 'miveba_buchungen'))
            frappe.db.commit()

    if len(skipped_miveba_entry) > 0:
        frappe.log_error(str(skipped_miveba_entry), "Miveba Zahlungen Import Skippings")
        frappe.db.commit()
        print("Miveba Zahlungen Import Skippings")
        print(skipped_miveba_entry)

def get_value(row, value):
    value = row[value]
    return value.strip()