# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint


DOCTYPE = "Vorlagen Baum"


@frappe.whitelist()
def get_children(parent_name=None, sektion_id=None):
    if not frappe.has_permission(DOCTYPE, "read"):
        frappe.throw(_("Keine Leseberechtigung für {0}").format(DOCTYPE))

    filters = {}

    if parent_name:
        filters["parent_vorlagen_baum"] = parent_name
    else:
        filters["parent_vorlagen_baum"] = ["in", ["", None]]

    if sektion_id:
        filters["sektion_id"] = sektion_id

    rows = frappe.get_all(
        DOCTYPE,
        filters=filters,
        fields=[
            "name",
            "vorlagen_baum_name",
            "is_group",
            "sektion_id",
            "parent_vorlagen_baum",
            "use_for_email",
            "use_for_druckvorlagen",
            "use_for_dokumentenvorlagen"
        ],
        order_by="vorlagen_baum_name asc"
    )

    result = []
    for row in rows:
        result.append({
            "name": row.name,
            "label": row.vorlagen_baum_name or row.name,
            "is_group": cint(row.is_group),
            "sektion_id": row.sektion_id,
            "parent": row.parent_vorlagen_baum,
            "use_for_email": cint(row.use_for_email),
            "use_for_druckvorlagen": cint(row.use_for_druckvorlagen),
            "use_for_dokumentenvorlagen": cint(row.use_for_dokumentenvorlagen)
        })

    return result


@frappe.whitelist()
def get_node_details(node_name):
    if not frappe.has_permission(DOCTYPE, "read"):
        frappe.throw(_("Keine Leseberechtigung für {0}").format(DOCTYPE))

    doc = frappe.get_doc(DOCTYPE, node_name)

    result = {
        "name": doc.name,
        "label": doc.vorlagen_baum_name or doc.name,
        "sektion_id": doc.sektion_id,
        "is_group": cint(doc.is_group),
        "use_for_email": cint(doc.use_for_email),
        "use_for_druckvorlagen": cint(doc.use_for_druckvorlagen),
        "use_for_dokumentenvorlagen": cint(doc.use_for_dokumentenvorlagen),
        "email_vorlagen": [],
        "druckvorlagen": [],
        "dokumentenvorlagen": []
    }

    # Child Table: E-Mail Vorlagen
    for row in doc.get("email_vorlagen") or []:
        result["email_vorlagen"].append(_serialize_child_row(row))

    # Child Table: Druckvorlagen
    for row in doc.get("druckvorlagen") or []:
        result["druckvorlagen"].append(_serialize_child_row(row))

    # Child Table: Dokumentenvorlagen
    for row in doc.get("dokumentenvorlagen") or []:
        result["dokumentenvorlagen"].append(_serialize_child_row(row))

    return result


def _serialize_child_row(row):
    data = {
        "name": row.name,
        "doctype": row.doctype
    }

    # Alle Felder der Child-Row mitgeben, damit das Frontend flexibel für die Zukunft bleibt
    for fieldname, value in row.as_dict().items():
        if fieldname not in data:
            data[fieldname] = value

    # Versuch Link-Felder zu erkennen
    meta = frappe.get_meta(row.doctype)
    link_fields = []

    for df in meta.fields:
        if df.fieldtype == "Link":
            link_fields.append({
                "fieldname": df.fieldname,
                "label": df.label,
                "options": df.options,
                "value": row.get(df.fieldname)
            })

    data["_link_fields"] = link_fields
    return data

@frappe.whitelist()
def search_nodes(query, sektion_id=None, purpose=None, limit=30):
    query = (query or "").strip()
    limit = cint(limit) or 30

    if not query:
        return []

    if not frappe.has_permission(DOCTYPE, "read"):
        frappe.throw(_("Keine Leseberechtigung für {0}").format(DOCTYPE))

    results = []
    seen = set()

    def add_node(node_name, match_type="node", match_label="Knoten", match_value=None):
        if not node_name:
            return

        key = (node_name, match_type, match_value)
        if key in seen:
            return

        doc = frappe.get_doc(DOCTYPE, node_name)

        if sektion_id and doc.sektion_id != sektion_id:
            return

        results.append({
            "name": doc.name,
            "label": doc.vorlagen_baum_name or doc.name,
            "is_group": cint(doc.is_group),
            "sektion_id": doc.sektion_id,
            "parent": doc.parent_vorlagen_baum,
            "use_for_email": cint(doc.use_for_email),
            "use_for_druckvorlagen": cint(doc.use_for_druckvorlagen),
            "use_for_dokumentenvorlagen": cint(doc.use_for_dokumentenvorlagen),
            "match_type": match_type,
            "match_label": match_label,
            "match_value": match_value or doc.vorlagen_baum_name or doc.name
        })

        seen.add(key)

    # 1. Suche direkt im Knoten
    filters = []
    if sektion_id:
        filters.append(["sektion_id", "=", sektion_id])

    node_rows = frappe.get_all(
        DOCTYPE,
        filters=filters,
        or_filters=[
            ["name", "like", "%%%s%%" % query],
            ["vorlagen_baum_name", "like", "%%%s%%" % query],
        ],
        fields=["name", "vorlagen_baum_name"],
        limit_page_length=limit
    )

    for row in node_rows:
        add_node(
            row.name,
            match_type="node",
            match_label="Knoten",
            match_value=row.vorlagen_baum_name or row.name
        )

    # 2. Suche in Child Table: email_vorlagen
    if not purpose or purpose == "email":
        email_rows = frappe.get_all(
            "Email Vorlagen TBL",
            filters={
                "email_template": ["like", "%%%s%%" % query],
                "parenttype": DOCTYPE
            },
            fields=["parent", "email_template"],
            limit_page_length=limit
        )

        for row in email_rows:
            add_node(
                row.parent,
                match_type="email_vorlage",
                match_label="E-Mail Vorlage",
                match_value=row.email_template
            )

    # 3. Suche in Child Table: druckvorlagen
    if not purpose or purpose == "druck":
        druck_rows = frappe.get_all(
            "Druckvorlagen TBL",
            filters={
                "druckvorlage": ["like", "%%%s%%" % query],
                "parenttype": DOCTYPE
            },
            fields=["parent", "druckvorlage"],
            limit_page_length=limit
        )

        for row in druck_rows:
            add_node(
                row.parent,
                match_type="druckvorlage",
                match_label="Druckvorlage",
                match_value=row.druckvorlage
            )

    # 4. Suche in Child Table: dokumentenvorlagen
    if not purpose or purpose == "dokument":
        dokument_rows = frappe.get_all(
            "Dokumentenvorlage TBL",
            filters={
                "dokumentenvorlage": ["like", "%%%s%%" % query],
                "parenttype": DOCTYPE
            },
            fields=["parent", "dokumentenvorlage"],
            limit_page_length=limit
        )

        for row in dokument_rows:
            add_node(
                row.parent,
                match_type="dokumentenvorlage",
                match_label="Dokumentenvorlage",
                match_value=row.dokumentenvorlage
            )

    return results[:limit]