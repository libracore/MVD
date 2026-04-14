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
def search_nodes(query, sektion_id=None, limit=20):
    if not frappe.has_permission(DOCTYPE, "read"):
        frappe.throw(_("Keine Leseberechtigung für {0}").format(DOCTYPE))

    query = (query or "").strip()
    limit = cint(limit) or 20

    if not query:
        return []

    filters = []

    if sektion_id:
        filters.append(["sektion_id", "=", sektion_id])

    rows = frappe.get_all(
        DOCTYPE,
        filters=filters,
        or_filters=[
            ["vorlagen_baum_name", "like", "%%%s%%" % query],
            ["name", "like", "%%%s%%" % query]
        ],
        fields=[
            "name",
            "vorlagen_baum_name",
            "sektion_id",
            "is_group",
            "parent_vorlagen_baum",
            "use_for_email",
            "use_for_druckvorlagen",
            "use_for_dokumentenvorlagen"
        ],
        order_by="vorlagen_baum_name asc",
        limit_page_length=limit
    )

    result = []
    for row in rows:
        result.append({
            "name": row.name,
            "label": row.vorlagen_baum_name or row.name,
            "sektion_id": row.sektion_id,
            "is_group": cint(row.is_group),
            "parent": row.parent_vorlagen_baum,
            "use_for_email": cint(row.use_for_email),
            "use_for_druckvorlagen": cint(row.use_for_druckvorlagen),
            "use_for_dokumentenvorlagen": cint(row.use_for_dokumentenvorlagen)
        })

    return result