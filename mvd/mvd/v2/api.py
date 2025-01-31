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
        self.doctype_sektion=None
        self.all_items=None
    
    def set_values(self, sektion, items, all_items):
        self.sektion = sektion.name
        self.all_items = all_items
        # insert whole classe i.e. doctype sektion
        self.doctype_sektion = frappe.get_doc("Sektion", sektion.name)
    def asDict(self):
        return self.__dict__

'''
    API Endpunkt
'''
# @frappe.whitelist(allow_guest=True)
@frappe.whitelist()
def get_data_sektionen(**api_request):
    return_obj = return_object()
    sektionen = frappe.db.sql("""
                                SELECT
                                    `name`,
                                    `mitgliedschafts_artikel` AS `mitgliedschaft_privat`
                                FROM `tabSektion`
                                WHERE `pseudo_sektion` != 1 AND `name` != 'M+W-Abo'
                              """, as_dict=True)
    for sektion in sektionen:
        item_details = get_item_details(sektion)
        sektion_obj = sektion_object()
        all_items = get_all_item_details(sektion)
        sektion_obj.set_values(sektion, item_details, all_items)
        return_obj.add_sektion(sektion_obj.asDict())

    frappe.local.response.http_status_code = 200
    frappe.local.response.message = return_obj.asDict()
    return

'''
    Hilfs-Methoden
'''
def get_item_names_of_doctype(doctype_name):
    '''
    Holt und gibt alle Item-Namen aus dem Doctype Sektion als Liste zurück
    '''
    meta = frappe.get_meta(doctype_name)

    link_fields = []
    
    for field in meta.fields:
        if field.fieldtype == 'Link' and field.options == 'Item':
            link_fields.append(field.fieldname)
    
    return link_fields


def get_all_item_details(sektion):
    '''
    Holt und gibt alle Item-Details aus dem Doctype Sektion zurück mit Artielnummer, Beschreibung und Preis
    '''
    
    #all_items = get_item_names_of_doctype("Sektion")
    all_items = ["mitgliedschafts_artikel", "mitgliedschafts_artikel_geschaeft", "mitgliedschafts_artikel_beitritt", "mitgliedschafts_artikel_beitritt_geschaeft", "mitgliedschafts_artikel_reduziert", "mitgliedschafts_artikel_gratis", "hv_artikel", "spenden_artikel"]
    
    # das ist nicht schön so
    doctype_sektion = frappe.get_doc("Sektion", sektion.name)
    
    items = []
    for item_name in all_items:
        if doctype_sektion.get(item_name):
            item_name = doctype_sektion.get(item_name)
    
        item_details = frappe.db.sql("""
                                        SELECT
                                            `name`,
                                            `description`,
                                            NULL AS `rate`
                                        FROM `tabItem`
                                        WHERE `name` = '{0}'
                                     """.format(item_name), as_dict=True)
        if len(item_details) > 0:
            item_details[0].rate = get_item_rate(item_details[0].name)
            items.append(item_details[0])
    
    return items

def get_item_rate(item):
    return get_item_price(item)['price']