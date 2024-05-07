# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import date, timedelta
from frappe.utils.data import getdate

class ArbeitsplanBeratung(Document):
    def validate(self):
        self.validate_date()
        self.validate_overlapping()
    
    def validate_date(self):
        if self.to_date < self.from_date:
            frappe.throw("Das Bis-Datum muss nach dem Von-Datum sein.")
    
    def validate_overlapping(self):
        overlapping = frappe.db.sql("""SELECT
                                            `name`
                                        FROM `tabArbeitsplan Beratung`
                                        WHERE `sektion_id` = '{sektion}'
                                        AND `name` != '{himself}'
                                        AND (
                                            `from_date` BETWEEN '{from_date}' AND '{to_date}'
                                            OR
                                            `to_date` BETWEEN '{from_date}' AND '{to_date}'
                                        )
                                        AND `docstatus` != 2
                                        """.format(sektion=self.sektion_id, \
                                                    from_date=self.from_date, \
                                                    to_date=self.to_date, \
                                                    himself=self.name), as_list=True)
        if len(overlapping) > 0:
            overlaps = ''
            for overlap in overlapping:
                overlaps += overlap[0] + "<br>"
            frappe.throw("Der Datumsbereich dieses Arbeitsplan überschneited sich mit:<br>{0}".format(overlaps))

    def get_personen(self):
        def get_beratungspersonen(weekday, sektion):
            weekday_query = [
                "Montag",
                "Dienstag",
                "Mittwoch",
                "Donnerstag",
                "Freitag",
                "Samstag",
                "Sonntag"
            ]
            beratungspersonen = frappe.db.sql("""SELECT
                                                    `as`.`parent` AS `beratungsperson`,
                                                    `as`.`from` AS `from_time`,
                                                    `as`.`to` AS `to_time`,
                                                    `as`.`ort` AS `art_ort`
                                                from `tabArbeitsplan Standardzeit` AS `as`
                                                LEFT JOIN `tabTermin Kontaktperson` AS `tk` ON `as`.`parent` = `tk`.`name`
                                                WHERE `tk`.`sektion_id` = '{sektion}'
                                                AND `tk`.`disabled` != 1
                                                AND `as`.`day` = '{weekday}'""".format(weekday=weekday_query[weekday], \
                                                                    sektion=sektion,), as_dict=True)
            if len(beratungspersonen) > 0:
                return beratungspersonen
            else:
                return False
        
        start_date = getdate(self.from_date)
        end_date = getdate(self.to_date)
        delta = timedelta(days=1)
        
        while start_date <= end_date:
            beratungspersonen = get_beratungspersonen(start_date.weekday(), self.sektion_id)
            if beratungspersonen:
                for beratungsperson in beratungspersonen:
                    row = self.append('einteilung', {})
                    row.date = start_date.strftime("%Y-%m-%d")
                    row.from_time = beratungsperson.from_time
                    row.to_time = beratungsperson.to_time
                    row.art_ort = beratungsperson.art_ort
                    row.beratungsperson = beratungsperson.beratungsperson
            start_date += delta
        
        self.save()

@frappe.whitelist()
def zeige_verfuegbarkeiten(sektion, datum, beraterin=None, art=None):
    von_datum = getdate(datum)
    delta = timedelta(days=1)
    bis_datum = von_datum + timedelta(days=7)
    beratungspersonen = ""
    beraterin_filter = ''
    art_filter = ''
    if beraterin and beraterin != '':
        beraterin_filter = '''AND `beratungsperson` = '{0}' '''.format(beraterin)
    if art and art != '':
        art_filter = '''AND `art` IN ('Ohne Einschränkung', '{0}') '''.format(art)
    
    while von_datum <= bis_datum:
        zugeteilte_beratungspersonen = frappe.db.sql("""
                                                        SELECT *
                                                        FROM `tabAPB Zuweisung`
                                                        WHERE `date` = '{von_datum}'
                                                        {beraterin_filter}
                                                        {art_filter}
                                                    """.format(von_datum=von_datum.strftime("%Y-%m-%d"), beraterin_filter=beraterin_filter, art_filter=art_filter), as_dict=True)
        if len(zugeteilte_beratungspersonen) > 0:
            for zugeteilte_beratungsperson in zugeteilte_beratungspersonen:
                beratungspersonen += bereinigt_mit_erfassten_termine(zugeteilte_beratungsperson, von_datum)
        von_datum += delta
    
    return beratungspersonen

def bereinigt_mit_erfassten_termine(beratungsperson, datum):
    erfasste_termine = frappe.db.sql("""
                                        SELECT
                                            `von`,
                                            `bis`,
                                            `parent`,
                                            `ort`,
                                            `art`
                                        FROM `tabBeratung Termin`
                                        WHERE `berater_in` = '{berater_in}'
                                        AND `von` BETWEEN '{datum} 00:00:00' AND '{datum} 23:59:59'
                                    """.format(berater_in=beratungsperson.beratungsperson, \
                                                datum=beratungsperson.date), as_dict=True)
    if len(erfasste_termine) > 0:
        return_html = "{0} / {1} ({2} - {3}): {4}<br>".format(getdate(beratungsperson.date).strftime("%d.%m.%Y"), \
                                                        beratungsperson.art_ort, \
                                                        beratungsperson.from_time, \
                                                        beratungsperson.to_time, \
                                                        beratungsperson.beratungsperson)
        for erfasster_termin in erfasste_termine:
            return_html += "--> {0} - {1}: {2}; {3} ({4})<br>".format(erfasster_termin.von.strftime("%H:%M:%S"), \
                                                            erfasster_termin.bis.strftime("%H:%M:%S"), \
                                                            erfasster_termin.art, \
                                                            erfasster_termin.ort, \
                                                            erfasster_termin.parent)
        
        return_html += "<br>"
        return return_html
    else:
        return "{0} / {1} ({2} - {3}): {4}<br>".format(getdate(beratungsperson.date).strftime("%d.%m.%Y"), \
                                                        beratungsperson.art_ort, \
                                                        beratungsperson.from_time, \
                                                        beratungsperson.to_time, \
                                                        beratungsperson.beratungsperson)
