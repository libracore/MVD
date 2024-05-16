# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import date, timedelta
from frappe.utils.data import getdate
from frappe import _

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
                                                    `as`.`ort` AS `art_ort`,
                                                    `tk`.`dispositions_hinweis`
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
        einteilung_list = []
        dispositions_hinweise = {}
        dispositions_hinweise_txt = ""

        while start_date <= end_date:
            beratungspersonen = get_beratungspersonen(start_date.weekday(), self.sektion_id)
            if beratungspersonen:
                for beratungsperson in beratungspersonen:
                    x = {}
                    x['date'] = start_date.strftime("%Y-%m-%d")
                    x['from_time'] = beratungsperson.from_time
                    x['to_time'] = beratungsperson.to_time
                    x['art_ort'] = beratungsperson.art_ort
                    x['beratungsperson'] = beratungsperson.beratungsperson
                    einteilung_list.append(x)
                    if beratungsperson.beratungsperson not in dispositions_hinweise:
                        if beratungsperson.dispositions_hinweis:
                            dispositions_hinweise[beratungsperson.beratungsperson] = beratungsperson.dispositions_hinweis
            start_date += delta
        
        sorted_einteilung_list = sorted(einteilung_list, key = lambda x: (x['art_ort'], x['date'], x['from_time']))

        for eintrag in sorted_einteilung_list:
            row = self.append('einteilung', {})
            row.date = eintrag['date']
            row.from_time = eintrag['from_time']
            row.to_time = eintrag['to_time']
            row.art_ort = eintrag['art_ort']
            row.beratungsperson = eintrag['beratungsperson']
        
        for key in dispositions_hinweise:
            dispositions_hinweise_txt += "{0}: {1}\n".format(key, dispositions_hinweise[key])
        self.dispositions_hinweis = dispositions_hinweise_txt
        
        self.save()

@frappe.whitelist()
def zeige_verfuegbarkeiten(sektion, datum, beraterin=None, ort=None):
    von_datum = getdate(datum)
    delta = timedelta(days=1)
    bis_datum = von_datum + timedelta(days=7)
    beraterin_filter = ''
    ort_filter = ''
    verfuegbarkeiten_html = ""
    if beraterin and beraterin != '':
        beraterin_filter = '''AND `beratungsperson` = '{0}' '''.format(beraterin)
    if ort and ort != '' and ort != ' ':
        ort_filter = '''AND `art_ort` = '{0}' '''.format(ort)
    
    while von_datum <= bis_datum:
        zugeteilte_beratungspersonen = frappe.db.sql("""
                                                        SELECT *
                                                        FROM `tabAPB Zuweisung`
                                                        WHERE `date` = '{von_datum}'
                                                        {beraterin_filter}
                                                        {ort_filter}
                                                    """.format(von_datum=von_datum.strftime("%Y-%m-%d"), beraterin_filter=beraterin_filter, ort_filter=ort_filter), as_dict=True)
        verfuegbarkeiten_html += """
            <p><b>{wochentag}, {datum}</b></p>
        """.format(wochentag=_(von_datum.strftime('%A')), datum=von_datum.strftime('%d.%m.%y'))
        if len(zugeteilte_beratungspersonen) > 0:
            zugeteilte_beratungspersonen_liste = []
            for zugeteilte_beratungsperson in zugeteilte_beratungspersonen:
                x = {
                    'ort': zugeteilte_beratungsperson.art_ort.replace("({sektion})".format(sektion=sektion), ""),
                    'from_time': zugeteilte_beratungsperson.from_time,
                    'to_time': zugeteilte_beratungsperson.to_time,
                    'beratungsperson': zugeteilte_beratungsperson.beratungsperson.replace("({sektion})".format(sektion=sektion), "")
                }
                zugeteilte_beratungspersonen_liste.append(x)
            sorted_list = sorted(zugeteilte_beratungspersonen_liste, key = lambda x: (x['ort'], x['from_time'], x['beratungsperson']))
            for entry in sorted_list:
                verfuegbarkeiten_html += """
                    <p>{from_time} - {to_time} / {ort} / {beratungsperson}</p>
                """.format(from_time=':'.join(str(entry['from_time']).split(':')[:2]), \
                           to_time=':'.join(str(entry['to_time']).split(':')[:2]), \
                            ort=entry['ort'], beratungsperson=entry['beratungsperson'])
        else:
            verfuegbarkeiten_html += """<p>Kein(e) Berater*in verfügbar</p>"""
        von_datum += delta
    
    return verfuegbarkeiten_html