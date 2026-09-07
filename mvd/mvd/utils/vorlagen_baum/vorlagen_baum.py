# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import json
import frappe
from frappe import _
from frappe.utils import cint


DOCTYPE = "Vorlagen Baum"
TEXTVORLAGEN_DOCTYPE = "Textvorlagen"
TEXTVORLAGEN_CHILD_DOCTYPE = "Textvorlagen TBL"


@frappe.whitelist()
def get_children(parent_name=None, sektion_id=None):
    if not frappe.has_permission(DOCTYPE, "read"):
        frappe.throw(
            _("Keine Leseberechtigung für {0}").format(DOCTYPE)
        )

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
            "use_for_dokumentenvorlagen",
            "use_for_textvorlagen"
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
            "use_for_dokumentenvorlagen": cint(
                row.use_for_dokumentenvorlagen
            ),
            "use_for_textvorlagen": cint(
                row.get("use_for_textvorlagen")
            )
        })

    return result


@frappe.whitelist()
def get_node_details(node_name, parent_doc=None):
    if not frappe.has_permission(DOCTYPE, "read"):
        frappe.throw(
            _("Keine Leseberechtigung für {0}").format(DOCTYPE)
        )

    doc = frappe.get_doc(DOCTYPE, node_name)

    result = {
        "name": doc.name,
        "label": doc.vorlagen_baum_name or doc.name,
        "sektion_id": doc.sektion_id,
        "is_group": cint(doc.is_group),
        "use_for_email": cint(doc.use_for_email),
        "use_for_druckvorlagen": cint(
            doc.use_for_druckvorlagen
        ),
        "use_for_dokumentenvorlagen": cint(
            doc.use_for_dokumentenvorlagen
        ),
        "use_for_textvorlagen": cint(
            doc.get("use_for_textvorlagen")
        ),
        "email_vorlagen": [],
        "druckvorlagen": [],
        "dokumentenvorlagen": [],
        "textvorlagen": []
    }

    # ---------------------------------------------------------
    # E-Mail Vorlagen
    # ---------------------------------------------------------

    for row in doc.get("email_vorlagen") or []:
        result["email_vorlagen"].append(
            _serialize_child_row(row)
        )

    # ---------------------------------------------------------
    # Druckvorlagen
    # ---------------------------------------------------------

    for row in doc.get("druckvorlagen") or []:
        result["druckvorlagen"].append(
            _serialize_child_row(row)
        )

    # ---------------------------------------------------------
    # Dokumentenvorlagen
    # ---------------------------------------------------------

    for row in doc.get("dokumentenvorlagen") or []:
        result["dokumentenvorlagen"].append(
            _serialize_child_row(row)
        )

    # ---------------------------------------------------------
    # Textvorlagen
    # ---------------------------------------------------------

    text_rows = list(
        doc.get("textvorlagen") or []
    )

    textvorlagen = _load_textvorlagen(
        text_rows
    )

    render_context = _get_render_context(
        parent_doc
    )

    for row in text_rows:
        result["textvorlagen"].append(
            _serialize_textvorlage_row(
                row=row,
                textvorlagen=textvorlagen,
                render_context=render_context
            )
        )

    return result


def _serialize_child_row(row):
    """
    Serialisiert eine normale Childtable-Zeile.
    """

    data = {
        "name": row.name,
        "doctype": row.doctype
    }

    for fieldname, value in row.as_dict().items():
        if fieldname not in data:
            data[fieldname] = value

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


def _load_textvorlagen(rows):
    """
    Lädt alle von den Childtable-Zeilen referenzierten
    Textvorlagen in einer Abfrage
    """

    names = []

    for row in rows:
        textvorlage = row.get("textvorlage")

        if (
            textvorlage
            and textvorlage not in names
        ):
            names.append(textvorlage)

    if not names:
        return {}

    templates = frappe.get_all(
        TEXTVORLAGEN_DOCTYPE,
        filters={
            "name": ["in", names]
        },
        fields=[
            "name",
            "titel",
            "text"
        ],
        limit_page_length=len(names)
    )

    return {
        template.name: template
        for template in templates
    }


def _serialize_textvorlage_row(
    row,
    textvorlagen,
    render_context=None
):
    """
    Serialisiert eine Zeile aus "Textvorlagen TBL".
    Der Text wird vor der Rückgabe mit dem parent_doc
    als Jinja-Kontext gerendert
    """

    data = _serialize_child_row(row)

    textvorlage_name = row.get("textvorlage")

    data["textvorlage"] = textvorlage_name
    data["titel"] = textvorlage_name or ""
    data["text"] = ""

    if not textvorlage_name:
        return data

    template_doc = textvorlagen.get(
        textvorlage_name
    )

    if not template_doc:
        return data

    data["titel"] = (
        template_doc.get("titel")
        or template_doc.name
    )

    text = template_doc.get("text") or ""

    if render_context:
        text = frappe.render_template(
            template=text,
            context=render_context
        )

    data["text"] = text

    return data


def _get_render_context(parent_doc):
    """
    Normalisiert parent_doc für frappe.render_template().

    parent_doc kommt je nach Aufruf entweder bereits als
    dict oder als JSON-String vom Client.

    Falls im Context das Feld `mv_mitgliedschaft` vorhanden
    und gesetzt ist, wird die referenzierte Mitgliedschaft
    geladen und deren Felder ergänzend in den Render-Context
    übernommen.

    Bereits vorhandene Werte aus parent_doc werden dabei
    nicht überschrieben.
    """

    if not parent_doc:
        return None

    # ---------------------------------------------------------
    # parent_doc normalisieren
    # ---------------------------------------------------------

    if isinstance(parent_doc, dict):
        render_context = dict(parent_doc)

    elif isinstance(parent_doc, str):
        try:
            render_context = json.loads(parent_doc)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "Vorlagen Baum: parent_doc konnte nicht gelesen werden"
            )
            return None

    elif hasattr(parent_doc, "as_dict"):
        render_context = parent_doc.as_dict()

    else:
        return None

    # ---------------------------------------------------------
    # Mitgliedschaft ergänzen
    # ---------------------------------------------------------

    mv_mitgliedschaft = render_context.get("mv_mitgliedschaft")

    if mv_mitgliedschaft:
        try:
            mitgliedschaft = frappe.get_doc(
                "Mitgliedschaft",
                mv_mitgliedschaft
            )

            mitgliedschaft_context = mitgliedschaft.as_dict()

            # Mitgliedschaft ergänzt nur Keys, die im
            # ursprünglichen Context noch nicht vorhanden sind.
            for key, value in mitgliedschaft_context.items():
                if key not in render_context:
                    render_context[key] = value

        except frappe.DoesNotExistError:
            frappe.log_error(
                "Mitgliedschaft '{0}' wurde nicht gefunden.".format(
                    mv_mitgliedschaft
                ),
                "Vorlagen Baum: Mitgliedschaft nicht gefunden"
            )

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "Vorlagen Baum: Mitgliedschaft konnte nicht geladen werden"
            )

    return render_context


@frappe.whitelist()
def search_nodes(
    query,
    sektion_id=None,
    purpose=None,
    limit=30
):
    query = (query or "").strip()
    limit = cint(limit) or 30

    purpose = _normalize_purpose(
        purpose
    )

    if not query:
        return []

    if not frappe.has_permission(DOCTYPE, "read"):
        frappe.throw(
            _("Keine Leseberechtigung für {0}").format(DOCTYPE)
        )

    results = []
    seen = set()

    def has_purpose(value):
        return (
            not purpose
            or value.lower() in purpose
        )

    def add_node(
        node_name,
        match_type="node",
        match_label="Knoten",
        match_value=None
    ):
        if not node_name:
            return

        key = (
            node_name,
            match_type,
            match_value
        )

        if key in seen:
            return

        doc = frappe.get_doc(
            DOCTYPE,
            node_name
        )

        if (
            sektion_id
            and doc.sektion_id != sektion_id
        ):
            return

        results.append({
            "name": doc.name,
            "label": (
                doc.vorlagen_baum_name
                or doc.name
            ),
            "is_group": cint(
                doc.is_group
            ),
            "sektion_id": doc.sektion_id,
            "parent": doc.parent_vorlagen_baum,
            "use_for_email": cint(
                doc.use_for_email
            ),
            "use_for_druckvorlagen": cint(
                doc.use_for_druckvorlagen
            ),
            "use_for_dokumentenvorlagen": cint(
                doc.use_for_dokumentenvorlagen
            ),
            "use_for_textvorlagen": cint(
                doc.get("use_for_textvorlagen")
            ),
            "match_type": match_type,
            "match_label": match_label,
            "match_value": (
                match_value
                or doc.vorlagen_baum_name
                or doc.name
            )
        })

        seen.add(key)

    # =========================================================
    # Knoten selbst durchsuchen
    # =========================================================

    filters = []

    if sektion_id:
        filters.append([
            "sektion_id",
            "=",
            sektion_id
        ])

    node_rows = frappe.get_all(
        DOCTYPE,
        filters=filters,
        or_filters=[
            [
                "name",
                "like",
                "%%%s%%" % query
            ],
            [
                "vorlagen_baum_name",
                "like",
                "%%%s%%" % query
            ],
        ],
        fields=[
            "name",
            "vorlagen_baum_name"
        ],
        limit_page_length=limit
    )

    for row in node_rows:
        add_node(
            row.name,
            match_type="node",
            match_label="Knoten",
            match_value=(
                row.vorlagen_baum_name
                or row.name
            )
        )

    # =========================================================
    # E-Mail Vorlagen
    # =========================================================

    if has_purpose("email"):
        email_rows = frappe.get_all(
            "Email Vorlagen TBL",
            filters={
                "email_template": [
                    "like",
                    "%%%s%%" % query
                ],
                "parenttype": DOCTYPE
            },
            fields=[
                "parent",
                "email_template"
            ],
            limit_page_length=limit
        )

        for row in email_rows:
            add_node(
                row.parent,
                match_type="email_vorlage",
                match_label="E-Mail Vorlage",
                match_value=row.email_template
            )

    # =========================================================
    # Druckvorlagen
    # =========================================================

    if has_purpose("druck"):
        druck_rows = frappe.get_all(
            "Druckvorlagen TBL",
            filters={
                "druckvorlage": [
                    "like",
                    "%%%s%%" % query
                ],
                "parenttype": DOCTYPE
            },
            fields=[
                "parent",
                "druckvorlage"
            ],
            limit_page_length=limit
        )

        for row in druck_rows:
            add_node(
                row.parent,
                match_type="druckvorlage",
                match_label="Druckvorlage",
                match_value=row.druckvorlage
            )

    # =========================================================
    # Dokumentenvorlagen
    # =========================================================

    if has_purpose("dokument"):
        dokument_rows = frappe.get_all(
            "Dokumentenvorlage TBL",
            filters={
                "dokumentenvorlage": [
                    "like",
                    "%%%s%%" % query
                ],
                "parenttype": DOCTYPE
            },
            fields=[
                "parent",
                "dokumentenvorlage"
            ],
            limit_page_length=limit
        )

        for row in dokument_rows:
            add_node(
                row.parent,
                match_type="dokumentenvorlage",
                match_label="Dokumentenvorlage",
                match_value=row.dokumentenvorlage
            )

    # =========================================================
    # Textvorlagen
    # =========================================================

    if has_purpose("text"):
        _search_textvorlagen(
            query=query,
            limit=limit,
            add_node=add_node
        )

    return results[:limit]


def _search_textvorlagen(
    query,
    limit,
    add_node
):
    """
    Sucht Textvorlagen sowohl über deren Dokumentnamen als
    auch über Titel und Inhalt.

    Anschliessend werden die dazugehörigen Vorlagen-Baum-
    Knoten über die Childtable ermittelt.
    """

    # ---------------------------------------------------------
    # 1. Direkter Treffer auf dem Linkfeld der Childtable
    # ---------------------------------------------------------

    direct_rows = frappe.get_all(
        TEXTVORLAGEN_CHILD_DOCTYPE,
        filters={
            "textvorlage": [
                "like",
                "%%%s%%" % query
            ],
            "parenttype": DOCTYPE
        },
        fields=[
            "parent",
            "textvorlage"
        ],
        limit_page_length=limit
    )

    direct_template_names = set()

    for row in direct_rows:
        direct_template_names.add(
            row.textvorlage
        )

        add_node(
            row.parent,
            match_type="textvorlage",
            match_label="Textvorlage",
            match_value=row.textvorlage
        )

    # ---------------------------------------------------------
    # 2. Im eigentlichen Textvorlagen-Doctype suchen
    # ---------------------------------------------------------

    template_rows = frappe.get_all(
        TEXTVORLAGEN_DOCTYPE,
        or_filters=[
            [
                "name",
                "like",
                "%%%s%%" % query
            ],
            [
                "titel",
                "like",
                "%%%s%%" % query
            ],
            [
                "text",
                "like",
                "%%%s%%" % query
            ]
        ],
        fields=[
            "name",
            "titel",
            "text"
        ],
        limit_page_length=limit
    )

    if not template_rows:
        return

    template_map = {
        row.name: row
        for row in template_rows
    }

    template_names = list(
        template_map.keys()
    )

    # ---------------------------------------------------------
    # 3. Baum-Knoten suchen, welche diese Textvorlagen
    #    referenzieren
    # ---------------------------------------------------------

    child_rows = frappe.get_all(
        TEXTVORLAGEN_CHILD_DOCTYPE,
        filters={
            "parenttype": DOCTYPE,
            "textvorlage": [
                "in",
                template_names
            ]
        },
        fields=[
            "parent",
            "textvorlage"
        ],
        limit_page_length=max(
            limit,
            len(template_names)
        )
    )

    query_lower = query.lower()

    for row in child_rows:
        template = template_map.get(
            row.textvorlage
        )

        if not template:
            continue

        titel = (
            template.get("titel")
            or template.name
        )

        name = template.name or ""

        text = template.get("text") or ""

        # ---------------------------------------------
        # Trefferart möglichst sinnvoll anzeigen
        # ---------------------------------------------

        if query_lower in titel.lower():
            match_label = "Textvorlage"
            match_value = titel

        elif query_lower in name.lower():
            match_label = "Textvorlage"
            match_value = name

        elif query_lower in text.lower():
            match_label = "Textvorlagen-Text"
            match_value = _make_search_excerpt(
                text,
                query
            )

        else:
            match_label = "Textvorlage"
            match_value = titel

        add_node(
            row.parent,
            match_type="textvorlage",
            match_label=match_label,
            match_value=match_value
        )


def _make_search_excerpt(
    text,
    query,
    length=120
):
    """
    Erstellt für Suchtreffer im Text einen kurzen Ausschnitt.
    """

    if not text:
        return ""

    text = str(text)
    query = str(query)

    text_lower = text.lower()
    query_lower = query.lower()

    position = text_lower.find(
        query_lower
    )

    if position < 0:
        if len(text) <= length:
            return text

        return text[:length] + "..."

    half = int(length / 2)

    start = max(
        0,
        position - half
    )

    end = min(
        len(text),
        position + len(query) + half
    )

    excerpt = text[start:end]

    if start > 0:
        excerpt = "..." + excerpt

    if end < len(text):
        excerpt += "..."

    return excerpt


def _normalize_purpose(purpose):
    """
    Normalisiert purpose unabhängig davon, ob Frappe
    einen String, JSON-String oder eine Liste übergibt.
    """

    if isinstance(purpose, str):
        try:
            parsed_purpose = json.loads(
                purpose
            )

            if isinstance(
                parsed_purpose,
                list
            ):
                purpose = parsed_purpose
            else:
                purpose = [purpose]

        except Exception:
            purpose = [purpose]

    elif purpose:
        purpose = list(purpose)

    else:
        purpose = []

    return [
        str(p).lower()
        for p in purpose
    ]


@frappe.whitelist()
def replace_jinja_in_text(text, doc):
    _doc = json.loads(doc)

    return frappe.render_template(
        template=text,
        context=_doc
    )