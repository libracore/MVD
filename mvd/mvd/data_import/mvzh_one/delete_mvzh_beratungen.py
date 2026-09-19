# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from tqdm import tqdm
import pandas as pd

'''
    Lösche MVZH Beratungen
    -----------------
    Prod:
    sudo bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_one.delete_mvzh_beratungen.delete --kwargs "{'site_name': 'libracore.mieterverband.ch', 'file_name': 'xyz.csv', 'bench': 'frappe'}"
    Test:
    sudo bench --site test-libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_one.delete_mvzh_beratungen.delete --kwargs "{'site_name': 'test-libracore.mieterverband.ch', 'file_name': 'xyz.csv', 'bench': 'frappe'}"
    VM:
    bench execute mvd.mvd.data_import.mvzh_one.delete_mvzh_beratungen.delete --kwargs "{'site_name': 'mvd', 'file_name': 'xyz.csv', 'bench': 'mvd', 'limit': 100}"
'''
def delete(site_name=None, file_name=None, bench=None, limit=0):
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench), sep=",", dtype=str, keep_default_na=False)
    sperrliste = []
    for index, row in df.iterrows():
        sperrliste.append(get_value(row, 'Beratungs-ID Homepage'))

    limit_filter = ''
    if limit > 0:
        limit_filter = 'LIMIT {0}'.format(limit)

    sperrliste_sql = ", ".join(["'{0}'".format(x) for x in sperrliste])
    query = """
        SELECT `name` FROM `tabBeratung`
        WHERE `sektion_id` = 'MVZH'
        AND `creation` < '2026-09-18 18:00:00'
        AND `name` NOT IN ({0})
        ORDER BY `creation` ASC
        {1}
    """.format(sperrliste_sql, limit_filter)

    beratungen = frappe.db.sql(
        query,
        as_dict=True
    )

    fails = []
    for beratung in tqdm(beratungen, desc="Lösche Beratungen", unit=" Beratung", total=len(beratungen)):
        try:
            b = frappe.get_doc("Beratung", beratung.name)
            files = frappe.db.sql(
                """
                    SELECT `name` FROM `tabFile`
                    WHERE `attached_to_doctype` = 'Beratung'
                    AND `attached_to_name` = '{0}'
                """.format(beratung.name.replace("'", "''")),
                as_dict=True
            )
            for file in files:
                f = frappe.get_doc("File", file.name)
                f.delete()
            b.delete()
            frappe.db.commit()
        except Exception as err:
            fails.append([beratung.name, str(err)])

    if len(fails) > 0:
        print(str(fails))
        frappe.log_error(str(fails), "delete_mvzh_beratungen fails")

def get_value(row, value):
    value = row[value]
    return value.strip()
