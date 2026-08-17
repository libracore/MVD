# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import date, datetime
from frappe.utils import getdate
import requests

class Dokumentenvorlage(Document):
    def validate(self):
        for mapping in self.mapping_tbl:
            if mapping.replace_with == 'Feld':
                mapping.function = None
                if not mapping.field: frappe.throw('Bitte erfassen sie "Feld" in Zeile {idx}'.format(idx=mapping.idx))
            if mapping.replace_with == 'Funktion':
                mapping.field = None
                
                if mapping.function == 'Mail-In DMC':
                    mapping.platzhalter = 'dmc_platzhalter'
                
                if not mapping.function: frappe.throw('Bitte erfassen sie "Funktion" in Zeile {idx}'.format(idx=mapping.idx))
        return
    
    def translate(self):
        mapping_tbl = self.mapping_tbl
        if self.mapping_vorlage:
            mapping_vorlage = frappe.get_doc("Dokumentenvorlage Mapping", self.mapping_vorlage)
            mapping_tbl = mapping_vorlage.mapping_tbl
        
        return {
            row.platzhalter: {
                "doctype": row.d_type,
                "fieldname": row.field,
                "replace_with": row.replace_with,
                "function": row.function,
                "subject": row.subject
            }
            for row in sorted(
                mapping_tbl,
                key=lambda row: len(row.platzhalter),
                reverse=True
            )
            if row.platzhalter and row.d_type and (row.replace_with == 'Feld' and row.field) or (row.replace_with == 'Funktion' and row.function)
        }

    def format_value(self, value, doctype, fieldname):
        if value is None:
            return ""

        meta = frappe.get_meta(doctype)
        df = meta.get_field(fieldname)

        if df and df.fieldtype in ("Date", "Datetime"):
            if isinstance(value, (date, datetime)):
                return value.strftime("%d.%m.%Y")

            return getdate(value).strftime("%d.%m.%Y")

        return str(value)

    def get_placeholder_values(self, doc):
        result = {}
        translations = self.translate()

        meta = frappe.get_meta(doc.doctype)

        link_fields_by_doctype = {}

        for df in meta.fields:
            if df.fieldtype == "Link" and df.options:
                link_fields_by_doctype[df.options] = df.fieldname

        for placeholder, config in translations.items():
            replace_with = config.get("replace_with")
            replace_function = config.get("function")
            target_doctype = config.get("doctype")
            target_fieldname = config.get("fieldname")

            if replace_with == "Feld":
                # Feld ist direkt auf dem aktuellen Dokument
                if target_doctype == doc.doctype:
                    value = doc.get(target_fieldname)
                    result[placeholder] = ['txt', self.format_value(
                        value,
                        target_doctype,
                        target_fieldname
                    )]
                    continue

                # Feld kommt von einem verknuepften Dokument
                link_fieldname = link_fields_by_doctype.get(target_doctype)

                if not link_fieldname:
                    result[placeholder] = ['txt', ""]
                    continue

                linked_docname = doc.get(link_fieldname)

                if not linked_docname:
                    result[placeholder] = ['txt', ""]
                    continue

                value = frappe.db.get_value(
                    target_doctype,
                    linked_docname,
                    target_fieldname
                )

                result[placeholder] = ['txt', self.format_value(
                    value,
                    target_doctype,
                    target_fieldname
                )]
            if replace_with == "Funktion":
                if replace_function == "Mail-In DMC":
                    result[placeholder] = ['img', get_dmc_png(doc.doctype, doc.name, config.get("subject"))]

        return result

@frappe.whitelist()
def get_doc_fields(doctype):
    return frappe.db.sql(
        """
            SELECT `fieldname`, `label`
            FROM `tabDocField`
            WHERE `parenttype` = "DocType"
            AND `parent` = '{0}'
            ORDER BY `fieldname` ASC;
        """.format(doctype),
        as_dict=True
    )

def get_dmc_png(dt, dn, subject=''):
    url = 'https://data.libracore.ch/phpqrcode/api/barcode.php'

    response = requests.get(url, params={
            "f": "png",
            "s": "dmtx",
            "d": "mailto:mv+{dn}+{dt}@libracore.io?subject={subject}".format(dn=dn, dt=dt, subject=subject),
            "h": 80,
            "w": 80,
        }, timeout=10)

    if response.status_code != 200:
        frappe.throw("DMC konnte nicht geladen werden: HTTP {0}".format(response.status_code))

    content_type = response.headers.get("Content-Type", "")
    if "image/png" not in content_type:
        frappe.throw("DMC-Endpunkt hat kein PNG zurückgegeben: {0}".format(content_type))

    return response.content