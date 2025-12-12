# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import time
import random
import pymysql

class Region(Document):
    pass

@frappe.whitelist()
def zuordnung(region):
    region = frappe.get_doc("Region", region)
    
    regionen = frappe.db.sql("""SELECT `name` FROM `tabRegion` WHERE `disabled` != 1 AND `sektion_id` = '{sektion}'""".format(sektion=region.sektion_id), as_dict=True)
    for reg in regionen:
        r = frappe.get_doc("Region", reg.name)
        r.auto_zuordnung = 1
        r.save()
    
    return

def _regionen_zuteilung():
    def verarbeitung_region(region, plz):
        mitgliedschaften_query = """WHERE `region_manuell` != 1
                                    AND `status_c` != 'Inaktiv'
                                    AND (
                                        CAST(IFNULL(`plz`, 0) AS INTEGER) BETWEEN {plz_von} AND {plz_bis}
                                    )
                                    AND (
                                        `region` != '{region}' OR `region` IS NULL
                                    )
                                    AND `sektion_id` = '{sektion}'""".format(plz_von=plz.plz_von, \
                                                                        plz_bis=plz.plz_bis, \
                                                                        region=region.name, \
                                                                        sektion=region.sektion_id)
        
        mitgliedschaften = frappe.db.sql("""SELECT
                                                        `name`
                                                    FROM `tabMitgliedschaft`
                                                    {mitgliedschaften_query}""".format(mitgliedschaften_query=mitgliedschaften_query), as_dict=True)
        
        for i, mitgliedschaft in enumerate(mitgliedschaften, 1):
            frappe.db.set_value(
                "Mitgliedschaft",
                mitgliedschaft.name,
                "region",
                region.name,
                update_modified=False
            )
            if i % 100 == 0:
                frappe.db.commit()
        frappe.db.commit()

    def delete_falsch_zuteilungen(region):
        # Löschen von Falsch-Zuteilungen (PLZ ausserhalb Range(s))
        mitgliedschaften_query = """WHERE `region_manuell` != 1
                                    AND `region` = '{region}'
                                    AND `sektion_id` = '{sektion}'
                                    AND `status_c` != 'Inaktiv'""".format(region=region.name, \
                                                                        sektion=region.sektion_id)
        for plz in region.plz_zuordnung:
            mitgliedschaften_query += """AND (CAST(IFNULL(`plz`, 0) AS INTEGER) NOT BETWEEN {plz_von} AND {plz_bis})""".format(plz_von=plz.plz_von, \
                                                                                                                            plz_bis=plz.plz_bis)
        
        mitgliedschaften = frappe.db.sql("""SELECT
                                                `name`
                                            FROM `tabMitgliedschaft`
                                            {mitgliedschaften_query}""".format(mitgliedschaften_query=mitgliedschaften_query), as_dict=True)
        
        for i, mitgliedschaft in enumerate(mitgliedschaften, 1):
            frappe.db.set_value(
                "Mitgliedschaft",
                mitgliedschaft.name,
                "region",
                '',
                update_modified=False
            )
            if i % 100 == 0:
                frappe.db.commit()
        frappe.db.commit()
        
        return
    
    regionen = frappe.db.sql("""SELECT `name` FROM `tabRegion` WHERE `auto_zuordnung` = 1 AND `disabled` != 1""", as_dict=True)
    for reg in regionen:
        # Zuteilen Region innerhalb PLZ Range(s)
        region = frappe.get_doc("Region", reg.name)
        for plz in region.plz_zuordnung:
            run_with_lock_retry(verarbeitung_region, region, plz)
        run_with_lock_retry(delete_falsch_zuteilungen, region)
        region.auto_zuordnung = 0
        region.save()
        frappe.db.commit()
    return



def run_with_lock_retry(fn, *args, retries=3, base_sleep=0.25, **kwargs):
    #Führt fn(*args, **kwargs) aus und retried bei Lock wait timeout (1205)

    LOCK_WAIT_TIMEOUT_CODE = 1205
    for attempt in range(retries + 1):
        try:
            return fn(*args, **kwargs)

        except pymysql.err.OperationalError as e:
            if e.args and e.args[0] == LOCK_WAIT_TIMEOUT_CODE and attempt < retries:
                frappe.db.rollback()

                sleep_s = base_sleep * (2 ** attempt)
                sleep_s += random.uniform(0, 0.1)
                time.sleep(sleep_s)

                continue

            # sonstiger DB-Fehler oder keine Retries mehr
            frappe.db.rollback()
            raise

        except Exception:
            # kein DB-Lock-Problem
            frappe.db.rollback()
            raise
