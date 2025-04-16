# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd
from frappe.utils.data import add_days, getdate, get_datetime, now_datetime, now


# Header mapping (ERPNext <> MVD)
hm = {
    'mitglied_nr': 'mitglied_nr',
    'mitglied_id': 'mitglied_id',
    'status_c': 'status_c',
    'sektion_id': 'sektion_id',
    'zuzug_sektion': 'sektion_zq_id',
    'mitgliedtyp_c': 'mitgliedtyp_c',
    'mitglied_c': 'mitglied_c',
    'wichtig': 'wichtig',
    'eintritt': 'datum_eintritt',
    'austritt': 'datum_austritt',
    'wegzug': 'datum_wegzug',
    'zuzug': 'datum_zuzug',
    'kuendigung': 'datum_kuend_per',
    'adresstyp_c': 'adresstyp_c',
    'adress_id': 'adress_id',
    'firma': 'firma',
    'zusatz_firma': 'zusatz_firma',
    'anrede_c': 'anrede_c',
    'nachname_1': 'nachname_1',
    'vorname_1': 'vorname_1',
    'tel_p_1': 'tel_p_1',
    'tel_m_1': 'tel_m_1',
    'tel_g_1': 'tel_g_1',
    'e_mail_1': 'e_mail_1',
    'zusatz_adresse': 'zusatz_adresse',
    'strasse': 'strasse',
    'nummer': 'nummer',
    'nummer_zu': 'nummer_zu',
    'postfach': 'postfach',
    'postfach_nummer': 'postfach_nummer',
    'plz': 'plz',
    'ort': 'ort',
    'nachname_2': 'nachname_2',
    'vorname_2': 'vorname_2',
    'tel_p_2': 'tel_p_2',
    'tel_m_2': 'tel_m_2',
    'tel_g_2': 'tel_g_2',
    'e_mail_2': 'e_mail_2',
    'datum': 'datum',
    'jahr': 'jahr',
    'offen': 'offen',
    'ref_nr_five_1': 'ref_nr_five_1',
    'kz_1': 'kz_1',
    'tkategorie_d': 'tkategorie_d',
    'pers_name': 'pers_name',
    'datum_von': 'datum_von',
    'datum_bis': 'datum_bis',
    'datum_erinnerung': 'datum_erinnerung',
    'notiz_termin': 'notiz_termin',
    'erledigt': 'erledigt',
    'nkategorie_d': 'nkategorie_d',
    'notiz': 'notiz',
    'weitere_kontaktinfos': 'weitere_kontaktinfos',
    'mkategorie_d': 'mkategorie_d',
    'benutzer_name': 'benutzer_name',
    'jahr_bez_mitgl': 'jahr_bez_mitgl',
    'objekt_hausnummer': 'objekt_hausnummer',
    'nummer_zu': 'nummer_zu',
    'objekt_nummer_zu': 'objekt_nummer_zu',
    'rg_nummer_zu': 'rg_nummer_zu',
    'buchungen': 'buchungen',
    'online_haftpflicht': 'online_haftpflicht',
    'online_gutschrift': 'online_gutschrift',
    'online_betrag': 'online_betrag',
    'datum_online_verbucht': 'datum_online_verbucht',
    'datum_online_gutschrift': 'datum_online_gutschrift',
    'online_payment_method': 'online_payment_method',
    'online_payment_id': 'online_payment_id',
    'region_d': 'region_d',
    'plz_von': 'plz_von',
    'plz_bis': 'plz_bis',
    'status': 'status',
    'mv_mitgliedschaft': 'mv_mitgliedschaft',
    'ausgabe': 'ausgabe',
    'legacy_kategorie_code': 'legacy_kategorie_code',
    'legacy_notiz': 'legacy_notiz',
    'grund_code': 'grund_code',
    'grund_bezeichnung': 'grund_bezeichnung',
    'retoure_mw_sequence_number': 'retoure_mw_sequence_number',
    'retoure_dmc': 'retoure_dmc',
    'retoure_sendungsbild': 'retoure_sendungsbild',
    'datum_erfasst_post': 'datum_erfasst_post',
    'jahr': 'jahr'
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
        
    for index, row in df.iterrows():
        if count <= max_loop:
            if not migliedschaft_existiert(str(get_value(row, 'mitglied_id'))):
                if get_value(row, 'adresstyp_c') == 'MITGL':
                    create_mitgliedschaft(row)
                else:
                    frappe.log_error("{0}".format(row), 'Adresse != MITGL, aber ID noch nicht erfasst')
            else:
                update_mitgliedschaft(row)
            print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
        else:
            break
            
def create_mitgliedschaft(data):
    try:
        mitgliedschaft = frappe.get_doc({
            "doctype": "Mitgliedschaft",
            "sektion_id": "MVD",
            "status_c": "Regulär",
            "language": "fr",
            "mitgliedtyp_c": "Privat",
            "eintrittsdatum": "2000-01-01",
            "kundentyp": "Einzelperson",
            "firma": '',
            "zusatz_firma": '',
            "anrede_c": '',
            "nachname_1": "TestanlageNachname",
            "vorname_1": "TestanlageVorname",
            "tel_p_1": '055 246 49 36',
            "tel_m_1": '079 489 84 48',
            "tel_g_1": '',
            "e_mail_1": 'test@email.ch',
            "zusatz_adresse": '',
            "strasse": "Musterstrasse",
            "nummer": "15",
            "nummer_zu": '',
            "postfach": 0,
            "postfach_nummer": '',
            "plz": "8330",
            "ort": "Pfäffikon ZH",
            "asloca_id": "xxx"
        })
        mitgliedschaft.insert(ignore_permissions=True)

        frappe.db.commit()
        return
    except Exception as err:
        frappe.log_error("{0}\n---\n{1}".format(err, data), 'create_mitgliedschaft')
        return

def update_mitgliedschaft(data):
    try:
        mitgliedschaft = frappe.get_doc("MV Mitgliedschaft", str(get_value(data, 'mitglied_id')))
        mitgliedschaft.save(ignore_permissions=True)
        frappe.db.commit()
        return
    except Exception as err:
        frappe.log_error("{0}\n{1}".format(err, data), 'update_mitgliedschaft')
        return

def get_formatted_datum(datum):
    if datum:
        datum_raw = datum.split(" ")[0]
        if not datum_raw:
            return ''
        else:
            return datum_raw.replace("/", "-")
    else:
        return ''

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

def migliedschaft_existiert(mitglied_id):
    anz = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabMitgliedschaft` WHERE `mitglied_id` = '{mitglied_id}'""".format(mitglied_id=mitglied_id), as_dict=True)[0].qty
    if anz > 0:
        return True
    else:
        return False