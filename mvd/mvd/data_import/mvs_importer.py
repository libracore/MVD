# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd
from frappe.utils.data import add_days, getdate, get_datetime, now_datetime, now
from tqdm import tqdm


# Header mapping (ERPNext <> MVD)
hm = {
    'asloca_id': 'asloca_id',
    'sektion_id': 'sektion_id',
    'region': 'region',
    'anrede_c': 'anrede_c',
    'firma': 'firmenname',
    'nachname_1': 'nachname_1',
    'vorname_1': 'vorname_1',
    'zusatz': 'zusatz',
    'strasse': 'strasse',
    'plz': 'plz',
    'ort': 'ort',
    'language': 'language',
    'zusatz_adresse': 'zusatz',
    'zusatz_firma': 'zusatz_firma',
    'nachname_2': 'nachname_2',
    'anrede_2': 'anrede_2',
    'vorname_2': 'vorname_2',
    'nachname_2': 'nachname_2'
}

def read_csv(site_name, file_name, limit=False, bench='frappe'):
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench))
    
    # loop through rows
    count = 1
    max_loop = limit
    
    if not limit:
        index = df.index
        max_loop = len(index)
    
    error_list = []
    added = 0
    updated = 0
    for index, row in tqdm(df.iterrows(), desc="Create / Update MVS", unit=" Mitglied", total=max_loop):
        if count <= max_loop:
            existing = migliedschaft_existiert(get_value(row, 'asloca_id'))
            if not existing:
                error_in_creation = create_mitgliedschaft(row)
                if error_in_creation:
                    error_list.append(error_in_creation)
                else:
                    added += 1
            else:
                error_in_update = update_mitgliedschaft(existing, row)
                if error_in_update:
                    error_list.append(error_in_update)
                else:
                    updated += 1
            count += 1
        else:
            break

    print("Added: {0}".format(added))
    print("Updated: {0}".format(updated))
    print("Failed:")
    print(error_list)

def create_mitgliedschaft(data):
    def get_kundentyp(data):
        if get_value(data, 'firmenname') and get_value(data, 'firmenname') != '':
            return 'Unternehmen'
        else:
            return 'Einzelperson'
        
    
    def get_strasse(data):
        str_list = get_value(data, 'strasse').split(" ")
        return get_value(data, 'strasse').replace(" {0}".format(str_list[len(str_list) - 1]), "")
    
    def get_nummer(data):
        str_list = get_value(data, 'strasse').split(" ")
        return str_list[len(str_list) - 1]
    
    def check_solidarmitglied(data):
        if get_value(data, 'nachname_2') and get_value(data, 'nachname_2') != '':
            return 1
        else:
            return 0
    
    try:
        mitgliedschaft = frappe.get_doc({
            "doctype": "Mitgliedschaft",
            "sektion_id": get_value(data, 'sektion_id'),
            "status_c": "Regulär",
            "language": get_value(data, 'language'),
            "mitgliedtyp_c": "Privat",
            "eintrittsdatum": "1900-01-01",
            "kundentyp": get_kundentyp(data),
            "firma": get_value(data, 'firma'),
            "zusatz_firma": get_value(data, 'zusatz_firma'),
            "anrede_c": get_value(data, 'anrede_c'),
            "nachname_1": get_value(data, 'nachname_1'),
            "vorname_1": get_value(data, 'vorname_1'),
            "tel_p_1": '',
            "tel_m_1": '',
            "tel_g_1": '',
            "e_mail_1": '',
            "zusatz_adresse": get_value(data, 'zusatz_adresse'),
            "strasse": get_strasse(data),
            "nummer": get_nummer(data),
            "nummer_zu": '',
            "postfach": 0,
            "postfach_nummer": '',
            "plz": get_value(data, 'plz'),
            "ort": get_value(data, 'ort'),
            "asloca_id": get_value(data, 'asloca_id'),
            "region_manuell": 1,
            'hat_solidarmitglied': check_solidarmitglied(data),
            'anrede_2': get_value(data, 'anrede_2'),
            'vorname_2': get_value(data, 'vorname_2'),
            'nachname_2': get_value(data, 'nachname_2'),
        })
        mitgliedschaft.insert(ignore_permissions=True)

        frappe.db.commit()
        return False
    except Exception as err:
        frappe.log_error("{0}\n---\n{1}".format(err, data), 'create_mvs_mitgliedschaft')
        return [get_value(data, 'asloca_id'), str(err)]

def update_mitgliedschaft(mitglied_id, data):
    try:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitglied_id)
        fields = [
            'sektion_id',
            'region',
            'anrede_c',
            'firma',
            'nachname_1',
            'vorname_1',
            'strasse',
            'plz',
            'ort',
            'language',
            'zusatz_adresse',
            'zusatz_firma',
            'nachname_2',
            'anrede_2',
            'vorname_2',
            'nachname_2'
        ]
        for field in fields:
            if get_value(data, field) != mitgliedschaft.get(field, ''):
                frappe.db.set_value("Mitgliedschaft", mitglied_id, field, get_value(data, field))
        frappe.db.commit()
        return False
    except Exception as err:
        frappe.log_error("{0}\n{1}".format(err, data), 'update_mitgliedschaft')
        return [get_value(data, 'asloca_id'), str(err)]

# def get_formatted_datum(datum):
#     if datum:
#         datum_raw = datum.split(" ")[0]
#         if not datum_raw:
#             return ''
#         else:
#             return datum_raw.replace("/", "-")
#     else:
#         return ''

def get_value(row, value):
    value = row[hm[value]]
    if not pd.isnull(value):
        try:
            if isinstance(value, str):
                return value.strip()
            else:
                return value
        except:
            return value
    else:
        return ''

def migliedschaft_existiert(asloca_id):
    mitglied = frappe.db.sql("""SELECT `name` AS `mitglied` FROM `tabMitgliedschaft` WHERE `asloca_id` = '{asloca_id}'""".format(asloca_id=asloca_id), as_dict=True)
    if len(mitglied) > 0:
        return mitglied[0].mitglied
    else:
        return False