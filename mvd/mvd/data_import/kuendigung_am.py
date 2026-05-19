# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd
from tqdm import tqdm

def read_csv(file_name, site_name='libracore.mieterverband.ch', limit=False, bench='frappe'):
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench), sep=";")

    for index, row in tqdm(df.iterrows(), desc="Korr. Kuendigung_am", unit=" Corrections", total=len(df.index)):
        mitglied = get_value(row, "name")
        if mitglied:
            frappe.db.set_value("Mitgliedschaft", mitglied, "kuendigung_am", get_value(row, "kuendigung_am"))



def get_value(row, value):
    value = row[value]
    if not pd.isnull(value):
        try:
            if isinstance(value, str):
                return value.strip()
            else:
                return value
        except:
            return value
    else:
        return ''