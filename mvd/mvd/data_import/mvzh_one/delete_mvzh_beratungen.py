# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from tqdm import tqdm

'''
    Lösche MVZH Beratungen
    -----------------
    Prod:
    sudo bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_one.delete_mvzh_beratungen.delete
    Test:
    sudo bench --site test-libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_one.delete_mvzh_beratungen.delete
    VM:
    bench execute mvd.mvd.data_import.mvzh_one.delete_mvzh_beratungen.delete --kwargs "{'limit': 100}"
'''
def delete(limit=0):
    limit_filter = ''
    if limit > 0:
        limit_filter = 'LIMIT {0}'.format(limit)
    beratungen = frappe.db.sql(
        """
            SELECT `name` FROM `tabBeratung`
            WHERE `sektion_id` = 'MVZH'
            {0}
        """.format(limit_filter),
        as_dict=True
    )

    for beratung in tqdm(beratungen, desc="Lösche Beratungen", unit=" Beratung", total=len(beratungen)):
        b = frappe.get_doc("Beratung", beratung.name)
        files = frappe.db.sql(
            """
                SELECT `name` FROM `tabFile`
                WHERE `attached_to_doctype` = 'Beratung'
                AND `attached_to_name` = '{0}'
            """.format(beratung.name),
            as_dict=True
        )
        for file in files:
            f = frappe.get_doc("File", file.name)
            f.delete()
        b.delete()
        frappe.db.commit()
