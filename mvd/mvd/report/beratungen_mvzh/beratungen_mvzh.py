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
        {"label": _("Beratung ID"), "fieldname": "beratung_id", "fieldtype": "Link", "options": "Beratung"},
        {"label": _("Erstellungsdatum"), "fieldname": "erstellt_am", "fieldtype": "Date"},
        {"label": _("Name Person"), "fieldname": "name_person", "fieldtype": "Data"},
        {"label": _("E-Mail Person"), "fieldname": "e_mail_person", "fieldtype": "Data"},
        {"label": _("SP Lieferung"), "fieldname": "sp_lieferung", "fieldtype": "Date"},
        {"label": _("SP Status"), "fieldname": "sp_status", "fieldtype": "Code"},
        {"label": _("Übermittelt an SP"), "fieldname": "sp_ok", "fieldtype": "Check"}
    ]

def get_data(filters):
    data = []
    
    date_filter = """WHERE `creation` BETWEEN '{0} 00:00:00' AND '{1} 23:59:59'""".format(filters.von, filters.bis)
    sektion_filter = ''
    if filters.sektion:
        sektion_filter = """ AND `sektion_id` = '{sektion}'""".format(sektion=filters.sektion)
    
    beratungen = frappe.db.sql("""
                                SELECT
                                    `name` AS `beratung_id`,
                                    `mv_mitgliedschaft` AS `mitglied_id`,
                                    `creation` AS `erstellt_am`,
                                    `raised_by` AS `e_mail_person`,
                                    `raised_by_name` AS `name_person`
                                FROM `tabBeratung`
                                {date_filter}{sektion_filter}""".format(date_filter=date_filter, sektion_filter=sektion_filter), as_dict=True)
    for beratung in beratungen:
        beratung.update(get_mitglied_name(beratung))
        beratung.update(get_sp_details(beratung))
        data.append(beratung)
    
    return data

def get_mitglied_name(beratung):
    mitglied_info = {}
    if beratung.mitglied_id:
        mitglied_info.update({'mitglied_nr': frappe.db.get_value("Mitgliedschaft", beratung.mitglied_id, "mitglied_nr")})
    return mitglied_info

def get_sp_details(beratung):
    sp_info = {}
    sp_send_log = frappe.db.sql("""
                                    SELECT
                                        `json` AS `sp_status`,
                                        `creation` AS `sp_lieferung`
                                    FROM `tabBeratungs Log`
                                    WHERE `beratung` = '{beratung}'
                                    AND `method` = 'send_beratung'
                                    AND `info` = 1
                                    AND `title` = 'Beratung an SP übermittelt'""".format(beratung=beratung.beratung_id), as_dict=True)
    if len(sp_send_log) > 0:
        sp_info.update(sp_send_log[0])
        sp_info.update({'sp_ok': 1})
    
    return sp_info
