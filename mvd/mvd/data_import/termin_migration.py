# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def migrate_termin_into_beratung(sektion=None):
    '''sudo bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.termin_migration.migrate_termin_into_beratung --kwargs "{'sektion': 'MVBE'}"'''
    if not sektion:
        print("Wähle entweder Sektion oder 'alle'")
    
    if sektion != 'alle':
        sektions_filter = """ AND `sektion_id` = '{sektion}'""".format(sektion=sektion)
    else:
        sektions_filter = ''
    
    termine = frappe.db.sql("""SELECT * FROM `tabTermin` WHERE `name` NOT IN (
                                    SELECT IFNULL(`migriert_von_termin`, '') AS `name` FROM `tabBeratung`
                                ){sektions_filter}""".format(sektions_filter=sektions_filter), as_dict=True)
    
    termin_qty = len(termine)
    loop = 1
    failed = []
    for termin in termine:
        try:
            beratung = frappe.get_doc({
                'doctype': 'Beratung',
                'terminkategorie': termin.kategorie,
                'beratungskategorie': termin.beratungskategorie,
                'kontaktperson': termin.kontaktperson,
                'mv_mitgliedschaft': termin.mv_mitgliedschaft,
                'status': termin.status,
                'notiz': termin.notitz,
                'migriert_von_termin': termin.name,
                'termin': [{
                    'von': termin.von,
                    'bis': termin.bis or termin.von
                }]
            }).insert()
            print("created {0} of {1}".format(loop, termin_qty))
        except Exception as err:
            print(err)
            failed.append(termin.name)
        loop += 1
    print("failed:")
    print(failed)
