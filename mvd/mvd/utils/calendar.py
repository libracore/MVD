# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt
#
# call the API from
#   /api/method/mvd.mvd.utils.calendar.download_calendar?secret=[secret]
#

from icalendar import Calendar, Event
import frappe
from frappe.utils import cint

def get_calendar(secret):
    # check access
    enabled = frappe.db.get_value("Calendar Sync Settings", "Calendar Sync Settings", "enabled")
    if cint(enabled) == 0:
        return
    erp_secret = frappe.db.get_value("Calendar Sync Settings", "Calendar Sync Settings", "secret")
    if not secret == erp_secret:
        return
        
    # initialise calendar
    cal = Calendar()

    # set properties
    cal.add('prodid', '-//MVD//libracore//')
    cal.add('version', '2.0')

    # get data
    sql_query = """SELECT * FROM `tabBeratung Termin`"""
    events = frappe.db.sql(sql_query, as_dict=True)
    # add events
    for erp_event in events:
        event = Event()
        event.add('summary', 'Beratungstermin')
        event.add('dtstart', erp_event['von'])
        if erp_event['bis']:
            event.add('dtend', erp_event['bis'])
        event.add('dtstamp', erp_event['modified'])
        description = get_event_description(erp_event)
        event.add('description', description)
        # add to calendar
        cal.add_component(event)
    
    return cal

def get_event_description(erp_event):
    kuerzel = ""
    try:
        berater_in = frappe.get_doc("Termin Kontaktperson", erp_event['berater_in'])
        for word in berater_in.kontakt.split(" "):
            kuerzel += "{0}.".format(word[0])
    except:
        kuerzel = "Kein/e Berater*in hintergelgt."
        pass

    description = """Berater*inn: {berater}\nOrt / Art: {art}\nVon - Bis: {von} - {bis}\n\n<a href="https://libracore.mieterverband.ch/desk#Form/Beratung/{beratung}">{beratung}</a>
    """.format(berater=kuerzel, \
                art=erp_event['art'], \
                von=erp_event['von'], \
                bis=erp_event['bis'], \
                beratung=erp_event['parent'])
    return description

@frappe.whitelist(allow_guest=True)
def download_calendar(secret):
    frappe.local.response.filename = "calendar.ics"
    calendar = get_calendar(secret)
    if calendar:
        frappe.local.response.filecontent = calendar.to_ical()
    else:
        frappe.local.response.filecontent = "No access"
    frappe.local.response.type = "download"