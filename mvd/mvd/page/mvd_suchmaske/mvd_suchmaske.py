# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import add_days, getdate
import six
import json

@frappe.whitelist()
def suche(suchparameter):
    if isinstance(suchparameter, six.string_types):
        suchparameter = json.loads(suchparameter)
    
    filters_list = []
    
    # allgemein
    if suchparameter["sektion_id"]:
        filters_list.append("""`sektion_id` = '{sektion_id}'""".format(sektion_id=suchparameter["sektion_id"]))
    if suchparameter["mitglied_nr"]:
        filters_list.append("""`mitglied_nr` LIKE '%{mitglied_nr}%'""".format(mitglied_nr=suchparameter["mitglied_nr"]))
    if suchparameter["status_c"]:
        filters_list.append("""`status_c` = '{status_c}'""".format(status_c=suchparameter["status_c"]))
    if suchparameter["mitgliedtyp_c"]:
        filters_list.append("""`mitgliedtyp_c` = '{mitgliedtyp_c}'""".format(mitgliedtyp_c=suchparameter["mitgliedtyp_c"]))
    if suchparameter["mitglied_c"]:
        filters_list.append("""`mitglied_c` = '{mitglied_c}'""".format(mitglied_c=suchparameter["mitglied_c"]))
    
    # Kontaktdaten
    if suchparameter["vorname"]:
        filters_list.append("""(`vorname_1` LIKE '%{vorname}%' OR `rg_vorname` LIKE '%{vorname}%' OR `vorname_2` LIKE '%{vorname}%')""".format(vorname=suchparameter["vorname"]))
    if suchparameter["nachname"]:
        filters_list.append("""(`nachname_1` LIKE '%{nachname}%' OR `rg_nachname` LIKE '%{nachname}%' OR `nachname_2` LIKE '%{nachname}%')""".format(nachname=suchparameter["nachname"]))
    if suchparameter["tel"]:
        filters_list.append("""
                            ((`tel_p_1` LIKE '%{tel}%' OR `rg_tel_p` LIKE '%{tel}%' OR `tel_p_2` LIKE '%{tel}%')
                            OR
                            (`tel_m_1` LIKE '%{tel}%' OR `rg_tel_m` LIKE '%{tel}%' OR `tel_m_2` LIKE '%{tel}%')
                            OR
                            (`tel_g_1` LIKE '%{tel}%' OR `rg_tel_g` LIKE '%{tel}%' OR `tel_g_2` LIKE '%{tel}%'))""".format(tel=suchparameter["tel"].replace(" ", "")))
    if suchparameter["email"]:
        filters_list.append("""(`e_mail_1` LIKE '%{email}%' OR `rg_e_mail` LIKE '%{email}%' OR `e_mail_2` LIKE '%{email}%')""".format(email=suchparameter["email"]))
    
    # Adressdaten
    if suchparameter["zusatz_adresse"]:
        filters_list.append("""(`zusatz_adresse` LIKE '%{zusatz_adresse}%' OR `rg_zusatz_adresse` LIKE '%{zusatz_adresse}%' OR `objekt_zusatz_adresse` LIKE '%{zusatz_adresse}%')""".format(zusatz_adresse=suchparameter["zusatz_adresse"]))
    if suchparameter["nummer"]:
        filters_list.append("""(`nummer` LIKE '%{nummer}%' OR `rg_nummer` LIKE '%{nummer}%' OR `objekt_hausnummer` LIKE '%{nummer}%')""".format(nummer=suchparameter["nummer"]))
    if suchparameter["nummer_zu"]:
        filters_list.append("""(`nummer_zu` LIKE '%{nummer_zu}%' OR `rg_nummer_zu` LIKE '%{nummer_zu}%' OR `objekt_nummer_zu` LIKE '%{nummer_zu}%')""".format(nummer_zu=suchparameter["nummer_zu"]))
    if suchparameter["postfach_nummer"]:
        filters_list.append("""(`postfach_nummer` LIKE '%{postfach_nummer}%' OR `rg_postfach_nummer` LIKE '%{postfach_nummer}%')""".format(postfach_nummer=suchparameter["postfach_nummer"]))
    if suchparameter["strasse"]:
        filters_list.append("""(`strasse` LIKE '%{strasse}%' OR `rg_strasse` LIKE '%{strasse}%' OR `objekt_strasse` LIKE '%{strasse}%')""".format(strasse=suchparameter["strasse"]))
    if suchparameter["postfach"]:
        filters_list.append("""(`postfach` = 1 OR `rg_postfach` = 1)""")
    if suchparameter["plz"]:
        filters_list.append("""(`plz` LIKE '%{plz}%' OR `rg_plz` LIKE '%{plz}%' OR `objekt_plz` LIKE '%{plz}%')""".format(plz=suchparameter["plz"]))
    if suchparameter["ort"]:
        filters_list.append("""(`ort` LIKE '%{ort}%' OR `rg_ort` LIKE '%{ort}%' OR `objekt_ort` LIKE '%{ort}%')""".format(ort=suchparameter["ort"]))
    
    if len(filters_list) > 0:
        filters = (" AND ").join(filters_list)
        filters = 'WHERE ' + filters
    else:
        filters = ''
    
    mitgliedschaften = frappe.db.sql("""SELECT `name` FROM `tabMV Mitgliedschaft` {filters}""".format(filters=filters), as_dict=True)
    
    if len(mitgliedschaften) > 0:
        resultate_html = get_resultate_html(mitgliedschaften)
        return resultate_html
    else:
        return False

def get_resultate_html(mitgliedschaften):
    
    suchresultate = []
    
    for mitgliedschaft in mitgliedschaften:
        mitgliedschaft = frappe.get_doc("MV Mitgliedschaft", mitgliedschaft.name)
        
        ''' mögliche Ampelfarben:
        - Grün: ampelgruen --> Mitglied kann alle Dienstleistungen beziehen (keine Karenzfristen, keine überfälligen oder offen Rechnungen)
        - Gelb: ampelgelb --> Karenzfristen oder offene Rechnungen
        - Rot: ampelrot --> überfällige offene Rechnungen
        '''
        
        rechnungs_kunde = mitgliedschaft.kunde_mitglied
        ueberfaellige_rechnungen = 0
        offene_rechnungen = 0
        
        sektion = frappe.get_doc("Sektion", mitgliedschaft.sektion_id)
        karenzfrist_in_d = sektion.karenzfrist
        ablauf_karenzfrist = add_days(getdate(mitgliedschaft.eintritt), karenzfrist_in_d)
        if getdate() < ablauf_karenzfrist:
            karenzfrist = False
        else:
            karenzfrist = True
        
        if mitgliedschaft.rg_kunde:
            rechnungs_kunde = mitgliedschaft.rg_kunde
        ueberfaellige_rechnungen = frappe.db.sql("""SELECT IFNULL(SUM(`outstanding_amount`), 0) AS `open_amount`
                                                    FROM `tabSales Invoice` 
                                                    WHERE `customer` = '{rechnungs_kunde}'
                                                    AND `due_date` < CURDATE()
                                                    AND `docstatus` = 1""".format(rechnungs_kunde=rechnungs_kunde), as_dict=True)[0].open_amount
        
        if ueberfaellige_rechnungen > 0:
            ampelfarbe = 'red'
        else:
            offene_rechnungen = frappe.db.sql("""SELECT IFNULL(SUM(`outstanding_amount`), 0) AS `open_amount`
                                                FROM `tabSales Invoice` 
                                                WHERE `customer` = '{rechnungs_kunde}'
                                                AND `due_date` >= CURDATE()
                                                AND `docstatus` = 1""".format(rechnungs_kunde=rechnungs_kunde), as_dict=True)[0].open_amount
            
            if offene_rechnungen > 0:
                ampelfarbe = 'yellow'
            else:
                if not karenzfrist:
                    ampelfarbe = 'yellow'
                else:
                    ampelfarbe = 'limegreen'
        dict_mitgliedschaft = mitgliedschaft.as_dict()
        dict_mitgliedschaft.ampelfarbe = ampelfarbe
        suchresultate.append(dict_mitgliedschaft)
    
    meine_sektionen = []
    from frappe.defaults import get_user_permissions
    restriktionen = frappe.defaults.get_user_permissions(str(frappe.session.user))
    if "Sektion" in restriktionen:
        for sektion in restriktionen["Sektion"]:
            meine_sektionen.append(sektion.doc)
    
    data = {
        'mitgliedschaften': suchresultate,
        'meine_sektionen': meine_sektionen if len(meine_sektionen) > 0 else False
    }
    
    return frappe.render_template('templates/includes/mvd_suchresultate.html', data)
