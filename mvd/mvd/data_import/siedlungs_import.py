# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd
from tqdm import tqdm

'''
    Prod:
    sudo bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.siedlungs_import.read_csv --kwargs "{'file_name': 'xyz.csv'}"
    Test:
    sudo bench --site test-libracore.mieterverband.ch execute mvd.mvd.data_import.siedlungs_import.read_csv --kwargs "{'file_name': 'xyz.csv', 'site_name': 'test-libracore.mieterverband.ch'}"
'''
def read_csv(file_name, site_name='libracore.mieterverband.ch', limit=False, bench='frappe'):
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench), sep=";", dtype=str, keep_default_na=False)

    for index, row in tqdm(df.iterrows(), desc="Import Siedlung", unit=" Imports", total=len(df.index)):
        if frappe.db.exists("Siedlung", get_value(row, 'id')):
            add_adr_egaid(row)
        else:
            create_siedlung(row)

def get_value(row, value):
    value = row[value]
    return value.strip()

def create_siedlung(row):
    siedlung = frappe.new_doc("Siedlung")
    siedlung.bezeichnung = get_value(row, 'bezeichnung')
    gebaeude_row = siedlung.append("zugehoerige_gebaeude", {})
    gebaeude_row.adr_egaid = get_value(row, 'adr_egaid').replace(".0", "")
    gebaeude_row.stn_label = get_value(row, 'stn_label')
    gebaeude_row.adr_number = get_value(row, 'adr_number')
    gebaeude_row.plz = get_value(row, 'plz')
    gebaeude_row.wohnort = get_value(row, 'wohnort')
    siedlung.insert()
    return

def add_adr_egaid(row):
    siedlung = frappe.get_doc("Siedlung", get_value(row, 'id'))
    gebaeude_row = siedlung.append("zugehoerige_gebaeude", {})
    gebaeude_row.adr_egaid = get_value(row, 'adr_egaid').replace(".0", "")
    gebaeude_row.stn_label = get_value(row, 'stn_label')
    gebaeude_row.adr_number = get_value(row, 'adr_number')
    gebaeude_row.plz = get_value(row, 'plz')
    gebaeude_row.wohnort = get_value(row, 'wohnort')
    siedlung.save()
    return