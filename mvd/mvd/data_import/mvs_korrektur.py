# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd


# Header mapping (ERPNext <> MVD)
hm = {
    'asloca_id': 'asloca_id',
    'region': 'region',
    'mitglied_id': 'mitglied_id'
}

def read_csv(site_name, file_name, limit=False, bench='frappe'):
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench))
    
    # loop through rows
    count = 1
    max_loop = limit
    commit_count = 1
    
    if not limit:
        index = df.index
        max_loop = len(index)
    
    error_list = []
        
    for index, row in df.iterrows():
        if count <= max_loop:
            try:
                frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `asloca_id` = '{0}', `region` = '{1}' WHERE `name` = '{2}'""".format(get_value(row, 'asloca_id'), get_value(row, 'region'), get_value(row, 'mitglied_id')))
            except:
                error_list.append(str(row))
            print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
            if commit_count == 100:
                frappe.db.commit()
                commit_count = 1
            else:
                commit_count += 1
        else:
            break

    print(error_list)

def get_value(row, value):
    value = row[hm[value]]
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