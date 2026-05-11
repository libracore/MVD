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
        {"label": _("Mitglied"), "fieldname": "mitglied_id", "fieldtype": "Link", "options": "Mitgliedschaft"},
        {"label": _("Mitglied Nr"), "fieldname": "mitglied_nr", "fieldtype": "Data"},
        {"label": _("Mitglied Name"), "fieldname": "mitglied_name", "fieldtype": "Data"},
        {"label": _("E-Mail"), "fieldname": "e_mail_1", "fieldtype": "Data"},
        {"label": _("Tel. Mobil"), "fieldname": "tel_m_1", "fieldtype": "Data"},
        {"label": _("Tel. Privat"), "fieldname": "tel_p_1", "fieldtype": "Data"},
        {"label": _("Mitglied Status"), "fieldname": "mitglied_status", "fieldtype": "Data"},
        {"label": _("Mitgliedtyp"), "fieldname": "mitgliedtyp_c", "fieldtype": "Data"},
        {"label": _("Rechnung"), "fieldname": "rechnung", "fieldtype": "Link", "options": "Sales Invoice"},
        {"label": _("Rechnung Status"), "fieldname": "rechnung_status", "fieldtype": "Data"},
        {"label": _("Betrag"), "fieldname": "betrag", "fieldtype": "Currency"},
        {"label": _("Ausstehender Betrag"), "fieldname": "ausstehender_betrag", "fieldtype": "Currency"},
        {"label": _("R-Datum"), "fieldname": "datum", "fieldtype": "Date"},
        {"label": _("Mitgliedschaftsjahr"), "fieldname": "mitgliedschaftsjahr", "fieldtype": "Int"},
        {"label": _("Z-Datum"), "fieldname": "payment_datum", "fieldtype": "Date"}
    ]

def get_data(filters):
    return frappe.db.sql("""
        SELECT
            sinv.name AS rechnung,
            sinv.grand_total AS betrag,
            sinv.outstanding_amount AS ausstehender_betrag,
            sinv.posting_date AS datum,
            sinv.mitgliedschafts_jahr AS mitgliedschaftsjahr,
            sinv.status AS rechnung_status,
            sinv.title AS mitglied_name,
            mvm.mitglied_nr,
            mvm.mitglied_id,
            mvm.status_c AS mitglied_status,
            mvm.mitgliedtyp_c,
            mvm.e_mail_1,
            mvm.tel_m_1,
            mvm.tel_p_1,
            IF(
                sinv.grand_total != sinv.outstanding_amount,
                IFNULL(pay.letztes_payment_datum, '---'),
                '---'
            ) AS payment_datum
        FROM `tabSales Invoice` sinv
        LEFT JOIN `tabMitgliedschaft` mvm
            ON sinv.mv_mitgliedschaft = mvm.name
        LEFT JOIN (
            SELECT
                per.reference_name,
                MAX(pe.posting_date) AS letztes_payment_datum
            FROM `tabPayment Entry Reference` per
            LEFT JOIN `tabPayment Entry` pe
                ON pe.name = per.parent
            GROUP BY per.reference_name
        ) pay
            ON pay.reference_name = sinv.name
        WHERE sinv.sektion_id = %(sektion_id)s
          AND sinv.docstatus = 1
          AND sinv.ist_mitgliedschaftsrechnung = 1
          AND (
              %(zahlstatus)s = ''
              OR (%(zahlstatus)s = 'Offen' AND sinv.status != 'Paid')
              OR (%(zahlstatus)s = 'Beglichen' AND sinv.status = 'Paid')
          )
          AND (
              %(jahr)s = ''
              OR sinv.mitgliedschafts_jahr = %(jahr)s
          )
    """, {
        "sektion_id": filters.sektion_id,
        "zahlstatus": filters.get("zahlstatus") or "",
        "jahr": filters.get("jahr") or ""
    }, as_dict=True)