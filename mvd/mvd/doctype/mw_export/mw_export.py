# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import add_days, today, now
from frappe.utils.csvutils import to_csv as make_csv
from frappe.utils.background_jobs import enqueue

class MWExport(Document):
    def validate(self):
        if not self.sprach_reset:
            self.language = ''
            self.sprach_reset = 1
        
        zeitungsauflage_query = """SELECT
            `sektion_id` AS `sektion`,
            COALESCE(`region`, '') AS `region`,
            SUM(CASE WHEN COALESCE(`m_und_w`, 0) > 0 THEN 1 ELSE 0 END) AS `aktiv`,
            SUM(CASE WHEN COALESCE(`m_und_w`, 0) < 1 THEN 1 ELSE 0 END) AS `inaktiv`,
            SUM(CASE WHEN COALESCE(`m_und_w`, 0) > 5 THEN COALESCE(`m_und_w`, 0) ELSE 0 END) AS `anzahl_5`,
            SUM(COALESCE(`m_und_w`, 0)) AS `anzahl`
        FROM `tabMitgliedschaft`
        WHERE 
            (
                `status_c` NOT IN ('Inaktiv', 'Interessent*in', 'Anmeldung', 'Online-Anmeldung')
                OR
                `status_c` = 'Interessent*in' AND `interessent_typ` = 'M+W'
            )
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
            not_allow_key_words = ['drop', 'update', 'alter', 'delete', 'insert', 'create']
            for not_allowed in not_allow_key_words:
                if not_allowed.upper() in zeitungsauflage_query.upper():
                    frappe.throw("Unerlaubtes Query!")
            zeitungsauflagen = frappe.db.sql(zeitungsauflage_query, as_dict=True)
            zwischentotal = 0
            sektion = None
            add_zwischentotal = False
            for za in zeitungsauflagen:
                if sektion:
                    if sektion == za.sektion:
                        zwischentotal += za.anzahl
                        add_zwischentotal = False
                    else:
                        add_zwischentotal = True
                else:
                    sektion = za.sektion
                    zwischentotal = za.anzahl
                if add_zwischentotal:
                    zeitungsauflage += """
                        <tr>
                            <td><b>{0}</b></td>
                            <td></td>
                            <td></td>
                            <td></td>
                            <td></td>
                            <td><b>{1}</b></td>
                        </tr>
                    """.format(sektion, int(zwischentotal))
                    zwischentotal = za.anzahl
                    sektion = za.sektion
                
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
                    <tr>
                        <td><b>{0}</b></td>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td><b>{1}</b></td>
                    </tr>
                """.format(sektion, int(zwischentotal))
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
        or self.plz_bis \
        or self.language:
            # Erstelle Query Liste
            query_list = []
            
            if self.query_sektion_id:
                query_list.append("""`sektion_id` = '{0}'""".format(self.query_sektion_id))
            
            if self.query_region:
                query_list.append("""`region` = '{0}'""".format(self.query_region))
            
            if self.language:
                query_list.append("""`language` = '{0}'""".format(self.language))
            
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
            self.language = None
            
            self.save()
    
    def export_queries(self):
        args = {
            'self': self
        }
        enqueue("mvd.mvd.doctype.mw_export.mw_export.bg_export_queries", queue='long', job_name='Export Queries {0}'.format(self.name), timeout=5000, **args)

def bg_export_queries(self):
    try:
        # Einzelqueries
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
        
        # Rest
        csv_data = get_csv_data(self.name)

        csv_file = make_csv(csv_data)

        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": "Rest_{datetime}.csv".format(datetime=now().replace(" ", "_")),
            "folder": "Home/Attachments",
            "is_private": 1,
            "content": csv_file,
            "attached_to_doctype": 'MW Export',
            "attached_to_name": self.name
        })
        _file.save()
        
        self.db_set('status', 'Abgeschlossen', commit=True)
    except Exception as err:
        self.add_comment('Comment', text=str(err))
        self.db_set('status', 'Fehlgeschlagen', commit=True)

def get_csv_data(mw_export, query=False):
    data = []
    titel = [
        'mitglied_nr',
        'anrede',
        'name_1',
        'name_2',
        'name_3',
        'strasse_pf',
        'plz_4',
        'ort',
        'anzahl',
        'sektion',
        'region_c'
    ]
    data.append(titel)
    
    query_filter = ''
    if query:
        query_filter = "AND " + query.replace("\n", " AND")
    query_data = frappe.db.sql("""SELECT
                                    `name`,
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
                                    `region`,
                                    `kundentyp`,
                                    `firma`,
                                    `zusatz_adresse`
                                FROM `tabMitgliedschaft`
                                WHERE (
                                    `status_c` NOT IN ('Inaktiv', 'Interessent*in', 'Anmeldung', 'Online-Anmeldung')
                                    OR
                                    `status_c` = 'Interessent*in' AND `interessent_typ` = 'M+W'
                                )
                                AND IFNULL(`m_und_w_export`, '') != '{mw_export}'
                                AND IFNULL(`m_und_w`, 0) > 0
                                {query}""".format(mw_export=mw_export, query=query_filter), as_dict=True, debug=True)
    if len(query_data) > 0:
        for entry in query_data:
            mitglied_nr = entry.mitglied_nr
            
            anrede = ''
            if not entry.nachname_2:
                anrede = entry.anrede_c
            
            if entry.kundentyp == 'Unternehmen':
                name_1 = entry.firma or ''
                name_2 = " ".join([entry.vorname_1 or '', entry.nachname_1 or ''])
            else:
                name_1 = " ".join([entry.vorname_1 or '', entry.nachname_1 or ''])
                name_2 = " ".join([entry.vorname_2 or '', entry.nachname_2 or ''])
            if entry.zusatz_adresse:
                name_2 = entry.zusatz_adresse
            
            name_3 = " ".join([entry.rg_vorname or '', entry.rg_nachname or ''])
            
            strasse_pf = " ".join([entry.strasse if not int(entry.postfach) == 1 else 'Postfach', entry.nummer + entry.nummer_zu or '' if not int(entry.postfach) == 1 else entry.postfach_nummer or ''])
            plz_6 = entry.plz
            ort = entry.ort
            anzahl = entry.m_und_w
            sektion_c = entry.sektion_id
            
            if entry.region:
                region_c = frappe.db.get_value("Region", entry.region, 'region_c')
            else:
                region_c = ''
            
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
            
            frappe.db.set_value("Mitgliedschaft", entry.name, "m_und_w_export", mw_export, update_modified=False)

    return data
