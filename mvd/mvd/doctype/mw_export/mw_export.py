# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

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
            query = """/* {0} */\nWHERE `status_c` NOT IN ('Inaktiv', 'Interessent*in', 'Anmeldung', 'Online-Anmeldung')\nAND `m_und_w_export` != '{1}'\nAND {2}\n/*----------*/""".format(self.query_titel or 'QUERY', self.name, "\nAND".join(query_list))
            
            # Hinzufügen des Queries zum Datensatz
            if self.einzel_queries:
                self.einzel_queries += """\n\n""" + query
            else:
                self.einzel_queries = query
            
            # Zurücksetzen des Query Generators
            self.query_titel = None
            self.query_sektion_id = None
            self.query_region = None
            self.plz_von = 0
            self.plz_bis = 0
            
            self.save()
