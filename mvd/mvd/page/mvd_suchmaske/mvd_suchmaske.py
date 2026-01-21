# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import add_days, getdate, now, today
from frappe.utils import cint
import six
import json
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import create_mitgliedschaftsrechnung
from mvd.mvd.doctype.arbeits_backlog.arbeits_backlog import create_abl

@frappe.whitelist()
def suche(suchparameter, goto_list=False):
    if isinstance(suchparameter, six.string_types):
        suchparameter = json.loads(suchparameter)
    
    filters_list = []
    faktura_filters_list = []
    
    # allgemein
    if suchparameter["sektion_id"]:
        query_string = """`sektion_id` = '{sektion_id}'""".format(sektion_id=suchparameter["sektion_id"])
        filters_list.append(query_string)
        faktura_filters_list.append(query_string)
    if suchparameter["language"]:
        query_string = """`language` = '{language}'""".format(language=suchparameter["language"])
        filters_list.append(query_string)
        faktura_filters_list.append(query_string)
    if suchparameter["mitglied_nr"]:
        mitglied_nr_bereinigt = suchparameter["mitglied_nr"]
        if 'MV' not in suchparameter["mitglied_nr"]:
            mitglied_nr_bereinigt = "MV" + suchparameter["mitglied_nr"]
        query_string = """`mitglied_nr` LIKE '{mitglied_nr}%'""".format(mitglied_nr=mitglied_nr_bereinigt)
        filters_list.append(query_string)
        faktura_filters_list.append(query_string)
    if suchparameter["status_c"] and suchparameter["sektion_id"]:
        # Dieser Filter ist für Faktura Kunden nicht anwendbar
        if suchparameter["status_c"] != 'Alle':
            if 'Regulär' in suchparameter["status_c"]:
                filters_list.append("""`status_c` IN ('Regulär', 'Online-Mutation')""")
            else:
                filters_list.append("""`status_c` = '{status_c}'""".format(status_c=suchparameter["status_c"]))
        else:
            if not suchparameter["inaktive"]:
                filters_list.append("""(`aktive_mitgliedschaft` = 1 OR `status_c` = 'Gestorben')""")
    if suchparameter["mitgliedtyp_c"] and suchparameter["sektion_id"]:
        # Dieser Filter ist für Faktura Kunden nicht anwendbar
        if suchparameter["mitgliedtyp_c"] != 'Alle':
            filters_list.append("""`mitgliedtyp_c` = '{mitgliedtyp_c}'""".format(mitgliedtyp_c=suchparameter["mitgliedtyp_c"]))
    
    # Kontaktdaten
    if suchparameter["vorname"]:
        filters_list.append("""(`vorname_1` LIKE "{vorname}%" OR `rg_vorname` LIKE "{vorname}%" OR `vorname_2` LIKE "{vorname}%")""".format(vorname=suchparameter["vorname"]))
        faktura_filters_list.append("""(`vorname` LIKE "{vorname}%" OR `rg_vorname` LIKE "{vorname}%")""".format(vorname=suchparameter["vorname"]))
    if suchparameter["nachname"]:
        filters_list.append("""(`nachname_1` LIKE "{nachname}%" OR `rg_nachname` LIKE "{nachname}%" OR `nachname_2` LIKE "{nachname}%")""".format(nachname=suchparameter["nachname"]))
        faktura_filters_list.append("""(`nachname` LIKE "{nachname}%" OR `rg_nachname` LIKE "{nachname}%")""".format(nachname=suchparameter["nachname"]))
    if suchparameter["tel"]:
        filters_list.append("""
                            ((REPLACE(`tel_p_1`, ' ', '') LIKE '{tel}%' OR REPLACE(`rg_tel_p`, ' ', '') LIKE '{tel}%' OR REPLACE(`tel_p_2`, ' ', '') LIKE '{tel}%')
                            OR
                            (REPLACE(`tel_m_1`, ' ', '') LIKE '{tel}%' OR REPLACE(`rg_tel_m`, ' ', '') LIKE '{tel}%' OR REPLACE(`tel_m_2`, ' ', '') LIKE '{tel}%')
                            OR
                            (REPLACE(`tel_g_1`, ' ', '') LIKE '{tel}%' OR REPLACE(`rg_tel_g`, ' ', '') LIKE '{tel}%' OR REPLACE(`tel_g_2`, ' ', '') LIKE '{tel}%'))""".format(tel=suchparameter["tel"].replace(" ", "")))
        faktura_filters_list.append("""
                            ((REPLACE(`tel_p`, ' ', '') LIKE '{tel}%' OR REPLACE(`rg_tel_p`, ' ', '') LIKE '{tel}%')
                            OR
                            (REPLACE(`tel_m`, ' ', '') LIKE '{tel}%' OR REPLACE(`rg_tel_m`, ' ', '') LIKE '{tel}%')
                            OR
                            (REPLACE(`tel_g`, ' ', '') LIKE '{tel}%' OR REPLACE(`rg_tel_g`, ' ', '') LIKE '{tel}%'))""".format(tel=suchparameter["tel"].replace(" ", "")))
    if suchparameter["email"]:
        filters_list.append("""(`e_mail_1` LIKE '{email}%' OR `rg_e_mail` LIKE '{email}%' OR `e_mail_2` LIKE '{email}%')""".format(email=suchparameter["email"]))
        faktura_filters_list.append("""(`e_mail` LIKE '{email}%' OR `rg_e_mail` LIKE '{email}%')""".format(email=suchparameter["email"]))
    if 'firma' in suchparameter:
        if 'zusatz_firma' in suchparameter:
            if suchparameter["firma"]:
                if suchparameter["zusatz_firma"]:
                    firma = str(suchparameter["firma"] + "%" + suchparameter["zusatz_firma"]).replace(" ", "")
                    query_string = """(REPLACE(CONCAT(IFNULL(`firma`, ''), IFNULL(`zusatz_firma`, '')), ' ', '') LIKE "{firma}%"
                                            OR
                                            REPLACE(CONCAT(IFNULL(`rg_firma`, ''), IFNULL(`rg_zusatz_firma`, '')), ' ', '') LIKE "{firma}%")""".format(firma=firma)
                    filters_list.append(query_string)
                    faktura_filters_list.append(query_string)
                else:
                    query_string = """(REPLACE(CONCAT(IFNULL(`firma`, ''), IFNULL(`zusatz_firma`, '')), ' ', '') LIKE "{firma}%"
                                            OR
                                            REPLACE(CONCAT(IFNULL(`rg_firma`, ''), IFNULL(`rg_zusatz_firma`, '')), ' ', '') LIKE "{firma}%")""".format(firma=str(suchparameter["firma"]).replace(" ", ""))
                    filters_list.append(query_string)
                    faktura_filters_list.append(query_string)
            else:
                if suchparameter["zusatz_firma"]:
                    query_string = """(REPLACE(CONCAT(IFNULL(`firma`, ''), IFNULL(`zusatz_firma`, '')), ' ', '') LIKE "{zusatz_firma}%"
                                            OR
                                            REPLACE(CONCAT(IFNULL(`rg_firma`, ''), IFNULL(`rg_zusatz_firma`, '')), ' ', '') LIKE "{zusatz_firma}%")""".format(zusatz_firma=str(suchparameter["zusatz_firma"]).replace(" ", ""))
                    filters_list.append(query_string)
                    faktura_filters_list.append(query_string)
        else:
            if suchparameter["firma"]:
                query_string = """(REPLACE(CONCAT(IFNULL(`firma`, ''), IFNULL(`zusatz_firma`, '')), ' ', '') LIKE "{firma}%"
                                        OR
                                        REPLACE(CONCAT(IFNULL(`rg_firma`, ''), IFNULL(`rg_zusatz_firma`, '')), ' ', '') LIKE "{firma}%")""".format(firma=str(suchparameter["firma"]).replace(" ", ""))
                filters_list.append(query_string)
                faktura_filters_list.append(query_string)
    
    # Adressdaten
    if suchparameter["zusatz_adresse"]:
        filters_list.append("""(`zusatz_adresse` LIKE '{zusatz_adresse}%' OR `rg_zusatz_adresse` LIKE '{zusatz_adresse}%' OR `objekt_zusatz_adresse` LIKE '{zusatz_adresse}%')""".format(zusatz_adresse=suchparameter["zusatz_adresse"]))
        faktura_filters_list.append("""(`zusatz_adresse` LIKE '{zusatz_adresse}%' OR `rg_zusatz_adresse` LIKE '{zusatz_adresse}%')""".format(zusatz_adresse=suchparameter["zusatz_adresse"]))
    
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
        faktura_filters_list.append("""(REPLACE(CONCAT(IFNULL(`strasse`, ''), IFNULL(`nummer`, ''), IFNULL(`nummer_zu`, '')), ' ', '') LIKE '{strassensuchwert}'
                                        OR
                                        REPLACE(CONCAT(IFNULL(`rg_strasse`, ''), IFNULL(`rg_nummer`, ''), IFNULL(`rg_nummer_zu`, '')), ' ', '') LIKE '{strassensuchwert}')""".format(strassensuchwert=strassensuchwert.replace(" ", "")))
    
    if suchparameter["postfach_nummer"]:
        query_string = """(`postfach_nummer` LIKE '{postfach_nummer}%' OR `rg_postfach_nummer` LIKE '{postfach_nummer}%')""".format(postfach_nummer=suchparameter["postfach_nummer"])
        filters_list.append(query_string)
        faktura_filters_list.append(query_string)
    if suchparameter["postfach"]:
        query_string = """(`postfach` = 1 OR `rg_postfach` = 1)"""
        filters_list.append(query_string)
        faktura_filters_list.append(query_string)
    if suchparameter["plz"]:
        filters_list.append("""(`plz` LIKE '{plz}%' OR `rg_plz` LIKE '{plz}%' OR `objekt_plz` LIKE '{plz}%')""".format(plz=suchparameter["plz"]))
        faktura_filters_list.append("""(`plz` LIKE '{plz}%' OR `rg_plz` LIKE '{plz}%')""".format(plz=suchparameter["plz"]))
    if suchparameter["ort"]:
        filters_list.append("""(`ort` LIKE '{ort}%' OR `rg_ort` LIKE '{ort}%' OR `objekt_ort` LIKE '{ort}%')""".format(ort=suchparameter["ort"]))
        faktura_filters_list.append("""(`ort` LIKE '{ort}%' OR `rg_ort` LIKE '{ort}%')""".format(ort=suchparameter["ort"]))
    
    if len(filters_list) > 0:
        filters = (" AND ").join(filters_list)
        filters = 'WHERE ' + filters
    else:
        filters = ''
        
    if len(faktura_filters_list) > 0:
        faktura_filters = (" AND ").join(faktura_filters_list)
        faktura_filters = 'WHERE ' + faktura_filters
    else:
        faktura_filters = ''
    
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
            faktura_kunden = []
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
            # ~ frappe.throw("""SELECT * FROM `tabKunden` {filters}""".format(filters=faktura_filters))
            faktura_kunden = frappe.db.sql("""SELECT * FROM `tabKunden` {filters}""".format(filters=faktura_filters), as_dict=True)
        
        if len(mitgliedschaften) > 0 or len(faktura_kunden) > 0:
            if not suchparameter["sektions_uebergreifend"]:
                resultate_html = get_resultate_html(mitgliedschaften, faktura_kunden=faktura_kunden)
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

def get_resultate_html(mitgliedschaften, faktura_kunden=None):
    meine_sektionen = []
    from frappe.defaults import get_user_permissions
    restriktionen = frappe.defaults.get_user_permissions(str(frappe.session.user))
    if "Sektion" in restriktionen:
        for sektion in restriktionen["Sektion"]:
            meine_sektionen.append(sektion.doc)
    
    data = {
        'mitgliedschaften': mitgliedschaften,
        'meine_sektionen': meine_sektionen if len(meine_sektionen) > 0 else False,
        'faktura_kunden': faktura_kunden
    }
    
    return frappe.render_template('templates/includes/mvd_suchresultate.html', data)

@frappe.whitelist()
def anlage_prozess(anlage_daten, druckvorlage=False, massendruck=False, faktura=False):
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
    
    if not faktura:
        hv_bar_bezahlt = False
        if "hv_bar_bezahlt" in anlage_daten and int(anlage_daten["hv_bar_bezahlt"]) == 1:
            hv_bar_bezahlt = True
        
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
            "abweichende_objektadresse": 1 if int(anlage_daten["postfach"]) == 1 else '0',
            "interessent_typ": anlage_daten["interessent_typ"],
            "bezahltes_mitgliedschaftsjahr": get_mitgl_jahr_in_anlage(anlage_daten["sektion_id"]) if anlage_daten["status"] == 'Regulär' else None,
            "datum_zahlung_mitgliedschaft": today() if anlage_daten["status"] == 'Regulär' else None,
            "zahlung_hv": get_mitgl_jahr_in_anlage(anlage_daten["sektion_id"]) if hv_bar_bezahlt else None,
            "datum_hv_zahlung": today() if hv_bar_bezahlt else None
        })
        mitgliedschaft.insert(ignore_permissions=True)
        
        # optional: erstelle Rechnung
        if anlage_daten["status"] == 'Regulär':
            bezahlt = True
            if int(massendruck) == 1:
                massendruck = True
            sinv = create_mitgliedschaftsrechnung(mitgliedschaft=mitgliedschaft.name, bezahlt=bezahlt, submit=True, attach_as_pdf=True, hv_bar_bezahlt=hv_bar_bezahlt, druckvorlage=druckvorlage, massendruck=massendruck)
        else:
            if "autom_rechnung" in anlage_daten and int(anlage_daten["autom_rechnung"]) == 1:
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
    else:
        # erstelle Faktura Kunde
        faktura_kunde = frappe.get_doc({
            "doctype": "Kunden",
            "sektion_id": anlage_daten["sektion_id"],
            "language": anlage_daten["language"],
            "kundentyp": anlage_daten["kundentyp"],
            "firma": firma,
            "zusatz_firma": zusatz_firma,
            "anrede_c": anlage_daten["anrede"] if 'anrede' in anlage_daten else '',
            "nachname": anlage_daten["nachname"],
            "vorname": anlage_daten["vorname"],
            "tel_p": anlage_daten["telefon"] if 'telefon' in anlage_daten else '',
            "tel_m": anlage_daten["telefon_m"] if 'telefon_m' in anlage_daten else '',
            "tel_g": anlage_daten["telefon_g"] if 'telefon_g' in anlage_daten else '',
            "e_mail": anlage_daten["email"] if 'email' in anlage_daten else '',
            "zusatz_adresse": anlage_daten["zusatz_adresse"] if 'zusatz_adresse' in anlage_daten else '',
            "strasse": anlage_daten["strasse"] if 'strasse' in anlage_daten else '',
            "nummer": anlage_daten["nummer"] if 'nummer' in anlage_daten else '',
            "nummer_zu": anlage_daten["nummer_zu"] if 'nummer_zu' in anlage_daten else '',
            "postfach": anlage_daten["postfach"],
            "postfach_nummer": anlage_daten["postfach_nummer"] if 'postfach_nummer' in anlage_daten else '',
            "plz": anlage_daten["plz"],
            "ort": anlage_daten["ort"],
            "abweichende_rechnungsadresse": 0
        })
        faktura_kunde.insert(ignore_permissions=True)
        return faktura_kunde.name

def get_mitgl_jahr_in_anlage(sektion_id):
    sektion = frappe.get_doc("Sektion", sektion_id)
    gratis_ab = getdate(getdate(today()).strftime("%Y") + "-" + getdate(sektion.gratis_bis_ende_jahr).strftime("%m") + "-" + getdate(sektion.gratis_bis_ende_jahr).strftime("%d"))
    if getdate(today()) >= gratis_ab:
        return cint(getdate(today()).strftime("%Y")) + 1
    return cint(getdate(today()).strftime("%Y"))

@frappe.whitelist()
def create_serien_email(search_hash=None, mitglied_selektion=None):
    if not search_hash and not mitglied_selektion:
        return
    
    if search_hash:
        # get mitgliedschafts data basierend auf search_hash aus Mitgliedschaftssuchmaske
        mitgliedschaften = frappe.db.sql("""
                                            SELECT
                                                `name` AS `mv_mitgliedschaft`,
                                                `e_mail_1` AS `email`,
                                                CASE
                                                    WHEN `e_mail_1` IS NOT NULL THEN
                                                        CASE
                                                            WHEN `e_mail_1` NOT IN ('', 'None') THEN 'Open'
                                                            ELSE 'E-Mail missing'
                                                        END
                                                    ELSE 'E-Mail missing'
                                                END AS `status`
                                            FROM `tabMitgliedschaft`
                                            WHERE `search_hash` = '{search_hash}'""".format(search_hash=search_hash), as_dict=True)
        
        if len(mitgliedschaften) < 1:
            return
    elif mitglied_selektion:
        # get mitgliedschafts data basierend auf mitgliedschaftsliste aus Selektion
        if isinstance(mitglied_selektion, str):
            mitglied_selektion = json.loads(mitglied_selektion)
            mitgliedschaften_list = []
            for mitgliedschaft in mitglied_selektion:
                mitgliedschaften_list.append(mitgliedschaft['name'])
            mitgliedschaften_list_filter = ", ".join(mitgliedschaften_list)
            mitgliedschaften = frappe.db.sql("""
                                            SELECT
                                                `name` AS `mv_mitgliedschaft`,
                                                `e_mail_1` AS `email`,
                                                CASE
                                                    WHEN `e_mail_1` IS NOT NULL THEN
                                                        CASE
                                                            WHEN `e_mail_1` NOT IN ('', 'None') THEN 'Open'
                                                            ELSE 'E-Mail missing'
                                                        END
                                                    ELSE 'E-Mail missing'
                                                END AS `status`
                                            FROM `tabMitgliedschaft`
                                            WHERE `name` IN ({mitgliedschaften_list_filter})""".format(mitgliedschaften_list_filter=mitgliedschaften_list_filter), as_dict=True)
            if len(mitgliedschaften) < 1:
                return
    
    
    sektion_id = frappe.db.get_value("Mitgliedschaft", mitgliedschaften[0].mv_mitgliedschaft, "sektion_id")
    empfaenger = mitgliedschaften
    
    # erstelle Serien Email
    serien_email = frappe.get_doc({
        "doctype": "Serien Email",
        "sektion_id": sektion_id,
        "title": now().split(".")[0],
        "empfaenger": empfaenger
    })
    serien_email.flags.ignore_validate = True
    
    serien_email.insert(ignore_permissions=True)
    return serien_email.name

@frappe.whitelist()
def history_search(suchparameter):
    if isinstance(suchparameter, six.string_types):
        suchparameter = json.loads(suchparameter)
    
    query_string = ''
    
    if suchparameter["sektion_id"]:
        query_string += """
            AND `docname` IN (
                SELECT `name` FROM `tabMitgliedschaft`
                WHERE `sektion_id` = '{sektion_id}'
            )
        """.format(sektion_id=suchparameter["sektion_id"])
    if suchparameter["strasse"]:
        query_string += """
            AND `data` LIKE '%"strasse",%"{strasse}",%'
        """.format(strasse=suchparameter["strasse"])
    if suchparameter["nummer"]:
        query_string += """
            AND `data` LIKE '%"nummer",%"{nummer}",%'
        """.format(nummer=suchparameter["nummer"])
    if suchparameter["plz"]:
        query_string += """
            AND `data` LIKE '%"plz",%"{plz}",%'
        """.format(plz=suchparameter["plz"])
    if suchparameter["ort"]:
        query_string += """
            AND `data` LIKE '%"ort",%"{ort}",%'
        """.format(ort=suchparameter["ort"])
    
    sql_query = """
        SELECT `data`, `docname` FROM `tabVersion`
        WHERE `ref_doctype` = 'Mitgliedschaft'
        {query_string}
    """.format(query_string=query_string)

    found_histories = frappe.db.sql(sql_query, as_dict=True)

    if len(found_histories) < 1:
        frappe.throw("Es wurde keine entsprechende Historie gefunden.")
    
    results = {}
    for found_history in found_histories:
        if found_history.docname not in results:
            results[found_history.docname] = {
                'mitglied_nr': frappe.db.get_value("Mitgliedschaft", found_history.docname, "mitglied_nr"),
                'mitglied_id': found_history.docname,
                'ampel_farbe': frappe.db.get_value("Mitgliedschaft", found_history.docname, "ampel_farbe"),
                'strasse': [],
                'nummer': [],
                'plz': [],
                'ort': [],
                'neue_adresse': frappe.db.get_value("Mitgliedschaft", found_history.docname, "adressblock"),
            }
        
        json_data = json.loads(found_history.data)
        for changed in json_data['changed']:
            if changed[0] == "strasse":
                results[found_history.docname]['strasse'].append([
                    changed[1],
                    changed[2]
                ])
            if changed[0] == "nummer":
                results[found_history.docname]['nummer'].append([
                    changed[1],
                    changed[2]
                ])
            if changed[0] == "plz":
                results[found_history.docname]['plz'].append([
                    changed[1],
                    changed[2]
                ])
            if changed[0] == "ort":
                results[found_history.docname]['ort'].append([
                    changed[1],
                    changed[2]
                ])

    data = {
        'mitgliedschaften': results
    }
    
    return frappe.render_template('templates/includes/mvd_suchresultate_history_search.html', data)
