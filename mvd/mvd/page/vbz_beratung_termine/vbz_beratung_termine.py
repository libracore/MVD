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
def get_open_data(
    free_only=0,
    beratungsort=None,
    berater_in=None,
    art=None,
    datum=None,
    language=None,
    fachskill=None,
    my_reservations_only=0,
    beratungstyp=None,
    termine_heute=0,
    termine_gebucht=0,
    datum_bis=None,
    chronologische_termine=0,
    geschaeftsstelle=None):

    # Entferne Platzhalter Werte
    if geschaeftsstelle == "Geschäftsstelle": geschaeftsstelle = None
    if beratungstyp == "Beratungstyp": beratungstyp = None
    if art == "Art": art = None

    alle_termine, meine_termine = get_alle_beratungs_termine(frappe.session.user, free_only, beratungsort,
                                                                               berater_in, art, datum, language, fachskill,
                                                                               my_reservations_only, beratungstyp, termine_heute,
                                                                               termine_gebucht, datum_bis, chronologische_termine,
                                                                               geschaeftsstelle)
    datasets = {
        'datenstand_as': now_datetime().strftime("%d.%m.%Y %H:%M:%S"),
        'alle_termine': alle_termine,
        'meine_termine': meine_termine
    }
    return datasets

def get_alle_beratungs_termine(
    user, free_only=0,
    beratungsort=None,
    berater_in=None,
    art=None,
    datum=None,
    language=None,
    fachskill=None,
    my_reservations_only=0,
    beratungstyp=None,
    termine_heute=0,
    termine_gebucht=0,
    datum_bis=None,
    chronologische_termine=0,
    geschaeftsstelle=None):

    alle = []
    meine = []
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

    geschaeftsstelle_filter = ''
    if geschaeftsstelle and geschaeftsstelle != '':
        geschaeftsstelle_filter = "AND (`bo`.`geschaeftsstelle` = '{0}' OR `bo`.`geschaeftsstelle` IS NULL)".format(geschaeftsstelle)
    
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
                                        LEFT JOIN `tabBeratungsort` AS `bo` ON `berTer`.`ort` = `bo`.`name`
                                        WHERE
                                        {datum_filter}
                                        {beratungsort_filter}
                                        {berater_in_filter}
                                        {art_filter}
                                        {fachskill_filter}
                                        {sprach_filter}
                                        {beratungstyp_filter}
                                        {geschaeftsstelle_filter}
                                        ORDER BY `berTer`.`von` DESC
                                    """.format(
                                            datum_filter=datum_filter,
                                            beratungsort_filter=beratungsort_filter,
                                            berater_in_filter=berater_in_filter,
                                            art_filter=art_filter,
                                            fachskill_filter=fachskill_filter,
                                            sprach_filter=sprach_filter,
                                            beratungstyp_filter=beratungstyp_filter,
                                            geschaeftsstelle_filter=geschaeftsstelle_filter),
                                    as_dict=True)
        # --------------------------------------------------------------------------
        # Daten fuer alle Termine gesammelt laden.
        #
        # Vorher wurden Beratungsdateien, Mitgliedschaften und Kunden innerhalb
        # der Schleife einzeln aus der DB gelesen. Bei 100 Terminen konnten dadurch
        # >100 zusaetzliche Queries entstehen.
        # --------------------------------------------------------------------------

        beratung_namen = list(set([
            termin.parent
            for termin in alle_termine
            if termin.parent
        ]))

        mitgliedschaft_namen = list(set([
            termin.mv_mitgliedschaft
            for termin in alle_termine
            if termin.mv_mitgliedschaft
        ]))

        kunden_namen = list(set([
            termin.faktura_kunde
            for termin in alle_termine
            if termin.faktura_kunde
        ]))


        # Beratungen mit Attachments
        beratungen_mit_attachment = set()

        if beratung_namen:
            placeholders = ", ".join(["%s"] * len(beratung_namen))

            rows = frappe.db.sql("""
                SELECT DISTINCT `parent`
                FROM `tabBeratungsdateien`
                WHERE `parent` IN ({0})
            """.format(placeholders), tuple(beratung_namen))

            beratungen_mit_attachment = set([
                row[0] for row in rows
            ])


        # Mitgliedschaften
        mitgliedschaften = {}

        if mitgliedschaft_namen:
            placeholders = ", ".join(["%s"] * len(mitgliedschaft_namen))

            rows = frappe.db.sql("""
                SELECT
                    `name`,
                    `vorname_1`,
                    `nachname_1`,
                    `status_c`
                FROM `tabMitgliedschaft`
                WHERE `name` IN ({0})
            """.format(placeholders), tuple(mitgliedschaft_namen), as_dict=True)

            mitgliedschaften = dict([
                (row.name, row)
                for row in rows
            ])


        # Kunden
        kunden = {}

        if kunden_namen:
            placeholders = ", ".join(["%s"] * len(kunden_namen))

            rows = frappe.db.sql("""
                SELECT
                    `name`,
                    `vorname`,
                    `nachname`
                FROM `tabKunden`
                WHERE `name` IN ({0})
            """.format(placeholders), tuple(kunden_namen), as_dict=True)

            kunden = dict([
                (row.name, row)
                for row in rows
            ])
        
        for termin in alle_termine:
            termin_data = None
            if not erlaubte_sektionen or termin.sektion_id in erlaubte_sektionen:
                if not erb_block or termin.berater_in in kontaktperson_multi_user:
                    hat_attachement = (
                        1 if termin.parent in beratungen_mit_attachment else 0
                    )

                    vorname = ""
                    nachname = ""
                    status_c = ""
                    link = "#"

                    if termin.mv_mitgliedschaft:
                        m_daten = mitgliedschaften.get(
                            termin.mv_mitgliedschaft
                        )

                        vorname = m_daten.get("vorname_1") if m_daten else ""
                        nachname = m_daten.get("nachname_1") if m_daten else ""
                        status_c = m_daten.get("status_c") if m_daten else ""

                        link = "/desk#Form/Mitgliedschaft/{0}".format(
                            termin.mv_mitgliedschaft
                        )
                    elif termin.faktura_kunde:
                        k_daten = kunden.get(
                            termin.faktura_kunde
                        )

                        vorname = k_daten.get("vorname") if k_daten else ""
                        nachname = k_daten.get("nachname") if k_daten else ""
                        status_c = "Kunde"

                        link = "/desk#Form/Kunden/{0}".format(
                            termin.faktura_kunde
                        )
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
                        'terminkategorie': termin.terminkategorie,
                        'sektion_id': termin.sektion_id
                    }
                    
                    if not cint(free_only) == 1:
                        alle.append(termin_data)
            if termin_data and termin.berater_in in kontaktperson_multi_user:
                meine.append(termin_data)
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

        geschaeftsstelle_filter = ''
        if geschaeftsstelle and geschaeftsstelle != '':
            geschaeftsstelle_filter = "AND (`beratungsort`.`geschaeftsstelle` = '{0}' OR `beratungsort`.`geschaeftsstelle` IS NULL)".format(geschaeftsstelle)
        
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
                                        `kp`.`sektion_id` AS `sektion_id`,
                                        NULL AS `is_business`
                                    FROM `tabAPB Zuweisung` AS `zuw`
                                    LEFT JOIN `tabBeratungsort` AS `beratungsort` ON `zuw`.`art_ort` = `beratungsort`.`name`
                                    LEFT JOIN `tabTermin Kontaktperson` AS `kp` ON `zuw`.`beratungsperson` = `kp`.`name`
                                    WHERE NOT EXISTS (
                                        SELECT 1
                                        FROM `tabBeratung Termin` AS `vergeben`
                                        WHERE `vergeben`.`abp_referenz` = `zuw`.`name`
                                    )
                                    {datum_filter}
                                    {beratungsort_filter}
                                    {berater_in_filter}
                                    {fachskill_filter}
                                    {sprach_filter}
                                    {beratungstyp_filter}
                                    {art_filter}
                                    {geschaeftsstelle_filter}
                                    """.format(
                                        datum_filter=datum_filter,
                                        beratungsort_filter=beratungsort_filter,
                                        berater_in_filter=berater_in_filter,
                                        fachskill_filter=fachskill_filter,
                                        sprach_filter=sprach_filter,
                                        beratungstyp_filter=beratungstyp_filter,
                                        art_filter=art_filter,
                                        geschaeftsstelle_filter=geschaeftsstelle_filter),
                                    as_dict=True)
        
        for freier_termin in freie_termine:
            freier_termin.von = frappe.utils.get_datetime(freier_termin.von)
            freier_termin.bis = frappe.utils.get_datetime(freier_termin.bis)
            freier_termin.von_date = get_datetime(freier_termin.von).strftime('%d.%m.%Y')
            freier_termin.von_time = get_datetime(freier_termin.von).strftime('%H:%M')
            freier_termin.bis_time = get_datetime(freier_termin.bis).strftime('%H:%M')
            freier_termin.wochentag = _(get_datetime(freier_termin.von).strftime('%A'))[:2]
            freier_termin.sort_date = frappe.utils.getdate(freier_termin.von)
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
    
    return alle_sortiert, meine

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

@frappe.whitelist()
def get_polling_state():
    """
    Sehr günstiger Endpoint für das 2-Sekunden-Polling.

    Wichtig:
    person_ist_eingetroffen() verwendet update_modified=False.
    Deshalb reicht MAX(modified) von tabBeratung alleine nicht aus.
    Die Anzahl eingetroffener Personen wird separat berücksichtigt.
    """

    state = frappe.db.sql("""
        SELECT
            (SELECT MAX(`modified`)
             FROM `tabBeratung`) AS `beratung_modified`,

            (SELECT MAX(`modified`)
             FROM `tabBeratung Termin`) AS `termin_modified`,

            (SELECT MAX(`modified`)
             FROM `tabAPB Zuweisung`) AS `zuweisung_modified`,

            (SELECT MAX(`modified`)
             FROM `tabBeratungsdateien`) AS `dateien_modified`,

            (SELECT COUNT(`name`)
             FROM `tabBeratung`
             WHERE `person_ist_eingetroffen` = 1) AS `anz_eingetroffen`
    """, as_dict=True)[0]

    return {
        "beratung_modified": str(state.beratung_modified or ""),
        "termin_modified": str(state.termin_modified or ""),
        "zuweisung_modified": str(state.zuweisung_modified or ""),
        "dateien_modified": str(state.dateien_modified or ""),
        "anz_eingetroffen": state.anz_eingetroffen or 0
    }