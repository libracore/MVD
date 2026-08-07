# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd
from tqdm import tqdm
from mvd.mvd.doctype.siedlungsfall.siedlungsfall import get_letzte_beratung, get_letztes_mandat
from frappe.utils.data import getdate

'''
    Import Siedlungen
    -----------------
    Prod:
    sudo bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.siedlungs_import.import_siedlungen --kwargs "{'file_name': 'xyz.csv'}"
    Test:
    sudo bench --site test-libracore.mieterverband.ch execute mvd.mvd.data_import.siedlungs_import.import_siedlungen --kwargs "{'file_name': 'xyz.csv', 'site_name': 'test-libracore.mieterverband.ch'}"
'''
def import_siedlungen(file_name, site_name='libracore.mieterverband.ch', bench='frappe'):
    def create_siedlung(row):
        siedlung = frappe.new_doc("Siedlung")
        siedlung.bezeichnung = get_value(row, 'bezeichnung')
        gebaeude_row = siedlung.append("zugehoerige_gebaeude", {})
        gebaeude_row.adr_egaid = get_value(row, 'adr_egaid').replace(".0", "")
        gebaeude_row.stn_label = get_value(row, 'stn_label')
        gebaeude_row.adr_number = get_value(row, 'adr_number')
        gebaeude_row.plz = get_value(row, 'plz')
        gebaeude_row.wohnort = get_value(row, 'wohnort')
        siedlung.insert()
        return
    
    def add_adr_egaid(row):
        siedlung = frappe.get_doc("Siedlung", get_value(row, 'id'))
        gebaeude_row = siedlung.append("zugehoerige_gebaeude", {})
        gebaeude_row.adr_egaid = get_value(row, 'adr_egaid').replace(".0", "")
        gebaeude_row.stn_label = get_value(row, 'stn_label')
        gebaeude_row.adr_number = get_value(row, 'adr_number')
        gebaeude_row.plz = get_value(row, 'plz')
        gebaeude_row.wohnort = get_value(row, 'wohnort')
        siedlung.save()
        return
    
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench), sep=";", dtype=str, keep_default_na=False)

    for index, row in tqdm(df.iterrows(), desc="Import Siedlung", unit=" Imports", total=len(df.index)):
        if frappe.db.exists("Siedlung", get_value(row, 'id')):
            add_adr_egaid(row)
        else:
            create_siedlung(row)

def get_value(row, value):
    value = row[value]
    return value.strip()

'''
    Import Siedlungsfälle
    -----------------
    Prod:
    sudo bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.siedlungs_import.import_siedlungsfaelle --kwargs "{'file_name': 'xyz.csv'}"
    Test:
    sudo bench --site test-libracore.mieterverband.ch execute mvd.mvd.data_import.siedlungs_import.import_siedlungsfaelle --kwargs "{'file_name': 'xyz.csv', 'site_name': 'test-libracore.mieterverband.ch'}"
'''
def import_siedlungsfaelle(file_name, site_name='libracore.mieterverband.ch', bench='frappe'):
    def create_siedlungsfall(row):
        siedlungsfall = frappe.new_doc("Siedlungsfall")
        siedlungsfall.flags.from_import = True
        siedlungsfall.siedlungsfall_id_legacy = get_value(row, 'siedlungsfall_id').replace(".0", "")
        siedlungsfall.siedlungsfall_title = get_value(row, 'siedlungsfall_title')
        siedlungsfall.siedlungfall_typ = get_value(row, 'siedlungfall_typ')
        siedlungsfall.creation_date = getdate(get_value(row, 'creation'))
        if get_value(row, 'abschluss'): siedlungsfall.abschluss = getdate(get_value(row, 'abschluss'))
        siedlungsfall.verantwortlich_intern = get_user_from_fullname(row)
        siedlungsfall.verantwortlich_extern = get_termin_kontaktperson(row)
        siedlungsfall.bemerkung = get_value(row, 'bemerkung')
        siedlungsfall.frist = get_value(row, 'frist')
        siedlungsfall.verwaltung = get_value(row, 'verwaltung')
        siedlungsfall.eigentuemer_in = get_value(row, 'eigentuemer_in')
        siedlungsfall.anzahl_wohnungen = get_value(row, 'anzahl_wohnungen')
        siedlungsfall.ansprechperson = get_value(row, 'ansprechperson')
        siedlungsfall.mv_mitgliedschaft = get_value(row, 'ansprechperson_mitgliedschaft').replace(".0", "")
        siedlungsfall.siedlung = get_value(row, 'siedlung')
        siedlungsfall.mandat = get_value(row, 'mandat')
        siedlungsfall.pfad = get_value(row, 'pfad')
        siedlungsfall.thema = add_thema(row)

        if get_value(row, 'mitglied_id') and frappe.db.exists("Mitgliedschaft", get_value(row, 'mitglied_id').replace(".0", "")):
            mitgl_row = siedlungsfall.append("mitgliedschaften", {})
            mitgl_row.mv_mitgliedschaft = get_value(row, 'mitglied_id').replace(".0", "")
            mitgl_row.mitglied_nr = frappe.db.get_value("Mitgliedschaft", get_value(row, 'mitglied_id').replace(".0", ""), "mitglied_nr")
            vorname_1 = frappe.db.get_value("Mitgliedschaft", get_value(row, 'mitglied_id').replace(".0", ""), "vorname_1")
            nachname_1 = frappe.db.get_value("Mitgliedschaft", get_value(row, 'mitglied_id').replace(".0", ""), "nachname_1")
            mitgl_row.mitglied_name = "{0} {1}".format(vorname_1, nachname_1)
            mitgl_row.letzte_beratung = get_letzte_beratung(get_value(row, 'mitglied_id').replace(".0", ""))
            mitgl_row.letztes_mandat = get_letztes_mandat(get_value(row, 'mitglied_id').replace(".0", ""))
            mitgl_row.eintrittsdatum = frappe.db.get_value("Mitgliedschaft", get_value(row, 'mitglied_id').replace(".0", ""), "eintrittsdatum")

        siedlungsfall.insert()
        return
    
    def get_user_from_fullname(row):
        user = frappe.db.sql(
            """
                SELECT `name` FROM `tabUser`
                WHERE `full_name` = '{0}'
            """.format(get_value(row, 'verantwortlich_intern')),
            as_dict=True
        )
        if len(user) > 0:
            return user[0].name
        return ""
    
    def get_termin_kontaktperson(row):
        user = get_user_from_fullname(row)
        if user:
            kontaktperson = frappe.db.sql(
                """
                    SELECT `parent`
                    FROM `tabTermin Kontaktperson Multi User`
                    WHERE `user` = '{0}'
                    AND `parenttype` = 'Termin Kontaktperson'
                """.format(user),
                as_dict=True
            )
            if len(kontaktperson) > 0:
                return kontaktperson[0].parent
        return ""
    
    def add_thema(row):
        # TBD wenn wirklich benötigt
        return ''
    
    def add_mitglied(row):
        if get_value(row, 'mitglied_id') and frappe.db.exists("Mitgliedschaft", get_value(row, 'mitglied_id').replace(".0", "")):
            siedlungsfall = frappe.get_doc("Siedlungsfall", {'siedlungsfall_id_legacy': get_value(row, 'siedlungsfall_id')})
            mitgl_row = siedlungsfall.append("mitgliedschaften", {})
            mitgl_row.mv_mitgliedschaft = get_value(row, 'mitglied_id').replace(".0", "")
            mitgl_row.mitglied_nr = frappe.db.get_value("Mitgliedschaft", get_value(row, 'mitglied_id').replace(".0", ""), "mitglied_nr")
            vorname_1 = frappe.db.get_value("Mitgliedschaft", get_value(row, 'mitglied_id').replace(".0", ""), "vorname_1")
            nachname_1 = frappe.db.get_value("Mitgliedschaft", get_value(row, 'mitglied_id').replace(".0", ""), "nachname_1")
            mitgl_row.mitglied_name = "{0} {1}".format(vorname_1, nachname_1)
            mitgl_row.letzte_beratung = get_letzte_beratung(get_value(row, 'mitglied_id').replace(".0", ""))
            mitgl_row.letztes_mandat = get_letztes_mandat(get_value(row, 'mitglied_id').replace(".0", ""))
            mitgl_row.eintrittsdatum = frappe.db.get_value("Mitgliedschaft", get_value(row, 'mitglied_id').replace(".0", ""), "eintrittsdatum")
            siedlungsfall.save()
        return
    
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench), sep=";", dtype=str, keep_default_na=False)
    
    for index, row in tqdm(df.iterrows(), desc="Import Siedlungsfälle", unit=" Imports", total=len(df.index)):
        if frappe.db.exists("Siedlungsfall", {'siedlungsfall_id_legacy': get_value(row, 'siedlungsfall_id')}):
            add_mitglied(row)
        else:
            create_siedlungsfall(row)