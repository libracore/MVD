# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Beratung(Document):
    pass

@frappe.whitelist()
def verknuepfen(beratung, verknuepfung):
    multiselect = frappe.get_doc({
        'doctype': 'Beratung Multiselect',
        'parentfield': 'verknuepfungen',
        'parenttype': 'Beratung',
        'parent': beratung,
        'beratung': verknuepfung
    }).insert()

@frappe.whitelist()
def verknuepfung_entfernen(beratung, verknuepfung):
    multiselects = frappe.db.sql("""SELECT
                                        `name`
                                    FROM `tabBeratung Multiselect`
                                    WHERE `parentfield` = 'verknuepfungen'
                                    AND `parenttype` = 'Beratung'
                                    AND `parent` = '{beratung}'
                                    AND `beratung` = '{verknuepfung}'""".format(beratung=beratung, verknuepfung=verknuepfung), as_dict=True)
    for multiselect in multiselects:
        m = frappe.get_doc("Beratung Multiselect", multiselect.name)
        m.delete()

@frappe.whitelist()
def get_verknuepfungsuebersicht(beratung):
    verknuepfungen = frappe.db.sql("""SELECT
                                            *
                                        FROM `tabBeratung`
                                        WHERE `name` IN (
                                            SELECT `beratung`
                                            FROM `tabBeratung Multiselect`
                                            WHERE `parent` = '{beratung}'
                                        )""".format(beratung=beratung), as_dict=True)
    table = """<table style="width: 100%;">
                    <thead>
                        <tr>
                            <th>Datum</th>
                            <th>Priorität</th>
                            <th>Status</th>
                            <th>Kontaktperson</th>
                            <th>Beratungskategorie</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>"""
    
    for verknuepfung in verknuepfungen:
        table += """<tr>
                        <td>{0}</td>
                        <td>{1}</td>
                        <td>{2}</td>
                        <td>{3}</td>
                        <td>{4}</td>
                        <td><i class="fa fa-trash"></i></td>
                    </tr>""".format(frappe.utils.get_datetime(verknuepfung.start_date).strftime('%d.%m.%Y'), \
                                    verknuepfung.beratung_prio or '-', verknuepfung.status, verknuepfung.kontaktperson or '-', verknuepfung.beratungskategorie or '-')
    
    table += """</tbody>
                </table>"""
    
    return table
