# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.utils.manuelle_rechnungs_items import get_item_price

'''
Beispiel CURL Request
----------------------
curl --location --request POST 'https://[DOMAIN]/api/method/mvd.mvd.v2.api.get_data' \
--header 'Authorization: token [API_KEY]:[API_SECRET]' \
--header 'Content-Type: application/json' \
--header 'Cookie: full_name=Guest; sid=Guest; system_user=yes; user_id=Guest; user_image=' \
--data-raw '{}'
'''

class return_object:
    def __init__(self):
        self.sektionen=[]
    
    def add_sektion(self, sektion):
        self.sektionen.append(sektion)
    
    def asDict(self):
        return self.__dict__

class sektion_object:
    def __init__(self):
        self.sektion=None
        self.items=None
    
    def set_values(self, sektion, items):
        self.sektion = sektion.name
        self.items = items
    
    def asDict(self):
        return self.__dict__

'''
    API Endpunkt
'''
# @frappe.whitelist(allow_guest=True)
@frappe.whitelist()
def get_data(**api_request):
    return_obj = return_object()
    sektionen = frappe.db.sql("""
                                SELECT
                                    `name`,
                                    `mitgliedschafts_artikel` AS `mitgliedschaft_privat`
                                FROM `tabSektion`
                              """, as_dict=True)
    for sektion in sektionen:
        item_details = get_item_details(sektion)
        sektion_obj = sektion_object()
        sektion_obj.set_values(sektion, item_details)
        return_obj.add_sektion(sektion_obj.asDict())
    
    frappe.local.response.http_status_code = 200
    frappe.local.response.message = return_obj.asDict()
    return

'''
    Hilfs-Methoden
'''
def get_item_details(sektion):
    items = []
    if sektion.mitgliedschaft_privat:
        item_details = frappe.db.sql("""
                                        SELECT
                                            `name`,
                                            `description`,
                                            NULL AS `rate`
                                        FROM `tabItem`
                                        WHERE `name` = '{0}'
                                     """.format(sektion.mitgliedschaft_privat), as_dict=True)
        if len(item_details) > 0:
            item_details[0].rate = get_item_rate(item_details[0].name)
            items.append(item_details[0])
    return items

def get_item_rate(item):
    return get_item_price(item)['price']