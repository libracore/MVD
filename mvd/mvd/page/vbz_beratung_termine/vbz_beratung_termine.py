# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.data import today, now_datetime, get_datetime
from frappe import _
from frappe.utils import cint

no_cache=1

@frappe.whitelist()
def get_open_data(free_only=0, beratungsort=None, berater_in=None,
                  art=None, datum=None, language=None, fachskill=None,
                  my_reservations_only=0, beratungstyp=None, termine_heute=0,
                  termine_gebucht=0, datum_bis=None, chronologische_termine=0):
    alle_termine, meine_termine, anz_eingetroffen = get_alle_beratungs_termine(frappe.session.user, free_only, beratungsort,
                                                                               berater_in, art, datum, language, fachskill,
                                                                               my_reservations_only, beratungstyp, termine_heute,
                                                                               termine_gebucht, datum_bis, chronologische_termine)
    datasets = {
        'datenstand_as': now_datetime().strftime("%d.%m.%Y %H:%M:%S"),
        'datenstand_for_polling': now_datetime().strftime("%Y-%m-%d %H:%M:%S"),
        'anz_eingetroffen_for_polling': anz_eingetroffen,
        'alle_termine': alle_termine,
        'meine_termine': meine_termine
    }
    return datasets

def get_alle_beratungs_termine(user, free_only=0, beratungsort=None,
                               berater_in=None, art=None, datum=None,
                               language=None, fachskill=None, my_reservations_only=0,
                               beratungstyp=None, termine_heute=0, termine_gebucht=0,
                               datum_bis=None, chronologische_termine=0):
    alle = []
    meine = []
    anz_eingetroffen = 0
    vergebene_termin_liste = []
    kontaktperson_multi_user = get_kontaktperson_multi_user(user)
    erb_block = True if "MV_ERB" in frappe.get_roles() else False
    if erb_block:
        erb_block = False if "System Manager" in frappe.get_roles() else True

    sektionen = frappe.db.sql("""
                                SELECT `for_value`
                                FROM `tabUser Permission`
                                WHERE `allow` = 'Sektion'
                                AND `user` = '{user}'
                                ORDER BY `is_default` DESC""".format(user=user), as_dict=True)
    if len(sektionen) > 0:
        erlaubte_sektionen = []
        for sektion in sektionen:
            erlaubte_sektionen.append(sektion.for_value)
    else:
        erlaubte_sektionen = False
    
    datum_von = today()
    if datum and datum != '':
        if cint(termine_heute) != 1:
            datum_von = datum
    
    # Filter
    beratungsort_filter = ''
    if beratungsort and beratungsort != '':
        beratungsort_filter = "AND `berTer`.`ort` = '{0}'".format(beratungsort)
    
    berater_in_filter = ''
    if berater_in and berater_in != '':
        berater_in_filter = "AND `berTer`.`berater_in` = '{0}'".format(berater_in)
    
    art_filter = ''
    if art and art != '':
        art_filter = "AND `berTer`.`art` = '{0}'".format(art)
    
    datum_filter = ''
    if cint(termine_heute) == 1:
        datum_filter = """
            `berTer`.`von` >= '{datum_von} 00:00:00'
            AND `berTer`.`von` <= '{datum_von} 23:59:59'
        """.format(datum_von=datum_von)
    else:
        if (datum_bis):
            datum_filter = """
                (
                    (`berTer`.`von` BETWEEN '{datum_von} 00:00:00' AND '{datum_bis} 23:59:59') OR 
                    (`beratung`.`status` = 'Termin vereinbart' AND `berTer`.`von` < '{datum_von} 00:00:00')
                )
            """.format(datum_von=datum_von, datum_bis=datum_bis)
        else:
            datum_filter = """
                (
                    (`berTer`.`von` >= '{datum_von} 00:00:00') OR 
                    (`beratung`.`status` = 'Termin vereinbart' AND `berTer`.`von` < '{datum_von} 00:00:00')
                )
            """.format(datum_von=datum_von)
    
    fachskill_filter = ''
    if fachskill and fachskill != '':
        fachskill_filter = "AND `berTer`.`fachskill` LIKE '%{0}%'".format(fachskill)
    
    sprach_filter = ''
    if language and language != '':
        sprach_filter = "AND `berTer`.`language` = '{0}'".format(language)
    
    beratungstyp_filter = ''
    if beratungstyp:
        if beratungstyp == "Privat":
            beratungstyp_filter = "AND (`berTer`.`beratungstyp` = 'Privat' OR `berTer`.`beratungstyp` IS NULL)"
        if beratungstyp == "Geschäft":
            beratungstyp_filter = "AND `berTer`.`beratungstyp` = 'Geschäft'"
    
    if not cint(my_reservations_only) == 1:
    
        alle_termine = frappe.db.sql("""
                                        SELECT
                                            `berTer`.`von`,
                                            `berTer`.`bis`,
                                            `berTer`.`art`,
                                            `berTer`.`ort`,
                                            `berTer`.`parent`,
                                            `berTer`.`berater_in`,
                                            `berTer`.`telefonnummer`,
                                            IFNULL(`berTer`.`wunsch_berater_in`, '---') AS `wunsch_berater_in`,
                                            `beratung`.`sektion_id`,
                                            `beratung`.`beratungskategorie`,
                                            `beratung`.`beratungskategorie_2`,
                                            `beratung`.`beratungskategorie_3`,
                                            `beratung`.`mv_mitgliedschaft`,
                                            `beratung`.`faktura_kunde`,
                                            `beratung`.`status`,
                                            `beratung`.`terminkategorie`,
                                            IFNULL(`beratung`.`person_ist_eingetroffen`, 0) AS `person_ist_eingetroffen`,
                                            `berTer`.`abp_referenz`,
                                            `berTer`.`beratungstyp`
                                        FROM `tabBeratung Termin` AS `berTer`
                                        LEFT JOIN `tabBeratung` AS `beratung` ON `berTer`.`parent` = `beratung`.`name`
                                        WHERE
                                        {datum_filter}
                                        {beratungsort_filter}
                                        {berater_in_filter}
                                        {art_filter}
                                        {fachskill_filter}
                                        {sprach_filter}
                                        {beratungstyp_filter}
                                        ORDER BY `berTer`.`von` DESC
                                    """.format(datum_filter=datum_filter, beratungsort_filter=beratungsort_filter, berater_in_filter=berater_in_filter, \
                                                art_filter=art_filter, fachskill_filter=fachskill_filter, sprach_filter=sprach_filter, \
                                                beratungstyp_filter=beratungstyp_filter), as_dict=True)
        for termin in alle_termine:
            if not erlaubte_sektionen or termin.sektion_id in erlaubte_sektionen:
                if not erb_block or termin.berater_in in kontaktperson_multi_user:
                    hat_attachement = 1 if frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabBeratungsdateien` WHERE `parent` = '{termin}'""".format(termin=termin.parent), as_dict=True)[0].qty > 0 else 0
                    
                    if termin.mv_mitgliedschaft:
                        m_daten = frappe.db.get_value("Mitgliedschaft", termin.mv_mitgliedschaft, ["vorname_1", "nachname_1", "status_c"], as_dict=True)
                        vorname = m_daten.get("vorname_1") if m_daten else ""
                        nachname = m_daten.get("nachname_1") if m_daten else ""
                        status_c = m_daten.get("status_c") if m_daten else ""
                        link = "/desk#Form/Mitgliedschaft/{0}".format(termin.mv_mitgliedschaft)
                    elif termin.faktura_kunde:
                        k_daten = frappe.db.get_value("Kunden", termin.faktura_kunde, ["vorname", "nachname"], as_dict=True)
                        vorname = k_daten.get("vorname") if k_daten else ""
                        nachname = k_daten.get("nachname") if k_daten else ""
                        status_c = "Kunde"
                        link = "/desk#Form/Kunden/{0}".format(termin.faktura_kunde)
                    else:
                        vorname, nachname = "", ""
                    name_mitglied = "{0} {1}".format(vorname or "", nachname or "").strip()
                    name_mitglied_mit_link = """<a href="{0}" target="_blank">{1}<br>({2})</a>""".format(link, name_mitglied, status_c)

                    termin_data = {
                        'von_date': get_datetime(termin.von).strftime('%d.%m.%Y'),
                        'von_time': get_datetime(termin.von).strftime('%H:%M'),
                        'bis_time': get_datetime(termin.bis).strftime('%H:%M'),
                        'art': termin.art,
                        'ort': termin.ort,
                        'status': termin.status,
                        'beratung': termin.parent,
                        'beraterinn': termin.berater_in,
                        'hat_attachement': hat_attachement,
                        'telefonnummer': termin.telefonnummer,
                        'wunsch_berater_in': termin.wunsch_berater_in,
                        'wochentag': _(get_datetime(termin.von).strftime('%A'))[:2],
                        'beratungskategorie': termin.beratungskategorie.split(" - ")[0] if termin.beratungskategorie else '',
                        'beratungskategorie_2': termin.beratungskategorie_2.split(" - ")[0] if termin.beratungskategorie_2 else '',
                        'beratungskategorie_3': termin.beratungskategorie_3.split(" - ")[0] if termin.beratungskategorie_3 else '',
                        'name_mitglied': name_mitglied_mit_link,
                        'sort_date': frappe.utils.getdate(termin.von),
                        'name_for_reservation': '---',
                        'person_ist_eingetroffen': termin.person_ist_eingetroffen,
                        'is_business': 1 if termin.beratungstyp == "Geschäft" else 0,
                        'terminkategorie': termin.terminkategorie
                    }
                    if cint(termin.person_ist_eingetroffen) == 1:
                        anz_eingetroffen += 1
                    
                    if not cint(free_only) == 1:
                        alle.append(termin_data)
            if termin.berater_in in kontaktperson_multi_user:
                meine.append(termin_data)
            if termin.abp_referenz:
                vergebene_termin_liste.append(termin.abp_referenz)
        if len(meine) < 1:
            meine.append({'show_placeholder': 1})
    else:
        meine.append({'show_placeholder': 1})
    
    if not cint(termine_gebucht) == 1:
        # Filter
        beratungsort_filter = ''
        if beratungsort and beratungsort != '':
            beratungsort_filter = "AND `zuw`.`art_ort` = '{0}'".format(beratungsort)
        
        berater_in_filter = ''
        if berater_in and berater_in != '':
            berater_in_filter = "AND `zuw`.`beratungsperson` = '{0}'".format(berater_in)
        
        fachskill_filter = ''
        if fachskill and fachskill != '':
            fachskill_filter = """AND `zuw`.`beratungsperson` IN (
                SELECT `parent` FROM `tabTermin Kontaktperson Multi Fachskill` WHERE `fachskill` = '{0}'
            )""".format(fachskill)
        
        sprach_filter = ''
        if language and language != '':
            sprach_filter = """AND `zuw`.`beratungsperson` IN (
                SELECT `parent` FROM `tabTermin Kontaktperson Multi Language` WHERE `language` = '{0}'
            )""".format(language)
        
        beratungstyp_filter = ''
        if beratungstyp:
            if beratungstyp == "Privat":
                beratungstyp_filter = "AND (`zuw`.`beratungstyp` = 'Privat' OR `zuw`.`beratungstyp` IS NULL)"
            if beratungstyp == "Geschäft":
                beratungstyp_filter = "AND `zuw`.`beratungstyp` = 'Geschäft'"
        
        if cint(termine_heute) == 1:
            datum_filter = """
                AND `zuw`.`date` >= '{datum_von} 00:00:00'
                AND `zuw`.`date` <= '{datum_von} 23:59:59'
            """.format(datum_von=datum_von)
        else:
            datum_filter = """
                AND `zuw`.`date` >= '{datum_von}'
            """.format(datum_von=datum_von)
        
        art_filter = ''
        if art and art != '':
            art_filter = "AND (`beratungsort`.`default_art` = '{0}' OR `beratungsort`.`default_art` IS NULL)".format(art)
        
        freie_termine = frappe.db.sql("""
                                    SELECT DISTINCT
                                        CONCAT(`date`, ' ', `zuw`.`from_time`) AS `von`,
                                        CONCAT(`date`, ' ', `zuw`.`to_time`) AS `bis`,
                                        `zuw`.`art_ort` AS `ort`,
                                        `zuw`.`beratungsperson` AS `beraterinn`,
                                        NULL AS `von_date`,
                                        NULL AS `von_time`,
                                        NULL AS `bis_time`,
                                        IFNULL(`beratungsort`.`default_art`, '---') AS `art`,
                                        '---' AS `beratung`,
                                        0 AS `hat_attachement`,
                                        '---' AS `telefonnummer`,
                                        '---' AS `wunsch_berater_in`,
                                        NULL AS `wochentag`,
                                        '---' AS `beratungskategorie`,
                                        '---' AS `beratungskategorie_2`,
                                        '---' AS `beratungskategorie_3`,
                                        '---' AS `terminkategorie`,
                                        '---' AS `name_mitglied`,
                                        NULL AS `sort_date`,
                                        IFNULL(`zuw`.`reserved`, 0) AS `reserved_mark`,
                                        `zuw`.`reserved_by`,
                                        1 AS `is_free`,
                                        `zuw`.`name` AS `name_for_reservation`,
                                        `zuw`.`beratungstyp`,
                                        NULL AS `is_business`
                                    FROM `tabAPB Zuweisung` AS `zuw`
                                    LEFT JOIN `tabBeratungsort` AS `beratungsort` ON `zuw`.`art_ort` = `beratungsort`.`name`
                                    WHERE `zuw`.`name` NOT IN ('{vergebene_termine}')
                                    {datum_filter}
                                    {beratungsort_filter}
                                    {berater_in_filter}
                                    {fachskill_filter}
                                    {sprach_filter}
                                    {beratungstyp_filter}
                                    {art_filter}
                                    """.format(vergebene_termine="', '".join(vergebene_termin_liste), \
                                                datum_filter=datum_filter, beratungsort_filter=beratungsort_filter, \
                                                berater_in_filter=berater_in_filter, fachskill_filter=fachskill_filter, \
                                                sprach_filter=sprach_filter, beratungstyp_filter=beratungstyp_filter, \
                                                art_filter=art_filter), as_dict=True)
        for freier_termin in freie_termine:
            freier_termin.von = frappe.utils.get_datetime(freier_termin.von)
            freier_termin.bis = frappe.utils.get_datetime(freier_termin.bis)
            freier_termin.von_date = get_datetime(freier_termin.von).strftime('%d.%m.%Y')
            freier_termin.von_time = get_datetime(freier_termin.von).strftime('%H:%M')
            freier_termin.bis_time = get_datetime(freier_termin.bis).strftime('%H:%M')
            freier_termin.wochentag = _(get_datetime(freier_termin.von).strftime('%A'))[:2]
            freier_termin.sort_date = frappe.utils.getdate(freier_termin.von)
            freier_termin.sektion_id = frappe.db.get_value("Termin Kontaktperson", freier_termin.beraterinn, "sektion_id")
            freier_termin.is_business = 1 if freier_termin.beratungstyp == "Geschäft" else 0
        
        for freier_termin in freie_termine:
            if not erlaubte_sektionen or freier_termin.sektion_id in erlaubte_sektionen:
                if not erb_block or freier_termin.beraterinn in kontaktperson_multi_user:
                    if not cint(my_reservations_only) == 1:
                        alle.append(freier_termin)
                    else:
                        if freier_termin.reserved_by == frappe.session.user:
                            alle.append(freier_termin)

    if cint(chronologische_termine):
        alle_sortiert = sorted(alle, key = lambda x: (x['sort_date'], x['von_time'], x['beraterinn'] or 'ZZZ'))
    else:
        alle_sortiert = sorted(alle, key = lambda x: (x['sort_date'], x['beraterinn'] or 'ZZZ', x['von_time']))
    
    return alle_sortiert, meine, anz_eingetroffen

def get_kontaktperson_multi_user(user):
    kontaktperson_multi_user = frappe.db.sql("""SELECT `parent`
                                                FROM `tabTermin Kontaktperson Multi User`
                                                WHERE `user` = '{user}'  """.format(user=user), as_dict=True)
    user_list = []
    for multi_user in kontaktperson_multi_user:
        user_list.append(multi_user.parent)
    return user_list

@frappe.whitelist()
def has_changed(since):
    sql = """
        SELECT
            COUNT(`name`) AS `qty`
        FROM `tabAPB Zuweisung`
        WHERE `modified` > '{since}'
    """.format(since=since.replace("T", " "))

    return frappe.db.sql(sql, as_dict=True)[0].qty

@frappe.whitelist()
def get_anz_eingetroffen():
    sql = """
        SELECT
            COUNT(`name`) AS `qty`
        FROM `tabBeratung`
        WHERE `person_ist_eingetroffen` = 1
    """

    return frappe.db.sql(sql, as_dict=True)[0].qty

@frappe.whitelist()
def add_reservation(termin):
    frappe.db.set_value("APB Zuweisung", termin, {'reserved': 1, 'reserved_by': frappe.session.user})
    return

@frappe.whitelist()
def remove_reservation(termin):
    frappe.db.set_value("APB Zuweisung", termin, {'reserved': 0, 'reserved_by': None})
    return

@frappe.whitelist()
def person_ist_eingetroffen(beratung):
    frappe.db.set_value("Beratung", beratung, 'person_ist_eingetroffen', 1, update_modified=False)
    return
