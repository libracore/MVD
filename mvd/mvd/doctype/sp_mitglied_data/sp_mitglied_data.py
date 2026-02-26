# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr
from mvd.mvd.doctype.mitgliedschaft.utils import prepare_mvm_for_sp
from tqdm import tqdm
from frappe.utils import cint

class SPMitgliedData(Document):
    pass

def create_or_update_sp_mitglied_data(mitglied_nr, mitglied_id, timestamp_mismatch_retry=False):
    try:
        if frappe.db.exists("SP Mitglied Data", mitglied_nr):
            update(mitglied_nr, mitglied_id)
        else:
            create(mitglied_nr, mitglied_id)
    except frappe.TimestampMismatchError as err:
        if not timestamp_mismatch_retry:
            frappe.clear_messages()
            create_or_update_sp_mitglied_data(mitglied_nr, mitglied_id, timestamp_mismatch_retry=True)
        else:
            frappe.log_error("Mitglied: {0}\n\nFehler: {1}\n\n{2}".format(mitglied_nr, str(err), frappe.get_traceback()), 'create_or_update_sp_mitglied_data Failed (timestamp_mismatch_retry)')
    except Exception as err:
        frappe.log_error("Mitglied: {0}\n\nFehler: {1}\n\n{2}".format(mitglied_nr, str(err), frappe.get_traceback()), 'create_or_update_sp_mitglied_data Failed')

def create(mitglied_nr, mitglied_id):
    if not mitglied_id:
        mitglied_id = get_mitglied_id_from_nr(mitglied_nr=mitglied_nr, ignore_inaktiv=True)
    mitgliedschaft = False
    if frappe.db.exists("Mitgliedschaft", mitglied_id):
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitglied_id)
    if mitgliedschaft:
        data =  prepare_mvm_for_sp(mitgliedschaft)
        new_record = frappe.get_doc({
            'doctype': 'SP Mitglied Data',
            'mitglied_nr': mitglied_nr,
            'needs_update': 0,
            'json': json.dumps(data, indent=2)
        })
        new_record.insert(ignore_permissions=True)
        frappe.db.commit()

def update(mitglied_nr, mitglied_id):
    if not mitglied_id:
        mitglied_id = get_mitglied_id_from_nr(mitglied_nr=mitglied_nr, ignore_inaktiv=True)
    mitgliedschaft = False
    if frappe.db.exists("Mitgliedschaft", mitglied_id):
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitglied_id)
    if mitgliedschaft:
        data =  prepare_mvm_for_sp(mitgliedschaft)
        existing_record = frappe.get_doc("SP Mitglied Data", mitglied_nr)
        existing_record.json = json.dumps(data, indent=2)
        existing_record.needs_update = 0
        existing_record.save(ignore_permissions=True)
        frappe.db.commit()
    else:
        if frappe.db.exists("SP Mitglied Data", mitglied_nr):
            # Mitglied existiert nicht, aber SP Mitglied Data schon -> Löschen
            existing_record = frappe.get_doc("SP Mitglied Data", mitglied_nr)
            existing_record.delete()
            frappe.db.commit()

'''
    Nachfolgende Methode wird mit dem "All"-Scheduler (~4') ausgeführt.
'''
def update_based_on_scheduler():
    need_updates = frappe.db.sql(
        """
            SELECT
                `name` AS `id`
            FROM `tabSP Mitglied Data`
            WHERE IFNULL(`needs_update`, 0) = 1
        """,
        as_dict=True
    )
    for need_update in need_updates:
        update(need_update.id, None)

'''
    Selbst-Heil-Methode (called via Daily Scheduler)
'''
def fixing_wrong_data(manual=False):
    if manual:
        print("Analyse DB, please wait...")
    
    mitgliedschaften = frappe.db.sql(
        """
            SELECT
                spx.ref_nr,
                spx.mitgliedId,
                spx.status
            FROM (
                SELECT
                    sp.`name` AS ref_nr,
                    JSON_UNQUOTE(JSON_EXTRACT(sp.`json`, '$.mitgliedId')) AS mitgliedId,
                    CASE JSON_UNQUOTE(JSON_EXTRACT(sp.`json`, '$.status'))
                        WHEN 'Regulaer' THEN 'Regulär'
                        WHEN 'OnlineAnmeldung' THEN 'Online-Anmeldung'
                        WHEN 'OnlineBeitritt' THEN 'Online-Beitritt'
                        WHEN 'OnlineKuendigung' THEN 'Online-Kündigung'
                        WHEN 'Kuendigung' THEN 'Kündigung'
                        WHEN 'InteressentIn' THEN 'Interessent*in'
                        ELSE JSON_UNQUOTE(JSON_EXTRACT(sp.`json`, '$.status'))
                    END AS status
                FROM `tabSP Mitglied Data` sp
            ) spx
            LEFT JOIN `tabMitgliedschaft` m
                ON m.`mitglied_nr` = spx.ref_nr
                AND m.`status_c` = spx.status
                AND m.`mitglied_id` = spx.mitgliedId
            WHERE m.`mitglied_nr` IS NULL;
        """,
        as_dict=True
    )

    affected_qty = 0
    affected_records = []

    if not manual:
        for mitgliedschaft in mitgliedschaften:
            mitglied_id = get_mitglied_id_from_nr(mitglied_nr=mitgliedschaft.ref_nr, ignore_inaktiv=True)
            if cint(frappe.db.get_value("Mitgliedschaft", mitglied_id, "validierung_notwendig")) != 1:
                create_or_update_sp_mitglied_data(mitgliedschaft.ref_nr, mitglied_id)
                affected_qty += 1
                affected_records.append(mitgliedschaft.ref_nr)
    else:
        for mitgliedschaft in tqdm(mitgliedschaften, desc="fixing_wrong_data", unit=" Corr.", total=len(mitgliedschaften)):
            mitglied_id = get_mitglied_id_from_nr(mitglied_nr=mitgliedschaft.ref_nr, ignore_inaktiv=True)
            if cint(frappe.db.get_value("Mitgliedschaft", mitglied_id, "validierung_notwendig")) != 1:
                create_or_update_sp_mitglied_data(mitgliedschaft.ref_nr, mitglied_id)
                affected_qty += 1
                affected_records.append(mitgliedschaft.ref_nr)
    
    if manual:
        print("{0} korrigiert".format(affected_qty))
        print(affected_records)
    
    if affected_qty > 0:
        frappe.log_error("Anzahl korrigiert: {0}\nDatensätze: {1}".format(affected_qty, affected_records), 'SP Mitlgied Data fixing_wrong_data')