# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd


# Header mapping (ERPNext <> MVD)
hm = {
    'mitglied_nr': 'mitglied_nr',
    'mitglied_id': 'mitglied_id',
    'status_c': 'status_c',
    'sektion_id': 'sektion_id',
    'mitgliedtyp_c': 'mitgliedtyp_c',
    'mitglied_c': 'mitglied_c',
    # 'inkl_hv':, --> woher kommt diese Info?
    # 'm_und_w': 'zeitung_anzahl', --> Checkbox noch nicht implementiert --> zeitung_anzahl = 1 oder 0
    'wichtig': 'wichtig',
    'eintritt': 'datum_eintritt',
    'austritt': 'datum_austritt',
    'wegzug': 'datum_wegzug',
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
    # ! solidarmitglieddaten:
    #'anrede_2':, --> info fehlt!
    'nachname_2': 'nachname_2',
    'vorname_2': 'vorname_2',
    'tel_p_2': 'tel_p_2',
    'tel_m_2': 'tel_m_2',
    'tel_g_2': 'tel_g_2',
    'e_mail_2': 'e_mail_2'
    # ! nicht zugewiesene felder aus csv:
    # 'adress_identifier': 'adress_identifier'
    # 'sprache_c': 'sprache_c'
}

def read_csv(site_name, file_name, limit=False):
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/frappe-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name))
    
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
        if get_value(data, 'vorname_2') or get_value(data, 'nachname_2'):
            hat_solidarmitglied = 1
        else:
            hat_solidarmitglied = 0
        strasse = get_value(data, 'strasse')
        postfach = check_postfach(data, 'postfach')
        if postfach == 1:
            strasse = 'Postfach'
        else:
            if get_value(data, 'postfach_nummer') and not strasse:
                strasse = 'Postfach'
                postfach = 1
        
        kundentyp = 'Einzelperson'
        if get_value(data, 'mitgliedtyp_c') == 'GESCH':
            kundentyp = 'Unternehmen'
        
        new_mitgliedschaft = frappe.get_doc({
            'doctype': 'MV Mitgliedschaft',
            'mitglied_nr': str(get_value(data, 'mitglied_nr')).zfill(8),
            'mitglied_id': str(get_value(data, 'mitglied_id')),
            'status_c': get_status_c(get_value(data, 'status_c')),
            'sektion_id': get_sektion(get_value(data, 'sektion_id')),
            'mitgliedtyp_c': get_mitgliedtyp_c(get_value(data, 'mitgliedtyp_c')),
            'mitglied_c': get_mitglied_c(get_value(data, 'mitglied_c')),
            #'wichtig': get_value(data, 'wichtig'),
            'eintritt': get_formatted_datum(get_value(data, 'eintritt')),
            'austritt': get_formatted_datum(get_value(data, 'austritt')),
            'wegzug': get_formatted_datum(get_value(data, 'wegzug')),
            'kuendigung': get_formatted_datum(get_value(data, 'kuendigung')),
            'kundentyp': kundentyp,
            'firma': get_value(data, 'firma'),
            'zusatz_firma': get_value(data, 'zusatz_firma'),
            'anrede_c': get_anrede_c(get_value(data, 'anrede_c')),
            'nachname_1': get_value(data, 'nachname_1'),
            'vorname_1': get_value(data, 'vorname_1'),
            'tel_p_1': str(get_value(data, 'tel_p_1')),
            'tel_m_1': str(get_value(data, 'tel_m_1')),
            'tel_g_1': str(get_value(data, 'tel_g_1')),
            'e_mail_1': get_value(data, 'e_mail_1'),
            'zusatz_adresse': get_value(data, 'zusatz_adresse'),
            'strasse': strasse,
            'objekt_strasse': strasse, # fallback
            'objekt_ort': get_value(data, 'ort'), # fallback
            'nummer': get_value(data, 'nummer'),
            'nummer_zu': get_value(data, 'nummer_zu'),
            'postfach': postfach,
            'postfach_nummer': get_value(data, 'postfach_nummer'),
            'plz': get_value(data, 'plz'),
            'ort': get_value(data, 'ort'),
            'hat_solidarmitglied': hat_solidarmitglied,
            'nachname_2': get_value(data, 'nachname_2'),
            'vorname_2': get_value(data, 'vorname_2'),
            'tel_p_2': str(get_value(data, 'tel_p_2')),
            #'tel_m_2': str(get_value(data, 'tel_m_2')),
            'tel_g_2': str(get_value(data, 'tel_g_2')),
            'e_mail_2': str(get_value(data, 'e_mail_2'))
        })
        new_mitgliedschaft.insert()
        frappe.db.commit()
        return
    except Exception as err:
        frappe.log_error("{0}\n---\n{1}".format(err, data), 'create_mitgliedschaft')
        return

def update_mitgliedschaft(data):
    try:
        mitgliedschaft = frappe.get_doc("MV Mitgliedschaft", str(get_value(data, 'mitglied_id')))
        if get_value(data, 'adresstyp_c') == 'MITGL':
            # Mitglied (inkl. Soli)
            if get_value(data, 'vorname_2') or get_value(data, 'nachname_2'):
                hat_solidarmitglied = 1
            else:
                hat_solidarmitglied = 0
            strasse = get_value(data, 'strasse')
            postfach = check_postfach(data, 'postfach')
            if postfach == 1:
                strasse = 'Postfach'
            else:
                if get_value(data, 'postfach_nummer') and not strasse:
                    strasse = 'Postfach'
                    postfach = 1
            
            kundentyp = 'Einzelperson'
            if get_value(data, 'mitglied_c') == 'GESCH':
                kundentyp = 'Unternehmen'
            
            mitgliedschaft.mitglied_nr = str(get_value(data, 'mitglied_nr')).zfill(8)
            mitgliedschaft.status_c = get_status_c(get_value(data, 'status_c'))
            mitgliedschaft.sektion_id = get_sektion(get_value(data, 'sektion_id'))
            mitgliedschaft.mitgliedtyp_c = get_mitgliedtyp_c(get_value(data, 'mitgliedtyp_c'))
            mitgliedschaft.mitglied_c = get_mitglied_c(get_value(data, 'mitglied_c'))
            #mitgliedschaft.wichtig = get_value(data, 'wichtig')
            mitgliedschaft.eintritt = get_formatted_datum(get_value(data, 'eintritt'))
            mitgliedschaft.austritt = get_formatted_datum(get_value(data, 'austritt'))
            mitgliedschaft.wegzug = get_formatted_datum(get_value(data, 'wegzug'))
            mitgliedschaft.kuendigung = get_formatted_datum(get_value(data, 'kuendigung'))
            mitgliedschaft.kundentyp = kundentyp
            mitgliedschaft.firma = get_value(data, 'firma')
            mitgliedschaft.zusatz_firma = get_value(data, 'zusatz_firma')
            mitgliedschaft.anrede_c = get_anrede_c(get_value(data, 'anrede_c'))
            mitgliedschaft.nachname_1 = get_value(data, 'nachname_1')
            mitgliedschaft.vorname_1 = get_value(data, 'vorname_1')
            mitgliedschaft.tel_p_1 = str(get_value(data, 'tel_p_1'))
            mitgliedschaft.tel_m_1 = str(get_value(data, 'tel_m_1'))
            mitgliedschaft.tel_g_1 = str(get_value(data, 'tel_g_1'))
            mitgliedschaft.e_mail_1 = get_value(data, 'e_mail_1')
            mitgliedschaft.zusatz_adresse = get_value(data, 'zusatz_adresse')
            mitgliedschaft.strasse = strasse
            mitgliedschaft.nummer = get_value(data, 'nummer')
            mitgliedschaft.nummer_zu = get_value(data, 'nummer_zu')
            mitgliedschaft.postfach = postfach
            mitgliedschaft.postfach_nummer = get_value(data, 'postfach_nummer')
            mitgliedschaft.plz = get_value(data, 'plz')
            mitgliedschaft.ort = get_value(data, 'ort')
            mitgliedschaft.hat_solidarmitglied = hat_solidarmitglied
            mitgliedschaft.nachname_2 = get_value(data, 'nachname_2')
            mitgliedschaft.vorname_2 = get_value(data, 'vorname_2')
            mitgliedschaft.tel_p_2 = str(get_value(data, 'tel_p_2'))
            #mitgliedschaft.tel_m_2 = str(get_value(data, 'tel_m_2'))
            mitgliedschaft.tel_g_2 = str(get_value(data, 'tel_g_2'))
            mitgliedschaft.e_mail_2 = get_value(data, 'e_mail_2')
            mitgliedschaft.adress_id_mitglied = get_value(data, 'adress_id')
        elif get_value(data, 'adresstyp_c') == 'OBJEKT':
            # Objekt Adresse
            mitgliedschaft.objekt_zusatz_adresse = get_value(data, 'zusatz_adresse')
            mitgliedschaft.objekt_strasse = get_value(data, 'strasse') or 'Fehlende Angaben!'
            mitgliedschaft.objekt_hausnummer = get_value(data, 'nummer')
            mitgliedschaft.objekt_nummer_zu = get_value(data, 'nummer_zu')
            mitgliedschaft.objekt_plz = get_value(data, 'plz')
            mitgliedschaft.objekt_ort = get_value(data, 'ort') or 'Fehlende Angaben!'
            mitgliedschaft.adress_id_objekt = get_value(data, 'adress_id')
        elif get_value(data, 'adresstyp_c') == 'RECHN':
            # Rechnungs Adresse
            strasse = get_value(data, 'strasse')
            postfach = check_postfach(data, 'postfach')
            if postfach == 1:
                strasse = 'Postfach'
            else:
                if get_value(data, 'postfach_nummer') and not strasse:
                    strasse = 'Postfach'
                    postfach = 1
            mitgliedschaft.abweichende_rechnungsadresse = 1
            mitgliedschaft.rg_zusatz_adresse = get_value(data, 'zusatz_adresse')
            mitgliedschaft.rg_strasse = strasse
            mitgliedschaft.rg_nummer = get_value(data, 'nummer')
            mitgliedschaft.rg_nummer_zu = get_value(data, 'nummer_zu')
            mitgliedschaft.rg_postfach = postfach
            mitgliedschaft.rg_postfach_nummer = get_value(data, 'postfach_nummer')
            mitgliedschaft.rg_plz = get_value(data, 'plz')
            mitgliedschaft.rg_ort = get_value(data, 'ort')
            mitgliedschaft.adress_id_rg = get_value(data, 'adress_id')
        # else:
            # TBD!
        
        mitgliedschaft.save(ignore_permissions=True)
        frappe.db.commit()
        return
    except Exception as err:
        frappe.log_error("{0}\n{1}".format(err, data), 'update_mitgliedschaft')
        return

def get_sektion(id):
    # TBD!!!!!!!!!!
    if id == 25:
        return 'MVD'
    elif id == 4:
        return 'Bern'
    elif id == 8:
        return 'Basel Stadt'
    elif id == 14:
        return 'Luzern'
    elif id == 3:
        return 'Aargau'
    else:
        return '!TBD!'

def get_status_c(status_c):
    # Aufliestung vermutlich nicht abschliessend, prüfen!
    if status_c == 'AREG':
        return 'Mitglied'
    elif status_c == 'MUTATI':
        return 'Mutation'
    elif status_c == 'AUSSCH':
        return 'Ausschluss'
    elif status_c == 'GESTOR':
        return 'Gestorben'
    elif status_c == 'KUNDIG':
        return 'Kündigung'
    elif status_c == 'WEGZUG':
        return 'Wegzug'
    elif status_c == 'ZUZUG':
        return 'Zuzug'
    else:
        return 'Mitglied'

def get_mitgliedtyp_c(mitgliedtyp_c):
    # TBD!!!!!!!!!!
    if mitgliedtyp_c == 'PRIV':
        return 'Privat'
    else:
        return 'Privat'

def get_mitglied_c(mitglied_c):
    # TBD!!!!!!!!!!
    if mitglied_c == 'MITGL':
        return 'Mitglied'
    else:
        return 'Mitglied'

def get_anrede_c(anrede_c):
    anrede_c = int(anrede_c)
    if anrede_c == 1:
        return 'Herr'
    elif anrede_c == 2:
        return 'Frau'
    elif anrede_c == 3:
        return 'Frau und Herr'
    elif anrede_c == 4:
        return 'Herr und Frau'
    elif anrede_c == 5:
        return 'Familie'
    elif anrede_c == 7:
        return 'Herren'
    elif anrede_c == 8:
        return 'Frauen'
    else:
        return ''

def get_formatted_datum(datum):
    if datum:
        datum_raw = datum.split(" ")[0]
        if not datum_raw:
            return ''
        else:
            return datum_raw.replace("/", "-")
    else:
        return ''

def check_postfach(row, value):
    value = row[hm[value]]
    if not pd.isnull(value):
        postfach = int(value)
        if postfach < 0:
            return 1
        else:
            return 0
    else:
        return 0

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
    anz = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabMV Mitgliedschaft` WHERE `mitglied_id` = '{mitglied_id}'""".format(mitglied_id=mitglied_id), as_dict=True)[0].qty
    if anz > 0:
        return True
    else:
        return False
