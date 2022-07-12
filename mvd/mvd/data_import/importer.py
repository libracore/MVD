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
    'datum_erfasst_post': 'datum_erfasst_post'
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
        
        zuzug = get_formatted_datum(get_value(data, 'zuzug'))
        if zuzug:
            zuzug_von = get_sektion(get_value(data, 'zuzug_sektion'))
        else:
            zuzug_von = ''
        
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
            #'wegzug_zu': '', --> woher kommt diese Info?
            'zuzug': zuzug,
            'zuzug_von': zuzug_von,
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
            
            zuzug = get_formatted_datum(get_value(data, 'zuzug'))
            if zuzug:
                zuzug_von = get_sektion(get_value(data, 'zuzug_sektion'))
            else:
                zuzug_von = ''
            
            mitgliedschaft.mitglied_nr = str(get_value(data, 'mitglied_nr')).zfill(8)
            mitgliedschaft.status_c = get_status_c(get_value(data, 'status_c'))
            mitgliedschaft.sektion_id = get_sektion(get_value(data, 'sektion_id'))
            mitgliedschaft.mitgliedtyp_c = get_mitgliedtyp_c(get_value(data, 'mitgliedtyp_c'))
            mitgliedschaft.mitglied_c = get_mitglied_c(get_value(data, 'mitglied_c'))
            #mitgliedschaft.wichtig = get_value(data, 'wichtig')
            mitgliedschaft.eintritt = get_formatted_datum(get_value(data, 'eintritt'))
            mitgliedschaft.austritt = get_formatted_datum(get_value(data, 'austritt'))
            mitgliedschaft.wegzug = get_formatted_datum(get_value(data, 'wegzug'))
            mitgliedschaft.zuzug = zuzug
            #mitgliedschaft.wegzug_zu = '' --> woher kommt diese Info?
            mitgliedschaft.zuzug_von = zuzug_von
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
    # Aufliestung nicht abschliessend, prüfen!
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
        return 'Sektions-ID unbekannt'

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
    anz = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabMitgliedschaft` WHERE `mitglied_id` = '{mitglied_id}'""".format(mitglied_id=mitglied_id), as_dict=True)[0].qty
    if anz > 0:
        return True
    else:
        return False




# --------------------------------------------------------------
# Debitor Importer
# --------------------------------------------------------------
def import_debitoren(site_name, file_name, limit=False, delete_from=False):
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.import_debitoren --kwargs "{'site_name': 'site1.local', 'file_name': 'offene_rechnungen.csv'}"
    '''
    
    if delete_from:
        SQL_SAFE_UPDATES_false = frappe.db.sql("""SET SQL_SAFE_UPDATES=0""", as_list=True)
        delete_sinvs = frappe.db.sql("""DELETE FROM `tabSales Invoice` WHERE `sektion_id` = '{delete_from}'
                                    AND `docstatus` = 1
                                    AND `status` = 'Overdue'""".format(delete_from=delete_from), as_list=True)
        SQL_SAFE_UPDATES_true = frappe.db.sql("""SET SQL_SAFE_UPDATES=1""", as_list=True)
        frappe.db.commit()
    
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
            if get_value(row, 'offen') > 0:
                if not migliedschaft_existiert(str(get_value(row, 'mitglied_id'))):
                    frappe.log_error("{0}".format(row), 'Mitglied existiert nicht')
                else:
                    erstelle_rechnung(row)
                print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
        else:
            break

def erstelle_rechnung(row):
    try:
        file_qrr = int(str(get_value(row, 'ref_nr_five_1')).replace(" ", ""))
        qrr = '{num:027d}'.format(num=file_qrr)
        
        existing_sinv_query = ("""SELECT `name` FROM `tabSales Invoice` WHERE REPLACE(`esr_reference`, ' ', '') = '{qrr}'""".format(qrr=qrr))
        if len(frappe.db.sql(existing_sinv_query, as_list=True)) > 0:
            frappe.log_error("{0}".format(row), 'Rechnung wurde bereits erstellt')
            return
        else:
            existing_sinv_query = ("""SELECT `name` FROM `tabSales Invoice` WHERE `mv_mitgliedschaft` = '{mitglied_id}'""".format(mitglied_id=str(get_value(row, 'mitglied_id'))))
            existing_sinv = frappe.db.sql(existing_sinv_query, as_dict=True)
            if len(existing_sinv) > 0:
                frappe.db.sql("""UPDATE `tabSales Invoice` SET `esr_reference` = '{qrr}' WHERE `name` = '{name}'""".format(qrr=qrr, name=existing_sinv[0].name), as_list=True)
                frappe.log_error("{0}".format(row), 'Update QRR')
                return
            else:
                mitgliedschaft = frappe.get_doc("Mitgliedschaft", str(get_value(row, 'mitglied_id')))
                posting_date = str(get_value(row, 'datum')).split(" ")[0]
                item = frappe.get_value("Sektion", mitgliedschaft.sektion_id, "mitgliedschafts_artikel")
                company = frappe.get_value("Sektion", mitgliedschaft.sektion_id, "company")
                cost_center = frappe.get_value("Company", company, "cost_center")
                sektions_code = str(frappe.get_value("Sektion", mitgliedschaft.sektion_id, "sektion_id"))
                
                sinv = frappe.get_doc({
                    "doctype": "Sales Invoice",
                    "company": company,
                    "customer": mitgliedschaft.rg_kunde or mitgliedschaft.kunde_mitglied,
                    "set_posting_time": 1,
                    "posting_date": posting_date,
                    "posting_time": str(get_value(row, 'datum')).split(" ")[1],
                    "ist_mitgliedschaftsrechnung": 1,
                    "mv_mitgliedschaft": mitgliedschaft.name,
                    "sektion_id": mitgliedschaft.sektion_id,
                    "sektions_code": sektions_code,
                    "mitgliedschafts_jahr": str(get_value(row, 'jahr')),
                    "due_date": add_days(posting_date, 30),
                    "esr_reference": qrr,
                    "items": [
                        {
                            "item_code": item,
                            "qty": 1,
                            "rate": get_value(row, 'offen'),
                            "cost_center": cost_center
                        }
                    ]
                })
                sinv.insert()
                sinv.submit()
                frappe.db.commit()
                return
    except Exception as err:
        frappe.log_error("{0}\n\n{1}".format(err, row), 'Rechnung konnte nicht erstellt werden')
        return

# --------------------------------------------------------------
# Miveba-Termin Importer
# --------------------------------------------------------------
def import_termine(site_name, file_name, limit=False):
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.import_termine --kwargs "{'site_name': 'site1.local', 'file_name': 'termine.csv'}"
    '''
    
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
            if frappe.db.exists("Mitgliedschaft", str(get_value(row, 'mitglied_id'))):
                try:
                    create_termin(row)
                except Exception as err:
                    frappe.log_error("{0}\n\n{1}".format(err, row), 'Termin konnte nicht erstellt werden')
            else:
                frappe.log_error("{0}".format(row), 'Mitgliedschaft existiert nicht')
            print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
        else:
            break

def create_termin(row):
    try:
        kategorie = check_kategorie(row)
        kontakt = check_kontakt(row)
        termin_status = check_termin_status(row, 'erledigt')
        sektion_id = frappe.get_value("Mitgliedschaft", str(get_value(row, 'mitglied_id')), "sektion_id")
        new = frappe.get_doc({
            "doctype": "Termin",
            "kategorie": kategorie,
            "kontakt": kontakt,
            "sektion_id": sektion_id,
            "von": str(get_value(row, 'datum_von')),
            "bis": str(get_value(row, 'datum_bis')),
            "erinnerung": str(get_value(row, 'datum_erinnerung')),
            "notitz": str(get_value(row, 'notiz_termin')),
            "status": termin_status,
            "mv_mitgliedschaft": str(get_value(row, 'mitglied_id'))
        })
        new.insert()
        frappe.db.commit()
        return
    except Exception as err:
        frappe.log_error("{0}\n\n{1}".format(err, row), 'Termin konnte nicht erstellt werden')

def check_kategorie(row):
    kategorie = str(get_value(row, 'tkategorie_d'))
    sektion_id = frappe.get_value("Mitgliedschaft", str(get_value(row, 'mitglied_id')), "sektion_id")
    query = ("""SELECT `name` FROM `tabTerminkategorie` WHERE `kategorie` = '{kategorie}' AND `sektion_id` = '{sektion_id}'""".format(kategorie=kategorie, sektion_id=sektion_id))
    kat = frappe.db.sql(query, as_list=True)
    if len(kat) > 0:
        return kat[0][0]
    else:
        new = frappe.get_doc({
            "doctype": "Terminkategorie",
            "kategorie": kategorie,
            "sektion_id": sektion_id
        })
        new.insert()
        frappe.db.commit()
        return new.name

def check_kontakt(row):
    kontakt = str(get_value(row, 'pers_name'))
    if kontakt and kontakt != '':
        sektion_id = frappe.get_value("Mitgliedschaft", str(get_value(row, 'mitglied_id')), "sektion_id")
        query = ("""SELECT `name` FROM `tabTermin Kontaktperson` WHERE `kontakt` = '{kontakt}' AND `sektion_id` = '{sektion_id}'""".format(kontakt=kontakt, sektion_id=sektion_id))
        kat = frappe.db.sql(query, as_list=True)
        if len(kat) > 0:
            return kat[0][0]
        else:
            new = frappe.get_doc({
                "doctype": "Termin Kontaktperson",
                "kontakt": kontakt,
                "sektion_id": sektion_id
            })
            new.insert()
            frappe.db.commit()
            return new.name
    else:
        return ''

def check_termin_status(row, value):
    value = row[hm[value]]
    if not pd.isnull(value):
        termin_status = int(value)
        if termin_status < 0:
            return 'Closed'
        else:
            return 'Open'
    else:
        return 'Open'

# --------------------------------------------------------------
# Miveba-Notizen Importer
# --------------------------------------------------------------
def import_notizen(site_name, file_name, limit=False):
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.import_notizen --kwargs "{'site_name': 'site1.local', 'file_name': 'notizen.csv'}"
    '''
    
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
            if frappe.db.exists("Mitgliedschaft", str(get_value(row, 'mitglied_id'))):
                try:
                    create_notiz(row)
                except Exception as err:
                    frappe.log_error("{0}\n\n{1}".format(err, row), 'Notiz konnte nicht erstellt werden')
            else:
                frappe.log_error("{0}".format(row), 'Mitgliedschaft existiert nicht')
            print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
        else:
            break

def create_notiz(row):
    try:
        datum_erinnerung = str(get_value(row, 'datum_erinnerung'))
        if get_datetime(datum_erinnerung) > now_datetime():
            create_todo(row)
        else:
            create_comment(row)
        return
    except Exception as err:
        frappe.log_error("{0}\n\n{1}".format(err, row), 'Termin konnte nicht erstellt werden')

def create_comment(row):
    try:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", str(get_value(row, 'mitglied_id')))
        description = str(get_value(row, 'nkategorie_d')) + "<br>"
        description += str(get_value(row, 'datum_von')) + "<br>"
        description += str(get_value(row, 'notiz')) + "<br>"
        description += str(get_value(row, 'benutzer_name')) + "<br>"
        mitgliedschaft.add_comment('Comment', text=description)
        frappe.db.commit()
    except Exception as err:
        frappe.log_error("{0}\n\n{1}".format(err, row), 'Kommentar konnte nicht erstellt werden')

def create_todo(row):
    try:
        description = str(get_value(row, 'nkategorie_d')) + "<br>"
        description += str(get_value(row, 'datum_von')) + "<br>"
        description += str(get_value(row, 'notiz')) + "<br>"
        description += str(get_value(row, 'benutzer_name')) + "<br>"
        
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", str(get_value(row, 'mitglied_id')))
        owner = frappe.get_value("Sektion", mitgliedschaft.sektion_id, "virtueller_user")
        todo = frappe.get_doc({
            "doctype":"ToDo",
            "owner": owner,
            "reference_type": "Mitgliedschaft",
            "reference_name": str(get_value(row, 'mitglied_id')),
            "description": description or '',
            "priority": "Medium",
            "status": "Open",
            "date": str(get_value(row, 'datum_erinnerung')),
            "assigned_by": owner,
            "mv_mitgliedschaft": str(get_value(row, 'mitglied_id'))
        }).insert(ignore_permissions=True)
        frappe.db.commit()
        return
    except Exception as err:
        frappe.log_error("{0}\n\n{1}".format(err, row), 'ToDo konnte nicht erstellt werden')

# --------------------------------------------------------------
# Weitere Kontaktinfos Importer
# --------------------------------------------------------------
def import_weitere_kontaktinfos(site_name, file_name, limit=False):
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.import_weitere_kontaktinfos --kwargs "{'site_name': 'site1.local', 'file_name': 'weitere_kontaktinfos.csv'}"
    '''
    
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
            if frappe.db.exists("Mitgliedschaft", str(get_value(row, 'mitglied_id'))):
                try:
                    erstelle_weitere_kontaktinformation(row)
                except Exception as err:
                    frappe.log_error("{0}\n\n{1}".format(err, row), 'Weitere Kontaktinformation konnte nicht erstellt werden')
            else:
                frappe.log_error("{0}".format(row), 'Mitgliedschaft existiert nicht')
            print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
        else:
            break

def erstelle_weitere_kontaktinformation(row):
    try:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", str(get_value(row, 'mitglied_id')))
        description = str(get_value(row, 'weitere_kontaktinfos')).replace("\n", "<br>")
        mitgliedschaft.add_comment('Comment', text=description)
        frappe.db.commit()
    except Exception as err:
        frappe.log_error("{0}\n\n{1}".format(err, row), 'Kommentar konnte nicht erstellt werden')

# --------------------------------------------------------------
# Miveba Buchungen Importer
# --------------------------------------------------------------
def import_miveba_buchungen(site_name, file_name, limit=False):
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.import_miveba_buchungen --kwargs "{'site_name': 'site1.local', 'file_name': 'miveba_buchungen.csv'}"
    '''
    
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/frappe-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name))
    
    # loop through rows
    count = 1
    commit_count = 1
    max_loop = limit
    
    if not limit:
        index = df.index
        max_loop = len(index)
    
    for index, row in df.iterrows():
        if count <= max_loop:
            if frappe.db.exists("Mitgliedschaft", str(get_value(row, 'mitglied_id'))):
                try:
                    mitglied_id = str(get_value(row, 'mitglied_id'))
                    miveba_buchungen = str(get_value(row, 'buchungen'))
                    frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `miveba_buchungen` = '{miveba_buchungen}' WHERE `name` = '{mitglied_id}'""".format(miveba_buchungen=miveba_buchungen, mitglied_id=mitglied_id), as_list=True)
                    if commit_count == 1000:
                        frappe.db.commit()
                        commit_count = 1
                    else:
                        commit_count += 1
                except Exception as err:
                    frappe.log_error("{0}\n\n{1}".format(err, row), 'Miveba Buchung konnte nicht erstellt werden')
            else:
                frappe.log_error("{0}".format(row), 'Mitgliedschaft existiert nicht')
            print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
        else:
            break

# --------------------------------------------------------------
# Tags Importer
# --------------------------------------------------------------
def import_tags(site_name, file_name, limit=False):
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.import_tags --kwargs "{'site_name': 'site1.local', 'file_name': 'kategorien.csv'}"
    '''
    from frappe.desk.tags import add_tag
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
            if frappe.db.exists("Mitgliedschaft", str(get_value(row, 'mitglied_id'))):
                try:
                    add_tag(str(get_value(row, 'mkategorie_d')), "Mitgliedschaft", str(get_value(row, 'mitglied_id')))
                except Exception as err:
                    frappe.log_error("{0}\n\n{1}".format(err, row), 'Tag konnte nicht erstellt werden')
            else:
                frappe.log_error("{0}".format(row), 'Mitgliedschaft existiert nicht')
            print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
        else:
            break

# --------------------------------------------------------------
# Special Importer
# --------------------------------------------------------------
def import_special(site_name, file_name, limit=False):
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.import_special --kwargs "{'site_name': 'site1.local', 'file_name': 'jahr_bez_mitgl-PROD-1.csv'}"
    '''
    
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/frappe-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name))
    
    # loop through rows
    count = 1
    commit_count = 1
    max_loop = limit
    
    if not limit:
        index = df.index
        max_loop = len(index)
    
    for index, row in df.iterrows():
        if count <= max_loop:
            if frappe.db.exists("Mitgliedschaft", str(get_value(row, 'mitglied_id'))):
                try:
                    mitglied_id = str(get_value(row, 'mitglied_id'))
                    jahr = str(get_value(row, 'jahr_bez_mitgl'))
                    frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `zahlung_mitgliedschaft` = '{jahr}' WHERE `name` = '{mitglied_id}'""".format(jahr=jahr, mitglied_id=mitglied_id), as_list=True)
                    frappe.db.commit()
                    if int(jahr) == 2022:
                        sinvs = frappe.db.sql("""SELECT `name` FROM `tabSales Invoice` WHERE `mv_mitgliedschaft` = '{mitglied_id}' AND `status` != 'Paid' AND `docstatus` = 1""".format(mitglied_id=mitglied_id), as_dict=True)
                        for sinv in sinvs:
                            try:
                                sinv = frappe.get_doc("Sales Invoice", sinv.name)
                                sinv.cancel()
                                sinv.delete()
                                frappe.db.commit()
                            except Exception as e:
                                frappe.log_error("{0}\n\n{1}\n\n{2}".format(e, sinv.name, row), 'RG konnte nicht gelöscht werden')
                    commit_count += 1
                except Exception as err:
                    frappe.log_error("{0}\n\n{1}".format(err, row), 'Special konnte nicht erstellt werden')
            else:
                frappe.log_error("{0}".format(row), 'Mitgliedschaft existiert nicht')
            print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
        else:
            break

# --------------------------------------------------------------
# Adressen Update
# --------------------------------------------------------------
def update_adressen(site_name, file_name, limit=False):
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.update_adressen --kwargs "{'site_name': 'site1.local', 'file_name': 'hausnummer_zusatz_gefiltert.csv'}"
    '''
    from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import create_sp_queue
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/frappe-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name))
    
    # loop through rows
    count = 1
    submit_counter = 1
    max_loop = limit
    
    if not limit:
        index = df.index
        max_loop = len(index)
    
    for index, row in df.iterrows():
        if count <= max_loop:
            if frappe.db.exists("Mitgliedschaft", str(get_value(row, 'mitglied_id'))):
                try:
                    objekt_hausnummer = str(get_value(row, 'objekt_hausnummer'))
                    nummer_zu = str(get_value(row, 'nummer_zu'))
                    objekt_nummer_zu = str(get_value(row, 'objekt_nummer_zu'))
                    rg_nummer_zu = str(get_value(row, 'rg_nummer_zu'))
                    mitgliedschaft = frappe.get_doc("Mitgliedschaft", str(get_value(row, 'mitglied_id')))
                    mitgliedschaft.objekt_hausnummer = objekt_hausnummer
                    mitgliedschaft.nummer_zu = nummer_zu
                    mitgliedschaft.objekt_nummer_zu = objekt_nummer_zu
                    mitgliedschaft.rg_nummer_zu = rg_nummer_zu
                    mitgliedschaft.letzte_bearbeitung_von = 'SP'
                    mitgliedschaft.save()
                    create_sp_queue(mitgliedschaft, True)
                    if submit_counter == 100:
                        frappe.db.commit()
                        submit_counter = 1
                except Exception as err:
                    frappe.log_error("{0}\n\n{1}".format(err, row), 'Adressen Update konnte nicht durchgeführt werden')
            else:
                frappe.log_error("{0}".format(row), 'Mitgliedschaft existiert nicht')
            print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
            submit_counter += 1
        else:
            break

# --------------------------------------------------------------
# Ampel Reset
# --------------------------------------------------------------
def ampel_reset():
    '''
        Example:
        sudo bench --site [site_name] execute mvd.mvd.data_import.importer.ampel_reset
    '''
    from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_ampelfarbe
    
    # neuberechnung aller roten ampeln
    mitgliedschaften = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `ampel_farbe` = 'ampelrot'""", as_dict=True)
    total = len(mitgliedschaften)
    print("Setze/Berechne Ampel bei {0} Mitgliedschaften".format(total))
    submit_counter = 1
    count = 1
    for mitgliedschaft in mitgliedschaften:
        m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
        neue_farbe = get_ampelfarbe(m)
        if neue_farbe != m.ampel_farbe:
            set_neue_farbe = frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `ampel_farbe` = '{neue_farbe}' WHERE `name` = '{name}'""".format(neue_farbe=neue_farbe, name=m.name), as_list=True)
            submit_counter += 1
        if submit_counter == 100:
            frappe.db.commit()
            submit_counter = 1
        print("{0} von {1}".format(count, total))
        count += 1
    frappe.db.commit()

# --------------------------------------------------------------
# Setze CB "Aktive Mitgliedschaft"
# --------------------------------------------------------------
def aktive_mitgliedschaft():
    '''
        Example:
        sudo bench --site [site_name] execute mvd.mvd.data_import.importer.aktive_mitgliedschaft
    '''
    
    print("Aktiviere aktive Mitgliedschaften...")
    SQL_SAFE_UPDATES_false = frappe.db.sql("""SET SQL_SAFE_UPDATES=0""", as_list=True)
    update_cb = frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `aktive_mitgliedschaft` = 1 WHERE `status_c` NOT IN ('Gestorben', 'Wegzug', 'Ausschluss', 'Inaktiv')""", as_list=True)
    SQL_SAFE_UPDATES_true = frappe.db.sql("""SET SQL_SAFE_UPDATES=1""", as_list=True)
    frappe.db.commit()
    print("Aktive Mitgliedschaften aktiviert")

# --------------------------------------------------------------
# Tausche CB "Geschenkunterlagen an Schenker"
# --------------------------------------------------------------
def change_geschenk_cb():
    '''
        Example:
        sudo bench --site [site_name] execute mvd.mvd.data_import.importer.change_geschenk_cb
    '''
    
    mitgliedschaften = frappe.db.sql("""SELECT `name`, `geschenkunterlagen_an_schenker` FROM `tabMitgliedschaft` WHERE `ist_geschenkmitgliedschaft` = 1""", as_dict=True)
    print("Change {0} Mitgliedschaften".format(len(mitgliedschaften)))
    count = 1
    for m in mitgliedschaften:
        if int(m.geschenkunterlagen_an_schenker) == 1:
            frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `geschenkunterlagen_an_schenker` = 0 WHERE `name` = '{mitgliedschaft}'""".format(mitgliedschaft=m.name), as_list=True)
        else:
            frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `geschenkunterlagen_an_schenker` = 1 WHERE `name` = '{mitgliedschaft}'""".format(mitgliedschaft=m.name), as_list=True)
        print("{0} von {1}".format(count, len(mitgliedschaften)))
        count += 1
    frappe.db.commit()
    
# --------------------------------------------------------------
# Beitritt Update
# --------------------------------------------------------------
def update_beitritt(site_name, file_name, limit=False):
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.update_beitritt --kwargs "{'site_name': 'site1.local', 'file_name': 'mitglieder_ids_2022.csv'}"
    '''
    from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import create_sp_queue
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/frappe-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name))
    
    # loop through rows
    count = 1
    submit_counter = 1
    max_loop = limit
    
    if not limit:
        index = df.index
        max_loop = len(index)
    
    for index, row in df.iterrows():
        if count <= max_loop:
            if frappe.db.exists("Mitgliedschaft", str(get_value(row, 'mitglied_id'))):
                try:
                    frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `zahlung_mitgliedschaft` = '2022' WHERE `name` = '{mitglied_id}'""".format(mitglied_id=str(get_value(row, 'mitglied_id'))), as_list=True)
                    if submit_counter == 100:
                        frappe.db.commit()
                        submit_counter = 1
                    else:
                        submit_counter += 1
                except Exception as err:
                    frappe.log_error("{0}\n\n{1}".format(err, row), 'Beitritt Update konnte nicht durchgeführt werden')
            else:
                frappe.log_error("{0}".format(row), 'Mitgliedschaft existiert nicht')
            print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
            submit_counter += 1
        else:
            break

# --------------------------------------------------------------
# OnlinePayment Update
# --------------------------------------------------------------
def update_online_payment(site_name, file_name, limit=False):
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.update_online_payment --kwargs "{'site_name': 'site1.local', 'file_name': 'mitglied_nr_paymentId_vor_7_Maerz.csv'}"
    '''
    from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import create_sp_queue
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/frappe-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name))
    
    # loop through rows
    count = 1
    submit_counter = 1
    max_loop = limit
    
    if not limit:
        index = df.index
        max_loop = len(index)
    
    for index, row in df.iterrows():
        if count <= max_loop:
            if frappe.db.exists("Mitgliedschaft", str(get_value(row, 'mitglied_id'))):
                try:
                    online_haftpflicht = str(get_value(row, 'online_haftpflicht'))
                    online_gutschrift = str(get_value(row, 'online_gutschrift'))
                    online_betrag = str(get_value(row, 'online_betrag'))
                    datum_online_verbucht = str(get_value(row, 'datum_online_verbucht'))
                    datum_online_gutschrift = str(get_value(row, 'datum_online_gutschrift'))
                    online_payment_method = str(get_value(row, 'online_payment_method'))
                    online_payment_id = str(get_value(row, 'online_payment_id'))
                    
                    frappe.db.sql("""UPDATE `tabMitgliedschaft` SET
                                        `online_haftpflicht` = '{online_haftpflicht}',
                                        `online_gutschrift` = '{online_gutschrift}',
                                        `online_betrag` = '{online_betrag}',
                                        `datum_online_verbucht` = '{datum_online_verbucht}',
                                        `datum_online_gutschrift` = '{datum_online_gutschrift}',
                                        `online_payment_method` = '{online_payment_method}',
                                        `online_payment_id` = '{online_payment_id}'
                                    WHERE `name` = '{mitglied_id}'""".format(online_haftpflicht=online_haftpflicht, \
                                    online_gutschrift=online_gutschrift, \
                                    online_betrag=online_betrag, \
                                    datum_online_verbucht=datum_online_verbucht, \
                                    datum_online_gutschrift=datum_online_gutschrift, \
                                    online_payment_method=online_payment_method, \
                                    online_payment_id=online_payment_id, \
                                    mitglied_id=str(get_value(row, 'mitglied_id'))), as_list=True)
                    
                    if submit_counter == 100:
                        frappe.db.commit()
                        submit_counter = 1
                    else:
                        submit_counter += 1
                except Exception as err:
                    frappe.log_error("{0}\n\n{1}".format(err, row), 'OnlinePayment Update konnte nicht durchgeführt werden')
            else:
                frappe.log_error("{0}".format(row), 'Mitgliedschaft existiert nicht')
            print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
            submit_counter += 1
        else:
            break

# --------------------------------------------------------------
# Adressen reset (Postfach \n fix)
# --------------------------------------------------------------
def adressen_fix_postfach():
    '''
        Example:
        sudo bench --site [site_name] execute mvd.mvd.data_import.importer.adressen_fix_postfach
    '''
    
    mitgliedschaften = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `postfach` = 1""", as_dict=True)
    total = len(mitgliedschaften)
    print("Setze Adressenl bei {0} Mitgliedschaften".format(total))
    submit_counter = 0
    count = 0
    for mitgliedschaft in mitgliedschaften:
        m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
        m.save()
        submit_counter += 1
        if submit_counter == 100:
            frappe.db.commit()
            submit_counter = 1
        count += 1
        print("{0} von {1}".format(count, total))
        
    frappe.db.commit()

# --------------------------------------------------------------
# Fix: Zahlung Mitgliedschaft <> Bezahltes Mitgliedschaftsjahr
# --------------------------------------------------------------
def fix_zahlungs_jahr():
    '''
        Example:
        sudo bench --site [site_name] execute mvd.mvd.data_import.importer.fix_zahlungs_jahr
    '''
    
    mitgliedschaften = frappe.db.sql("""SELECT `name`, `zahlung_mitgliedschaft` FROM `tabMitgliedschaft` WHERE `zahlung_mitgliedschaft` > 0""", as_dict=True)
    total = len(mitgliedschaften)
    print("Fixe Zahlung Mitgliedschaft <> Bezahltes Mitgliedschaftsjahr bei {0} Mitgliedschaften".format(total))
    submit_counter = 0
    count = 0
    for mitgliedschaft in mitgliedschaften:
        frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `bezahltes_mitgliedschaftsjahr` = {zahlung_mitgliedschaft} WHERE `name` = '{name}'""".format(zahlung_mitgliedschaft=mitgliedschaft.zahlung_mitgliedschaft, name=mitgliedschaft.name), as_list=True)
        submit_counter += 1
        if submit_counter == 100:
            frappe.db.commit()
            submit_counter = 1
        count += 1
        print("{0} von {1}".format(count, total))
        
    frappe.db.commit()

# --------------------------------------------------------------
# Nachmigration für SP
# --------------------------------------------------------------
def nachmigration_fuer_sp():
    '''
        Example:
        sudo bench --site [site_name] execute mvd.mvd.data_import.importer.nachmigration_fuer_sp
    '''
    
    from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import send_mvm_to_sp
    
    mitgliedschaften = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `datum_zahlung_mitgliedschaft` BETWEEN CAST('2022-03-01' AS DATE) AND CAST('2022-05-03' AS DATE)""", as_dict=True)
    submit_counter = 1
    counter = 1
    for mitgliedschaft in mitgliedschaften: 
        m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name) 
        send_mvm_to_sp(m, True) 
        print("{0} von {1}".format(counter, len(mitgliedschaften))) 
        counter += 1
        if submit_counter == 100:
            frappe.db.commit()
            submit_counter = 1
        else:
            submit_counter += 1
    frappe.db.commit()

# --------------------------------------------------------------
# regionCode SP Update
# --------------------------------------------------------------
def update_region_code(site_name, file_name, limit=False):
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.update_region_code --kwargs "{'site_name': 'site1.local', 'file_name': 'update_region_code.csv'}"
    '''
    from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import send_mvm_to_sp
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/frappe-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name))
    
    # loop through rows
    count = 1
    submit_counter = 1
    max_loop = limit
    
    if not limit:
        index = df.index
        max_loop = len(index)
    
    for index, row in df.iterrows():
        if count <= max_loop:
            if frappe.db.exists("Mitgliedschaft", str(get_value(row, 'mitglied_id'))):
                try:
                    m = frappe.get_doc("Mitgliedschaft", str(get_value(row, 'mitglied_id'))) 
                    send_mvm_to_sp(m, True)
                    if submit_counter == 100:
                        frappe.db.commit()
                        submit_counter = 1
                    else:
                        submit_counter += 1
                except Exception as err:
                    frappe.log_error("{0}\n\n{1}".format(err, row), 'Queue konnte nicht erstellt werden')
            else:
                frappe.log_error("{0}".format(row), 'Mitgliedschaft existiert nicht')
            print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
            submit_counter += 1
        else:
            break

# --------------------------------------------------------------
# region_plz import
# --------------------------------------------------------------
def import_region_plz(site_name, file_name, limit=False):
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.import_region_plz --kwargs "{'site_name': 'site1.local', 'file_name': 'region_plz.csv'}"
    '''
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/frappe-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name))
    
    # loop through rows
    count = 1
    submit_counter = 1
    max_loop = limit
    
    if not limit:
        index = df.index
        max_loop = len(index)
    
    region = None
    error_logs = False
    for index, row in df.iterrows():
        if count <= max_loop:
            if region and region.name == str(get_value(row, 'region_d')):
                r_row = region.append('plz_zuordnung', {})
                r_row.plz_von = int(get_value(row, 'plz_von'))
                r_row.plz_bis = int(get_value(row, 'plz_bis'))
                region.save()
                print("Add range {0}..{1} to {2}".format(get_value(row, 'plz_von'), get_value(row, 'plz_bis'), str(get_value(row, 'region_d'))))
            else:
                if frappe.db.exists("Region", str(get_value(row, 'region_d'))):
                    try:
                        region = frappe.get_doc("Region", str(get_value(row, 'region_d'))) 
                        r_row = region.append('plz_zuordnung', {})
                        r_row.plz_von = int(get_value(row, 'plz_von'))
                        r_row.plz_bis = int(get_value(row, 'plz_bis'))
                        region.save()
                        print("Add range {0}..{1} to {2}".format(get_value(row, 'plz_von'), get_value(row, 'plz_bis'), str(get_value(row, 'region_d'))))
                    except Exception as err:
                        frappe.log_error("FAILED: Add range {0}..{1} to {2}".format(get_value(row, 'plz_von'), get_value(row, 'plz_bis'), str(get_value(row, 'region_d'))), 'Region / PLZ')
                        print("FAILED: Add range {0}..{1} to {2}".format(get_value(row, 'plz_von'), get_value(row, 'plz_bis'), str(get_value(row, 'region_d'))))
                        error_logs = True
                else:
                    frappe.log_error("FAILED: Add range {0}..{1} to {2}".format(get_value(row, 'plz_von'), get_value(row, 'plz_bis'), str(get_value(row, 'region_d'))), 'Region / PLZ')
                    print("FAILED: Add range {0}..{1} to {2}".format(get_value(row, 'plz_von'), get_value(row, 'plz_bis'), str(get_value(row, 'region_d'))))
                    error_logs = True
            if submit_counter == 100:
                frappe.db.commit()
                submit_counter = 1
            else:
                submit_counter += 1
        else:
            break
    if error_logs:
        print("Errors detected, see error log")
    print("Done")
    
# --------------------------------------------------------------
# Entfernung fehlerhaften Eintrittsdatum
# --------------------------------------------------------------
def entfernung_fehlerhaften_eintrittsdatum():
    '''
        Example:
        sudo bench --site [site_name] execute mvd.mvd.data_import.importer.entfernung_fehlerhaften_eintrittsdatum
    '''
    
    
    mitgliedschaften = frappe.db.sql("""SELECT DISTINCT
                                            `name`
                                        FROM `tabMitgliedschaft`
                                        WHERE `eintrittsdatum` IS NOT NULL
                                        AND `status_c` IN ('Anmeldung', 'Online-Anmeldung', 'Interessent*in')""", as_dict=True)
    submit_counter = 1
    counter = 1
    for mitgliedschaft in mitgliedschaften: 
        m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name) 
        m.eintrittsdatum = ''
        m.bezahltes_mitgliedschaftsjahr = 0
        m.save()
        
        print("{0} von {1}".format(counter, len(mitgliedschaften))) 
        counter += 1
        if submit_counter == 100:
            frappe.db.commit()
            submit_counter = 1
        else:
            submit_counter += 1
    frappe.db.commit()

# --------------------------------------------------------------
# Nachsendung Auschluss ohne Eintrittsdatum an SP
# --------------------------------------------------------------
def nachsendung_auschluss_ohne_eintrittsdatum_an_sp():
    '''
        Example:
        sudo bench --site [site_name] execute mvd.mvd.data_import.importer.nachsendung_auschluss_ohne_eintrittsdatum_an_sp
    '''
    
    from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import send_mvm_to_sp
    
    mitgliedschaften = frappe.db.sql("""SELECT DISTINCT
                                            `name`
                                        FROM `tabMitgliedschaft`
                                        WHERE `status_c` = 'Inaktiv'
                                        AND `eintrittsdatum` IS NULL""", as_dict=True)
    submit_counter = 1
    counter = 1
    for mitgliedschaft in mitgliedschaften: 
        m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name) 
        send_mvm_to_sp(m, True) 
        print("{0} von {1}".format(counter, len(mitgliedschaften))) 
        counter += 1
        if submit_counter == 100:
            frappe.db.commit()
            submit_counter = 1
        else:
            submit_counter += 1
    frappe.db.commit()

# --------------------------------------------------------------
# import Retouren
# --------------------------------------------------------------
def import_retouren(site_name, file_name, limit=False):
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.import_retouren --kwargs "{'site_name': 'site1.local', 'file_name': 'retouren.csv'}"
    '''
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    
    # read csv
    df = pd.read_csv('/home/frappe/frappe-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name))
    
    # loop through rows
    count = 1
    submit_counter = 1
    max_loop = limit
    
    if not limit:
        index = df.index
        max_loop = len(index)
    
    for index, row in df.iterrows():
        if count <= max_loop:
            try:
                post_retoure = frappe.get_doc({
                    'doctype': 'Retouren',
                    'status': get_value(row, 'status'),
                    'mv_mitgliedschaft': get_value(row, 'mv_mitgliedschaft'),
                    'sektion_id': get_value(row, 'sektion_id'),
                    'ausgabe': get_value(row, 'ausgabe'),
                    'legacy_kategorie_code': get_value(row, 'legacy_kategorie_code'),
                    'legacy_notiz': get_value(row, 'legacy_notiz'),
                    'grund_code': get_value(row, 'grund_code'),
                    'grund_bezeichnung': get_value(row, 'grund_bezeichnung'),
                    'retoure_mw_sequence_number': get_value(row, 'retoure_mw_sequence_number'),
                    'retoure_dmc': get_value(row, 'retoure_dmc'),
                    'retoure_sendungsbild': get_value(row, 'retoure_sendungsbild'),
                    'datum_erfasst_post': str(get_value(row, 'datum_erfasst_post'))
                })
                
                post_retoure.insert(ignore_permissions=True)
                if submit_counter == 100:
                    frappe.db.commit()
                    submit_counter = 1
                else:
                    submit_counter += 1
            
            except Exception as err:
                frappe.log_error("{0}\n\n{1}\n\n{2}".format(err, row, frappe.utils.get_traceback()), 'post_retoure konnte nicht erstellt werden')
            print("{count} of {max_loop} --> {percent}".format(count=count, max_loop=max_loop, percent=((100 / max_loop) * count)))
            count += 1
        else:
            break
    frappe.db.commit()

# --------------------------------------------------------------
# update mitgliedschaften anhand import Retouren
# --------------------------------------------------------------
def update_mitgliedschaften_anhand_import_retouren():
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.update_mitgliedschaften_anhand_import_retouren
    '''
    
    counter = 1
    update_offen = frappe.db.sql("""SELECT 
                                    `mv_mitgliedschaft`,
                                    COUNT(`name`) AS `qty`
                                    FROM `tabRetouren`
                                    WHERE `status` IN ('Offen', 'In Bearbeitung')
                                    GROUP BY `mv_mitgliedschaft`""", as_dict=True)
    for u_o in update_offen:
        update = frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `m_w_anzahl` = {qty} WHERE `name` = '{mitgliedschaft}'""".format(qty=u_o.qty, mitgliedschaft=u_o.mv_mitgliedschaft), as_list=True)
        print("Update {0} of {1}".format(counter, len(update_offen)))
        counter += 1
    
    frappe.db.commit()

# --------------------------------------------------------------
# update mitgliedschaften: korrektur Kündigung/Regulär/Inaktiv
# --------------------------------------------------------------
def update_mitgliedschaften_korr_k_r_i():
    '''
        Example:
        sudo bench execute mvd.mvd.data_import.importer.update_mitgliedschaften_korr_k_r_i
    '''
    
    s_c = 1
    counter = 1
    inaktive_ms = frappe.db.sql("""SELECT 
                                    `name`
                                    FROM `tabMitgliedschaft`
                                    WHERE `status_c` = 'Kündigung'
                                    AND `kuendigung` <= CURDATE()""", as_dict=True)
    for i_ms in inaktive_ms:
        try:
            m = frappe.get_doc("Mitgliedschaft", i_ms.name)
            m.status_c = 'Inaktiv'
            change_log_row = m.append('status_change', {})
            change_log_row.datum = now()
            change_log_row.status_alt = 'Kündigung'
            change_log_row.status_neu = 'Inaktiv'
            change_log_row.grund = 'Autom. Bereinigung'
            m.letzte_bearbeitung_von = 'User'
            m.save()
        except Exception as err:
            frappe.log_error("{0}\n\n{1}\n\n{2}".format(err, frappe.utils.get_traceback(), i_ms.name), 'update_mitgliedschaften_korr_k_r_i')
            
        print("Update {0} of {1}".format(counter, len(inaktive_ms)))
        counter += 1
        s_c += 1
        if s_c == 100:
            frappe.db.commit()
            s_c = 1
    
    s_c = 1
    counter = 1
    regul_ms = frappe.db.sql("""SELECT 
                                    `name`
                                    FROM `tabMitgliedschaft`
                                    WHERE `status_c` = 'Kündigung'
                                    AND `kuendigung` > CURDATE()""", as_dict=True)
    for i_ms in regul_ms:
        try:
            m = frappe.get_doc("Mitgliedschaft", i_ms.name)
            m.status_c = 'Regulär'
            change_log_row = m.append('status_change', {})
            change_log_row.datum = now()
            change_log_row.status_alt = 'Kündigung'
            change_log_row.status_neu = 'Regulär &dagger;'
            change_log_row.grund = 'Autom. Bereinigung'
            m.letzte_bearbeitung_von = 'User'
            m.save()
        except Exception as err:
            frappe.log_error("{0}\n\n{1}\n\n{2}".format(err, frappe.utils.get_traceback(), i_ms.name), 'update_mitgliedschaften_korr_k_r_i')
        
        print("Update {0} of {1}".format(counter, len(regul_ms)))
        counter += 1
        s_c += 1
        if s_c == 100:
            frappe.db.commit()
            s_c = 1
    
    frappe.db.commit()
