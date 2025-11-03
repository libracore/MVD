# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from tqdm import tqdm

# mvd.mvd.data_import.digital_rg_hash_cleanup.clean_up
def clean_up():
    mitgliedschaften = frappe.db.sql("""
        SELECT
            tm.name AS `mitglied`,
            tm.mitglied_hash as `hash`
        FROM tabMitgliedschaft AS tm
        WHERE tm.aktive_mitgliedschaft = 1
        AND NOT EXISTS (
            SELECT 1
            FROM tabDigitalrechnung AS td
            WHERE td.mitglied_id = tm.name
            AND td.hash <=> tm.mitglied_hash
        );
    """, as_dict=True)

    for mitgliedschaft in tqdm(mitgliedschaften, desc="Cleanup Digi-RG-Hash", unit=" Cleanups", total=len(mitgliedschaften)):
        if not frappe.db.exists("Digitalrechnung", {'mitglied_id': mitgliedschaft.mitglied, 'hash': mitgliedschaft.hash}):
            existing = frappe.db.exists("Digitalrechnung", {'mitglied_id': mitgliedschaft.mitglied})
            if existing:
                frappe.db.set_value("Digitalrechnung", existing, 'hash', mitgliedschaft.hash)
            else:
                m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.mitglied)
                m.save()
            frappe.db.commit()
