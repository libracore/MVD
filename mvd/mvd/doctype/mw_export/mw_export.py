# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import add_days, today, now
from frappe.utils.csvutils import to_csv as make_csv

class MWExport(Document):
    def validate(self):
        zeitungsauflage_query = """SELECT
            `sektion_id` AS `sektion`,
            COALESCE(`region`, '') AS `region`,
            SUM(CASE WHEN COALESCE(`m_und_w`, 0) > 0 THEN 1 ELSE 0 END) AS `aktiv`,
            SUM(CASE WHEN COALESCE(`m_und_w`, 0) < 1 THEN 1 ELSE 0 END) AS `inaktiv`,
            SUM(CASE WHEN COALESCE(`m_und_w`, 0) > 5 THEN COALESCE(`m_und_w`, 0) ELSE 0 END) AS `anzahl_5`,
            SUM(COALESCE(`m_und_w`, 0)) AS `anzahl`
        FROM `tabMitgliedschaft`
        WHERE `status_c` NOT IN ('Inaktiv', 'Interessent*in', 'Anmeldung', 'Online-Anmeldung')
        GROUP BY `sektion_id`, COALESCE(`region`, '')"""
        if self.zeitungsauflage_query != zeitungsauflage_query.replace("        ", ""):
            if not self.zeitungsauflage_query or self.zeitungsauflage_query == '':
                self.zeitungsauflage_query = zeitungsauflage_query.replace("        ", "")
            else:
                zeitungsauflage_query = self.zeitungsauflage_query
            
            zeitungsauflage = """
                <table style="width: 100%;">
                    <thead>
                        <tr>
                            <th>Sektion</th>
                            <th>Region</th>
                            <th>Aktiv</th>
                            <th>Inaktiv</th>
                            <th>Werbeexemplare</th>
                            <th>Anzahl</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            zeitungsauflagen = frappe.db.sql(zeitungsauflage_query, as_dict=True)
            for za in zeitungsauflagen:
                zeitungsauflage += """
                    <tr>
                        <td>{0}</td>
                        <td>{1}</td>
                        <td>{2}</td>
                        <td>{3}</td>
                        <td>{4}</td>
                        <td>{5}</td>
                    </tr>
                """.format(za.sektion, za.region, int(za.aktiv), int(za.inaktiv), int(za.anzahl_5), int(za.anzahl))
            zeitungsauflage += """
                </tbody>
                </table>
            """
            self.zeitungsauflage_data = zeitungsauflage
    def query_hinzufuegen(self):
        # Prüfe ob Titel (aka Filename) vorhanden
        if not self.query_titel:
            frappe.throw("Bitte mindestens ein Query Titel angeben")
        
        # Prüfe ob Daten für Query vorhanden
        if self.query_sektion_id \
        or self.query_region \
        or self.plz_von \
        or self.plz_bis:
            # Erstelle Query Liste
            query_list = []
            
            if self.query_sektion_id:
                query_list.append("""`sektion_id` = '{0}'""".format(self.query_sektion_id))
            
            if self.query_region:
                query_list.append("""`region` = '{0}'""".format(self.query_region))
            
            if self.plz_von and self.plz_von > 0:
                if self.plz_bis and self.plz_bis > 0:
                    query_list.append("""`plz` BETWEEN {0} AND {1}""".format(self.plz_von, self.plz_bis))
                else:
                    query_list.append("""`plz` = {0}""".format(self.plz_von))
            
            # Zusammenführen der Queryliste zu einem Query
            query = """{0}""".format("\n".join(query_list))
            
            # Hinzufügen des Queries zum Datensatz
            row = self.append('einzelqueries', {})
            row.titel = self.query_titel
            row.query = query
            
            # Zurücksetzen des Query Generators
            self.query_titel = None
            self.query_sektion_id = None
            self.query_region = None
            self.plz_von = 0
            self.plz_bis = 0
            
            self.save()
    
    def export_queries(self):
        try:
            for query in self.einzelqueries:
                csv_data = get_csv_data(self.name, query.query)

                csv_file = make_csv(csv_data)

                _file = frappe.get_doc({
                    "doctype": "File",
                    "file_name": "{titel}_{datetime}.csv".format(titel=query.titel, datetime=now().replace(" ", "_")),
                    "folder": "Home/Attachments",
                    "is_private": 1,
                    "content": csv_file,
                    "attached_to_doctype": 'MW Export',
                    "attached_to_name": self.name
                })
                _file.save()
            self.status = 'Abgeschlossen'
            self.save()
        except Exception as err:
            self.add_comment('Comment', text=str(err))
            self.status = 'Fehlgeschlagen'
            self.save()

def get_csv_data(mw_export, query):
    data = []
    titel = [
        'mitglied_nr',
        'anrede',
        'name_1',
        'name_2',
        'name_3',
        'strasse_pf',
        'plz_6',
        'ort',
        'anzahl',
        'sektion_c',
        'region_c'
    ]
    data.append(titel)
    
    query_data = frappe.db.sql("""SELECT
                                    `mitglied_nr`,
                                    `anrede_c`,
                                    `vorname_1`,
                                    `nachname_1`,
                                    `vorname_2`,
                                    `nachname_2`,
                                    `rg_vorname`,
                                    `rg_nachname`,
                                    `strasse`,
                                    `nummer`,
                                    `nummer_zu`,
                                    `postfach`,
                                    `postfach_nummer`,
                                    `plz`,
                                    `ort`,
                                    `m_und_w`,
                                    `sektion_id`,
                                    `region`
                                FROM `tabMitgliedschaft`
                                WHERE `status_c` NOT IN ('Inaktiv', 'Interessent*in', 'Anmeldung', 'Online-Anmeldung')
                                /*AND `m_und_w_export` != '{mw_export}'*/
                                AND `m_und_w` > 0
                                AND {query}""".format(mw_export=mw_export, query=query.replace("\n", " AND")), as_dict=True)
    if len(query_data) > 0:
        for entry in query_data:
            mitglied_nr = entry.mitglied_nr
            anrede = entry.anrede_c
            name_1 = " ".join([entry.vorname_1 or '', entry.nachname_1 or ''])
            name_2 = " ".join([entry.vorname_2 or '', entry.nachname_2 or ''])
            name_3 = " ".join([entry.rg_vorname or '', entry.rg_nachname or ''])
            strasse_pf = " ".join([entry.strasse if not int(entry.postfach) == 1 else 'Postfach', entry.nummer + entry.nummer_zu or '' if not int(entry.postfach) == 1 else entry.postfach_nummer or ''])
            plz_6 = entry.plz
            ort = entry.ort
            anzahl = entry.m_und_w
            sektion_c = entry.sektion_id
            region_c = entry.region or ''
            
            _data = [
                mitglied_nr,
                anrede,
                name_1,
                name_2,
                name_3,
                strasse_pf,
                plz_6,
                ort,
                anzahl,
                sektion_c,
                region_c
            ]
            data.append(_data)

    return data
