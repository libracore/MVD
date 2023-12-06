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
                ['''`monday_from` AS `from_time`, `monday_to` AS `to_time`''', '''AND `monday` = 1'''],
                ['''`tuesday_from` AS `from_time`, `tuesday_to` AS `to_time`''', '''AND `tuesday` = 1'''],
                ['''`wednesday_from` AS `from_time`, `wednesday_to` AS `to_time`''', '''AND `wednesday` = 1'''],
                ['''`thursday_from` AS `from_time`, `thursday_to` AS `to_time`''', '''AND `thursday` = 1'''],
                ['''`friday_from` AS `from_time`, `friday_to` AS `to_time`''', '''AND `friday` = 1'''],
                ['''`saturday_from` AS `from_time`, `saturday_to` AS `to_time`''', '''AND `saturday` = 1'''],
                ['''`sunday_from` AS `from_time`, `sunday_to` AS `to_time`''', '''AND `sunday` = 1'''],
            ]
            beratungspersonen = frappe.db.sql("""SELECT
                                                    `name`,
                                                    {selections}
                                                from `tabTermin Kontaktperson`
                                                WHERE `sektion_id` = '{sektion}'
                                                AND `disabled` != 1
                                                {wheres}""".format(selections=weekday_query[weekday][0], \
                                                                    sektion=sektion, \
                                                                    wheres=weekday_query[weekday][1]), as_dict=True)
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
                    row.beratungsperson = beratungsperson.name
            start_date += delta
        
        self.save()

@frappe.whitelist()
def zeige_verfuegbarkeiten(sektion, datum):
    von_datum = getdate(datum)
    delta = timedelta(days=1)
    bis_datum = von_datum + timedelta(days=7)
    beratungspersonen = ""
    
    while von_datum <= bis_datum:
        zugeteilte_beratungspersonen = frappe.db.sql("""
                                                        SELECT *
                                                        FROM `tabAPB Zuweisung`
                                                        WHERE `date` = '{von_datum}'
                                                    """.format(von_datum=von_datum.strftime("%Y-%m-%d")), as_dict=True)
        if len(zugeteilte_beratungspersonen) > 0:
            for zugeteilte_beratungsperson in zugeteilte_beratungspersonen:
                beratungspersonen += bereinigt_mit_erfassten_termine(zugeteilte_beratungsperson, von_datum)
        von_datum += delta
    
    return beratungspersonen

def bereinigt_mit_erfassten_termine(beratungsperson, datum):
    # ~ erfasste_termine = [] # muss eine sql abfrage werden
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
        return_html = "{0} ({1} - {2}): {3}<br>".format(getdate(beratungsperson.date).strftime("%d.%m.%Y"), \
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
        # ~ return '' # muss durch bereinigung ersetzt werden
    else:
        return "{0} ({1} - {2}): {3}<br>".format(getdate(beratungsperson.date).strftime("%d.%m.%Y"), \
                                                        beratungsperson.from_time, \
                                                        beratungsperson.to_time, \
                                                        beratungsperson.beratungsperson)
