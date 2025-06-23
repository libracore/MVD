# Copyright (c) 2013, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return[
        {"label": _("Mitglied ID"), "fieldname": "mitglied_id", "fieldtype": "Link", "options": "Mitgliedschaft"},
        {"label": _("Mitglied Nr"), "fieldname": "mitglied_nr", "fieldtype": "Data"},
        {"label": _("Mitglied Name"), "fieldname": "mitglied_name", "fieldtype": "Data"},
        {"label": _("Mitglied Status"), "fieldname": "mitglied_status", "fieldtype": "Data"},
        {"label": _("Mitgliedtyp"), "fieldname": "mitgliedtyp_c", "fieldtype": "Data"},
        {"label": _("Zuletzt bearbeitet"), "fieldname": "modified", "fieldtype": "Data"},
        {"label": _("Anzahl Rechnungen"), "fieldname": "anzahl_rechnungen", "fieldtype": "Int"},
    ]

def get_data(filters):
    sektion_id = filters.get("sektion_id")

    # Step 1: Get mitglied_ids with at least one unpaid/overdue sales invoice
    invoice_mitglied_ids = frappe.get_all(
        "Sales Invoice",
        filters={"status": ["in", ["Unpaid", "Overdue"]]},
        fields=["mv_mitgliedschaft"]
    )
    mitglied_ids = list(set(inv["mv_mitgliedschaft"] for inv in invoice_mitglied_ids if inv["mv_mitgliedschaft"]))

    if not mitglied_ids:
        return []

    # Step 2: Get matching Mitgliedschaft records
    mitglieder = frappe.get_all(
        "Mitgliedschaft",
        filters={
            "status_c": "Ausschluss",
            "sektion_id": sektion_id,
            "mitglied_id": ["in", mitglied_ids]
        },
        fields=[
            "mitglied_id",
            "mitglied_nr",
            "vorname_1",
            "nachname_1",
            "status_c as mitglied_status",
            "mitgliedtyp_c",
            "modified",
        ]
    )

    # Step 3: Concatenate names
    for m in mitglieder:
        m["mitglied_name"] = "{0} {1}".format(m.get('vorname_1', ''), m.get('nachname_1', '')).strip()
        # Trim milliseconds from modified
        if m.get("modified"):
            m["modified"] = m["modified"].strftime("%Y-%m-%d %H:%M:%S")
        # Add invoice count
        m["anzahl_rechnungen"] = frappe.db.count("Sales Invoice", {
            "mv_mitgliedschaft": m["mitglied_id"],
            "status": ["in", ["Unpaid", "Overdue"]]
        })

    return mitglieder