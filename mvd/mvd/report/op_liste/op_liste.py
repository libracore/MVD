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
        {"label": _("Mitglied"), "fieldname": "mitglied", "fieldtype": "Link", "options": "Mitgliedschaft"},
        {"label": _("Mitglied Nr"), "fieldname": "mitglied_nr", "fieldtype": "Data"},
        {"label": _("Mitglied Status"), "fieldname": "mitglied_status", "fieldtype": "Data"},
        {"label": _("Rechnung"), "fieldname": "rechnung", "fieldtype": "Link", "options": "Sales Invoice"},
        {"label": _("Betrag"), "fieldname": "betrag", "fieldtype": "Currency"},
        {"label": _("Ausstehender Betrag"), "fieldname": "ausstehender_betrag", "fieldtype": "Currency"},
        {"label": _("Datum"), "fieldname": "datum", "fieldtype": "Date"},
        {"label": _("Mitgliedschaftsjahr"), "fieldname": "mitgliedschaftsjahr", "fieldtype": "Int"}
    ]

def get_data(filters):
    data = []
    data = get_nicht_bezahlt(filters, data)
    return data

def get_nicht_bezahlt(filters, data):
    # Mitglieder
    nicht_bezahlt_per_se = frappe.db.sql("""SELECT
                                                `sinv`.`name` AS `rechnung`,
                                                `sinv`.`grand_total` AS `betrag`,
                                                `sinv`.`outstanding_amount` AS `ausstehender_betrag`,
                                                `sinv`.`posting_date` AS `datum`,
                                                `sinv`.`mitgliedschafts_jahr` AS `mitgliedschaftsjahr`,
                                                `mvm`.`mitglied_nr` AS `mitglied_nr`,
                                                `mvm`.`status_c` AS `mitglied_status`
                                            FROM `tabSales Invoice` AS `sinv`
                                            LEFT JOIN `tabMitgliedschaft` AS `mvm` ON `sinv`.`mv_mitgliedschaft` = `mvm`.`name`
                                            WHERE `sinv`.`sektion_id` = 'MVAG'
                                            AND `sinv`.`status` != 'Paid'
                                            AND `sinv`.`docstatus` = 1
                                            AND `sinv`.`ist_mitgliedschaftsrechnung` = 1""".format(sektion_id=filters.sektion_id), as_dict=True)
    for record in nicht_bezahlt_per_se:
        data.append(record)
    
    return data
