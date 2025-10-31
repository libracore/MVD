# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from tqdm import tqdm

def clean_up():
    mitgliedschaften = frappe.db.sql("""select distinct mitglied_id from tabDigitalrechnung WHERE sektion_id = 'MVZH' and opt_in is not NULL""", as_dict=True)

    for mitgliedschaft in tqdm(mitgliedschaften, desc="Cleanup Digi-RG-DS", unit=" Cleanups", total=len(mitgliedschaften)):
        m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.mitglied_id)
        if m.digitalrechnung != 1:
            m.digitalrechnung = 1
            m.save()
            frappe.db.commit()