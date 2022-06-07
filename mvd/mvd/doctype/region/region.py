# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import send_mvm_to_sp
from frappe.utils.background_jobs import enqueue

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
    regionen = frappe.db.sql("""SELECT `name` FROM `tabRegion` WHERE `auto_zuordnung` = 1 AND `disabled` != 1""", as_dict=True)
    
    for reg in regionen:
        # Zuteilen Region innerhalb PLZ Range(s)
        region = frappe.get_doc("Region", reg.name)
        
        for plz in region.plz_zuordnung:
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
            
            commit_counter = 1
            for mitgliedschaft in mitgliedschaften:
                m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
                m.region = region.name
                m.save()
                if commit_counter == 100:
                    frappe.db.commit()
                    commit_counter = 1
                else:
                    commit_counter += 1
            frappe.db.commit()
        
        # Löschen von Falsch-Zuteilungen (PLZ ausserhalb Range(s))
        mitgliedschaften_query = """WHERE `region_manuell` != 1
                                    AND `region` = '{region}'
                                    AND `sektion_id` = '{sektion}'
                                    AND `status_c` != 'Inaktiv'""".format(plz_von=plz.plz_von, \
                                                                        plz_bis=plz.plz_bis, \
                                                                        region=region.name, \
                                                                        sektion=region.sektion_id)
        for plz in region.plz_zuordnung:
            mitgliedschaften_query += """AND (CAST(IFNULL(`plz`, 0) AS INTEGER) NOT BETWEEN {plz_von} AND {plz_bis})""".format(plz_von=plz.plz_von, \
                                                                                                                            plz_bis=plz.plz_bis)
        
        mitgliedschaften = frappe.db.sql("""SELECT
                                                `name`
                                            FROM `tabMitgliedschaft`
                                            {mitgliedschaften_query}""".format(mitgliedschaften_query=mitgliedschaften_query), as_dict=True)
        
        commit_counter = 1
        for mitgliedschaft in mitgliedschaften:
            m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
            m.region = ''
            m.save()
            if commit_counter == 100:
                frappe.db.commit()
                commit_counter = 1
            else:
                commit_counter += 1
        frappe.db.commit()
        
        region.auto_zuordnung = 0
        region.save()
        
    return
