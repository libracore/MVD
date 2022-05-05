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
    
    # Zuteilen Region innerhalb PLZ Range(s)
    for plz in region.plz_zuordnung:
        mitgliedschaften_query = """WHERE `region_manuell` != 1
                                    AND `plz` >= '{plz_von}'
                                    AND `plz` <= '{plz_bis}'
                                    AND `region` != '{region}'
                                    AND `sektion_id` = '{sektion}'
                                    AND `status_c` != 'Inaktiv'""".format(plz_von=plz.plz_von, \
                                                                        plz_bis=plz.plz_bis, \
                                                                        region=region.name, \
                                                                        sektion=region.sektion_id)
        
        mitgliedschaften_queue = frappe.db.sql("""SELECT
                                                        `name`
                                                    FROM `tabMitgliedschaft`
                                                    {mitgliedschaften_query}""".format(mitgliedschaften_query=mitgliedschaften_query), as_dict=True)
        frappe.db.sql("""SET SQL_SAFE_UPDATES=0""", as_list=True)
        mitgliedschafts_update = frappe.db.sql("""UPDATE `tabMitgliedschaft`
                                                    SET `region` = '{region}'
                                                    {mitgliedschaften_query}""".format(region=region.name, mitgliedschaften_query=mitgliedschaften_query), as_list=True)
        frappe.db.sql("""SET SQL_SAFE_UPDATES=1""", as_list=True)
        frappe.db.commit()
    
    args = {
        'mitgliedschaften_queue': mitgliedschaften_queue
    }
    enqueue("mvd.mvd.doctype.region.region.create_queues", queue='long', job_name='Zuteilung Region {0}'.format(region.name), timeout=5000, **args)
    
    # Löschen von Falsch-Zuteilungen (PLZ ausserhalb Range(s))
    mitgliedschaften_query = """WHERE `region_manuell` != 1
                                AND `region` = '{region}'
                                AND `sektion_id` = '{sektion}'
                                AND `status_c` != 'Inaktiv'""".format(plz_von=plz.plz_von, \
                                                                    plz_bis=plz.plz_bis, \
                                                                    region=region.name, \
                                                                    sektion=region.sektion_id)
    for plz in region.plz_zuordnung:
        mitgliedschaften_query += """ AND `plz` NOT BETWEEN {plz_von} AND {plz_bis}""".format(plz_von=plz.plz_von, \
                                                                    plz_bis=plz.plz_bis)
    
    mitgliedschaften_queue = frappe.db.sql("""SELECT
                                                    `name`
                                                FROM `tabMitgliedschaft`
                                                {mitgliedschaften_query}""".format(mitgliedschaften_query=mitgliedschaften_query), as_dict=True)
    frappe.db.sql("""SET SQL_SAFE_UPDATES=0""", as_list=True)
    mitgliedschafts_update = frappe.db.sql("""UPDATE `tabMitgliedschaft`
                                                SET `region` = ''
                                                {mitgliedschaften_query}""".format(mitgliedschaften_query=mitgliedschaften_query), as_list=True)
    frappe.db.sql("""SET SQL_SAFE_UPDATES=1""", as_list=True)
    frappe.db.commit()
    
    args = {
        'mitgliedschaften_queue': mitgliedschaften_queue
    }
    enqueue("mvd.mvd.doctype.region.region.create_queues", queue='long', job_name='Entfernung von Falsch-Zuteilungen ({0})'.format(region.name), timeout=5000, **args)
    
    region.add_comment('Comment', text='Automatische Zuordnung ausgelöst')
    
    return

def create_queues(mitgliedschaften_queue):
    commit_counter = 1
    for mitgliedschaft in mitgliedschaften_queue:
        m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
        send_mvm_to_sp(m, True)
        if commit_counter == 100:
            frappe.db.commit()
            commit_counter = 1
        else:
            commit_counter += 1
    frappe.db.commit()
    return
