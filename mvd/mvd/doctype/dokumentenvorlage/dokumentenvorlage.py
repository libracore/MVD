# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Dokumentenvorlage(Document):
    def translate(self):
        return {
            row.platzhalter: {
                "doctype": row.d_type,
                "fieldname": row.field
            }
            for row in self.mapping_tbl
            if row.platzhalter and row.d_type and row.field
        }

    def get_placeholder_values(self, doc):
        result = {}
        translations = self.translate()

        meta = frappe.get_meta(doc.doctype)

        link_fields_by_doctype = {}

        for df in meta.fields:
            if df.fieldtype == "Link" and df.options:
                link_fields_by_doctype[df.options] = df.fieldname

        for placeholder, config in translations.items():
            target_doctype = config.get("doctype")
            target_fieldname = config.get("fieldname")

            # Feld ist direkt auf dem aktuellen Dokument
            if target_doctype == doc.doctype:
                result[placeholder] = doc.get(target_fieldname)
                continue

            # Feld kommt von einem verknuepften Dokument
            link_fieldname = link_fields_by_doctype.get(target_doctype)

            if not link_fieldname:
                result[placeholder] = None
                continue

            linked_docname = doc.get(link_fieldname)

            if not linked_docname:
                result[placeholder] = None
                continue

            result[placeholder] = frappe.db.get_value(
                target_doctype,
                linked_docname,
                target_fieldname
            )

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