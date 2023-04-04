# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import add_days, getdate, now
import six
import json
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import create_mitgliedschaftsrechnung
from mvd.mvd.doctype.arbeits_backlog.arbeits_backlog import create_abl

@frappe.whitelist()
def suche(suchparameter, goto_list=False):
    if isinstance(suchparameter, six.string_types):
        suchparameter = json.loads(suchparameter)
    
    filters_list = []
    
    # allgemein
    if suchparameter["sektion_id"]:
        filters_list.append("""`sektion_id` = '{sektion_id}'""".format(sektion_id=suchparameter["sektion_id"]))
    if suchparameter["language"]:
        filters_list.append("""`language` = '{language}'""".format(language=suchparameter["language"]))
    if suchparameter["mitglied_nr"]:
        mitglied_nr_bereinigt = suchparameter["mitglied_nr"]
        if 'MV' not in suchparameter["mitglied_nr"]:
            mitglied_nr_bereinigt = "MV" + suchparameter["mitglied_nr"]
        filters_list.append("""`mitglied_nr` LIKE '{mitglied_nr}%'""".format(mitglied_nr=mitglied_nr_bereinigt))
    if suchparameter["status_c"] and suchparameter["sektion_id"]:
        if suchparameter["status_c"] != 'Alle':
            if 'Regulär' in suchparameter["status_c"]:
                filters_list.append("""`status_c` IN ('Regulär', 'Online-Mutation')""")
            else:
                filters_list.append("""`status_c` = '{status_c}'""".format(status_c=suchparameter["status_c"]))
        else:
            if not suchparameter["inaktive"]:
                filters_list.append("""(`aktive_mitgliedschaft` = 1 OR `status_c` = 'Gestorben')""")
    if suchparameter["mitgliedtyp_c"] and suchparameter["sektion_id"]:
        if suchparameter["mitgliedtyp_c"] != 'Alle':
            filters_list.append("""`mitgliedtyp_c` = '{mitgliedtyp_c}'""".format(mitgliedtyp_c=suchparameter["mitgliedtyp_c"]))
    
    # Kontaktdaten
    if suchparameter["vorname"]:
        filters_list.append("""(`vorname_1` LIKE "{vorname}%" OR `rg_vorname` LIKE "{vorname}%" OR `vorname_2` LIKE "{vorname}%")""".format(vorname=suchparameter["vorname"]))
    if suchparameter["nachname"]:
        filters_list.append("""(`nachname_1` LIKE "{nachname}%" OR `rg_nachname` LIKE "{nachname}%" OR `nachname_2` LIKE "{nachname}%")""".format(nachname=suchparameter["nachname"]))
    if suchparameter["tel"]:
        filters_list.append("""
                            ((REPLACE(`tel_p_1`, ' ', '') LIKE '{tel}%' OR REPLACE(`rg_tel_p`, ' ', '') LIKE '{tel}%' OR REPLACE(`tel_p_2`, ' ', '') LIKE '{tel}%')
                            OR
                            (REPLACE(`tel_m_1`, ' ', '') LIKE '{tel}%' OR REPLACE(`rg_tel_m`, ' ', '') LIKE '{tel}%' OR REPLACE(`tel_m_2`, ' ', '') LIKE '{tel}%')
                            OR
                            (REPLACE(`tel_g_1`, ' ', '') LIKE '{tel}%' OR REPLACE(`rg_tel_g`, ' ', '') LIKE '{tel}%' OR REPLACE(`tel_g_2`, ' ', '') LIKE '{tel}%'))""".format(tel=suchparameter["tel"].replace(" ", "")))
    if suchparameter["email"]:
        filters_list.append("""(`e_mail_1` LIKE '{email}%' OR `rg_e_mail` LIKE '{email}%' OR `e_mail_2` LIKE '{email}%')""".format(email=suchparameter["email"]))
    if 'firma' in suchparameter:
        if 'zusatz_firma' in suchparameter:
            if suchparameter["firma"]:
                if suchparameter["zusatz_firma"]:
                    firma = str(suchparameter["firma"] + "%" + suchparameter["zusatz_firma"]).replace(" ", "")
                    filters_list.append("""(REPLACE(CONCAT(IFNULL(`firma`, ''), IFNULL(`zusatz_firma`, '')), ' ', '') LIKE "{firma}%"
                                            OR
                                            REPLACE(CONCAT(IFNULL(`rg_firma`, ''), IFNULL(`rg_zusatz_firma`, '')), ' ', '') LIKE "{firma}%")""".format(firma=firma))
                else:
                    filters_list.append("""(REPLACE(CONCAT(IFNULL(`firma`, ''), IFNULL(`zusatz_firma`, '')), ' ', '') LIKE "{firma}%"
                                            OR
                                            REPLACE(CONCAT(IFNULL(`rg_firma`, ''), IFNULL(`rg_zusatz_firma`, '')), ' ', '') LIKE "{firma}%")""".format(firma=str(suchparameter["firma"]).replace(" ", "")))
            else:
                if suchparameter["zusatz_firma"]:
                    filters_list.append("""(REPLACE(CONCAT(IFNULL(`firma`, ''), IFNULL(`zusatz_firma`, '')), ' ', '') LIKE "{zusatz_firma}%"
                                            OR
                                            REPLACE(CONCAT(IFNULL(`rg_firma`, ''), IFNULL(`rg_zusatz_firma`, '')), ' ', '') LIKE "{zusatz_firma}%")""".format(zusatz_firma=str(suchparameter["zusatz_firma"]).replace(" ", "")))
        else:
            if suchparameter["firma"]:
                filters_list.append("""(REPLACE(CONCAT(IFNULL(`firma`, ''), IFNULL(`zusatz_firma`, '')), ' ', '') LIKE "{firma}%"
                                        OR
                                        REPLACE(CONCAT(IFNULL(`rg_firma`, ''), IFNULL(`rg_zusatz_firma`, '')), ' ', '') LIKE "{firma}%")""".format(firma=str(suchparameter["firma"]).replace(" ", "")))
    
    # Adressdaten
    if suchparameter["zusatz_adresse"]:
        filters_list.append("""(`zusatz_adresse` LIKE '{zusatz_adresse}%' OR `rg_zusatz_adresse` LIKE '{zusatz_adresse}%' OR `objekt_zusatz_adresse` LIKE '{zusatz_adresse}%')""".format(zusatz_adresse=suchparameter["zusatz_adresse"]))
    
    strassensuchwert = ''
    if suchparameter["strasse"]:
        strassensuchwert += suchparameter["strasse"] + "%"
    if suchparameter["nummer"]:
        strassensuchwert += suchparameter["nummer"] + "%"
    if suchparameter["nummer_zu"]:
        strassensuchwert += suchparameter["nummer_zu"] + "%"
    if strassensuchwert:
        filters_list.append("""(REPLACE(CONCAT(IFNULL(`strasse`, ''), IFNULL(`nummer`, ''), IFNULL(`nummer_zu`, '')), ' ', '') LIKE '{strassensuchwert}'
                                OR
                                REPLACE(CONCAT(IFNULL(`rg_strasse`, ''), IFNULL(`rg_nummer`, ''), IFNULL(`rg_nummer_zu`, '')), ' ', '') LIKE '{strassensuchwert}'
                                OR
                                REPLACE(CONCAT(IFNULL(`objekt_strasse`, ''), IFNULL(`objekt_hausnummer`, ''), IFNULL(`objekt_nummer_zu`, '')), ' ', '') LIKE '{strassensuchwert}')""".format(strassensuchwert=strassensuchwert.replace(" ", "")))
    
    if suchparameter["postfach_nummer"]:
        filters_list.append("""(`postfach_nummer` LIKE '{postfach_nummer}%' OR `rg_postfach_nummer` LIKE '{postfach_nummer}%')""".format(postfach_nummer=suchparameter["postfach_nummer"]))
    if suchparameter["postfach"]:
        filters_list.append("""(`postfach` = 1 OR `rg_postfach` = 1)""")
    if suchparameter["plz"]:
        filters_list.append("""(`plz` LIKE '{plz}%' OR `rg_plz` LIKE '{plz}%' OR `objekt_plz` LIKE '{plz}%')""".format(plz=suchparameter["plz"]))
    if suchparameter["ort"]:
        filters_list.append("""(`ort` LIKE '{ort}%' OR `rg_ort` LIKE '{ort}%' OR `objekt_ort` LIKE '{ort}%')""".format(ort=suchparameter["ort"]))
    
    if len(filters_list) > 0:
        filters = (" AND ").join(filters_list)
        filters = 'WHERE ' + filters
    else:
        filters = ''
    
    if goto_list:
        search_hash = frappe.generate_hash(length=10)
        mitgliedschaften = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` {filters}""".format(filters=filters), as_list=True)
        if len(mitgliedschaften) > 1:
            mitgliedschaften = [item for sublist in mitgliedschaften for item in sublist]
            mitgliedschaften = tuple(mitgliedschaften)
            set_search_hash = frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `search_hash` = '{search_hash}' WHERE `name` IN {mitgliedschaften}""".format(search_hash=search_hash, mitgliedschaften=mitgliedschaften), as_list=True)
            return search_hash
        else:
            return False
    else:
        if suchparameter["sektions_uebergreifend"] and not suchparameter["alle_sektionen"]:
            mitgliedschaften = frappe.db.sql("""SELECT * FROM `tabMitgliedschaft` {filters}
                                                ORDER BY CASE WHEN `status_c` NOT IN ('Inaktiv', 'Wegzug') THEN 1
                                                ELSE 2 END
                                                LIMIT 1""".format(filters=filters), as_dict=True)
        else:
            sortierung = """CASE
                                WHEN `status_c` = 'Regulär' THEN 1
                                WHEN `status_c` = 'Kündigung' THEN 2
                                WHEN `status_c` = 'Online-Beitritt' THEN 3
                                WHEN `status_c` = 'Zuzug' THEN 4
                                WHEN `status_c` = 'Online-Anmeldung' THEN 5
                                WHEN `status_c` = 'Anmeldung' THEN 6
                                WHEN `status_c` = 'Interessent*in' THEN 7
                                WHEN `status_c` = 'Gestorben' THEN 8
                                WHEN `status_c` = 'Wegzug' THEN 9
                                WHEN `status_c` = 'Ausschluss' THEN 10
                                WHEN `status_c` = 'Inaktiv' THEN 11
                            ELSE 12 END"""
            if suchparameter["sortierung"]:
                if suchparameter["sortierung"] != 'Status':
                    if suchparameter["sortierung"] == 'Mitglied':
                        sortierung = """`mitglied_nr` ASC"""
                    elif suchparameter["sortierung"] == 'Firma':
                        sortierung = """`firma` ASC"""
                    elif suchparameter["sortierung"] == 'Nachname':
                        sortierung = """`nachname_1` ASC"""
                    elif suchparameter["sortierung"] == 'Vorname':
                        sortierung = """`vorname_1` ASC"""
                    elif suchparameter["sortierung"] == 'Strasse':
                        sortierung = """`strasse` ASC"""
                    elif suchparameter["sortierung"] == 'Nr':
                        sortierung = """`nummer` ASC"""
                    elif suchparameter["sortierung"] == 'Wohnort':
                        sortierung = """`plz` ASC"""
                    elif suchparameter["sortierung"] == 'P':
                        sortierung = """`tel_p_1` ASC"""
                    elif suchparameter["sortierung"] == 'M':
                        sortierung = """`tel_m_1` ASC"""
                    elif suchparameter["sortierung"] == 'G':
                        sortierung = """`tel_g_1` ASC"""
                    elif suchparameter["sortierung"] == 'Mitgliedtyp':
                        sortierung = """`mitgliedtyp_c` ASC"""
            
            mitgliedschaften = frappe.db.sql("""SELECT * FROM `tabMitgliedschaft` {filters} ORDER BY {sortierung}""".format(filters=filters, sortierung=sortierung), as_dict=True)
        
        if len(mitgliedschaften) > 0:
            if not suchparameter["sektions_uebergreifend"]:
                resultate_html = get_resultate_html(mitgliedschaften)
                return resultate_html
            else:
                if len(mitgliedschaften) > 1:
                    return 'too many'
                else:
                    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaften[0].name).as_dict()
                    data = {
                        'mitgliedschaft': mitgliedschaft,
                    }
                    return frappe.render_template('templates/includes/mvd_freizuegigkeitsabfrage.html', data)
        else:
            return False

def get_resultate_html(mitgliedschaften):
    meine_sektionen = []
    from frappe.defaults import get_user_permissions
    restriktionen = frappe.defaults.get_user_permissions(str(frappe.session.user))
    if "Sektion" in restriktionen:
        for sektion in restriktionen["Sektion"]:
            meine_sektionen.append(sektion.doc)
    
    data = {
        'mitgliedschaften': mitgliedschaften,
        'meine_sektionen': meine_sektionen if len(meine_sektionen) > 0 else False
    }
    
    return frappe.render_template('templates/includes/mvd_suchresultate.html', data)

@frappe.whitelist()
def anlage_prozess(anlage_daten, druckvorlage=False, massendruck=False):
    if isinstance(anlage_daten, six.string_types):
        anlage_daten = json.loads(anlage_daten)
    
    firma = ''
    if 'firma' in anlage_daten:
        firma = anlage_daten["firma"] if anlage_daten["firma"] else ''
    zusatz_firma = ''
    if 'zusatz_firma' in anlage_daten:
        zusatz_firma = anlage_daten["zusatz_firma"] if anlage_daten["zusatz_firma"] else ''
    
    eintritt = None
    if anlage_daten["status"] == 'Regulär':
        eintritt = now()
    
    if anlage_daten["sektion_id"] == "M+W-Abo":
        anlage_daten_status = 'Regulär'
    else:
        anlage_daten_status = anlage_daten["status"]
    
    # erstelle mitgliedschaft
    mitgliedschaft = frappe.get_doc({
        "doctype": "Mitgliedschaft",
        "sektion_id": anlage_daten["sektion_id"],
        "status_c": anlage_daten_status,
        "language": anlage_daten["language"],
        "m_und_w": 1,
        "mitgliedtyp_c": anlage_daten["mitgliedtyp"],
        "inkl_hv": 1,
        "eintrittsdatum": eintritt,
        "kundentyp": anlage_daten["kundentyp"],
        "firma": firma,
        "zusatz_firma": zusatz_firma,
        "anrede_c": anlage_daten["anrede"] if 'anrede' in anlage_daten else '',
        "nachname_1": anlage_daten["nachname"],
        "vorname_1": anlage_daten["vorname"],
        "tel_p_1": anlage_daten["telefon"] if 'telefon' in anlage_daten else '',
        "tel_m_1": anlage_daten["telefon_m"] if 'telefon_m' in anlage_daten else '',
        "tel_g_1": anlage_daten["telefon_g"] if 'telefon_g' in anlage_daten else '',
        "e_mail_1": anlage_daten["email"] if 'email' in anlage_daten else '',
        "zusatz_adresse": anlage_daten["zusatz_adresse"] if 'zusatz_adresse' in anlage_daten else '',
        "strasse": anlage_daten["strasse"] if 'strasse' in anlage_daten else '',
        "nummer": anlage_daten["nummer"] if 'nummer' in anlage_daten else '',
        "nummer_zu": anlage_daten["nummer_zu"] if 'nummer_zu' in anlage_daten else '',
        "postfach": anlage_daten["postfach"],
        "postfach_nummer": anlage_daten["postfach_nummer"] if 'postfach_nummer' in anlage_daten else '',
        "plz": anlage_daten["plz"],
        "ort": anlage_daten["ort"],
        "objekt_strasse": anlage_daten["strasse"] if int(anlage_daten["postfach"]) == 1 else '',
        "objekt_plz": anlage_daten["plz"] if int(anlage_daten["postfach"]) == 1 else '',
        "objekt_ort": anlage_daten["ort"] if int(anlage_daten["postfach"]) == 1 else '',
        "abweichende_objektadresse": 1 if int(anlage_daten["postfach"]) == 1 else '0'
    })
    mitgliedschaft.insert(ignore_permissions=True)
    
    # optional: erstelle Rechnung
    if anlage_daten["status"] == 'Regulär':
        bezahlt = True
        hv_bar_bezahlt = False
        if int(anlage_daten["hv_bar_bezahlt"]) == 1:
            hv_bar_bezahlt = True
        if int(massendruck) == 1:
            massendruck = True
        sinv = create_mitgliedschaftsrechnung(mitgliedschaft=mitgliedschaft.name, bezahlt=bezahlt, submit=True, attach_as_pdf=True, hv_bar_bezahlt=hv_bar_bezahlt, druckvorlage=druckvorlage, massendruck=massendruck)
    else:
        if int(anlage_daten["autom_rechnung"]) == 1:
            bezahlt = False
            hv_bar_bezahlt = False
            if int(massendruck) == 1:
                massendruck = True
            else:
                massendruck = False
            sinv = create_mitgliedschaftsrechnung(mitgliedschaft=mitgliedschaft.name, bezahlt=bezahlt, submit=True, attach_as_pdf=True, hv_bar_bezahlt=hv_bar_bezahlt, druckvorlage=druckvorlage, massendruck=massendruck)
        else:
            if anlage_daten["status"] == 'Interessent*in':
                # erstelle ABL für Interessent*Innenbrief mit EZ
                create_abl("Interessent*Innenbrief mit EZ", mitgliedschaft)
                mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
                mitgliedschaft.interessent_innenbrief_mit_ez = 1
                mitgliedschaft.save()
            if anlage_daten["status"] == 'Anmeldung' and anlage_daten["sektion_id"] != "M+W-Abo":
                # erstelle ABL für Anmeldung mit EZ
                create_abl("Anmeldung mit EZ", mitgliedschaft)
                mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
                mitgliedschaft.anmeldung_mit_ez = 1
                mitgliedschaft.save()
    
    return mitgliedschaft.name
