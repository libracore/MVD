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
    
    def set_values(self, sektion, all_items):
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
        sektion_obj = sektion_object()
        all_items = get_all_item_details(sektion)
        sektion_obj.set_values(sektion, all_items)
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
    
    items = {}
    for item_field_name in all_items:
        if doctype_sektion.get(item_field_name):
            item_name = doctype_sektion.get(item_field_name)
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
            #items.append(item_details[0])   
            items[item_details[0].name] = item_details[0]   
        items[item_details[0].name]['field_name'] = item_field_name          
    
    return items

def get_item_rate(item):
    return get_item_price(item)['price']

@frappe.whitelist()
def get_md_shop_all_items():
    """
    Retrieves a list of all enabled items from the 'tabItem' table along with their associated pricing and member rates.

    This function performs the following steps:
    1. Retrieves all items from the 'tabItem' table that are not marked as 'disabled' (disabled = 0).
    2. For each item, it sets default values for `rate` and `member_rate` to `NULL` (as placeholders).
    3. Retrieves the latest item rates from the `tabItem Price` table using the `get_md_rates()` function.
    4. Retrieves member-specific pricing for items from the `tabPricing Rule` table using the `get_md_member_rates()` function.
    5. Returns a list of items with the necessary data, which can include `rate` and `member_rate` if they exist.

    Returns:
        list: A list of dictionaries containing item details, including:
              - `item_code`: Unique identifier for the item.
              - `sektion_id`: Section ID of the item.
              - `item_name`: Name of the item.
              - `item_group`: Item group to which the item belongs.
              - `show_in_website`: Boolean (0 or 1)
              - `description`: Web long description of the item.
              - `rate`: Price list rate (optional, populated later).
              - `member_rate`: Member-specific rate (optional, populated later).
              - `image`: URL or path to the item's image.
    """
    items = frappe.db.sql("""SELECT `item_code` AS `item_code`,
                                `sektion_id` AS `sektion_id`,
                                `item_name` AS `item_name`,
                                `item_group` AS `item_group`,
                                `web_long_description` AS `description`,
                                `show_in_website` AS `show_in_website`,
                                NULL AS `rate`,
                                NULL AS `member_rate`,
                                `website_image` AS `image`
                                FROM `tabItem` 
                                WHERE `disabled` = 0 -- später brauchen wir noch webEnabled
                            ORDER BY `sektion_id`, `weightage` ASC;""", as_dict=True)
    item_rates = get_md_rates()
    item_member_rates = get_md_member_rates()

    for item in items:
        if item.item_code in item_rates:  # Update rate if available
            item.rate = item_rates[item.item_code].get('price_list_rate')
        if item.item_code in item_member_rates:  # Update member_rate if available
            item.member_rate = item_member_rates[item.item_code].get('rate')

    return items

def get_md_rates():
    """
    Fetches the latest valid price list rates for each item from the 'tabItem Price' table. For this 
    the function retrieves the most recent `price_list_rate` for each `item_code`.

    Returns:
        dict: A dictionary where the keys are `item_code` and the values are dictionaries containing
              item details such as `price_list_rate`.   
    """
    item_rates = frappe.db.sql("""SELECT *
                                FROM `tabItem Price` tip1
                                WHERE tip1.valid_from <= CURDATE()
                                AND tip1.valid_from = (
                                    SELECT MAX(valid_from)
                                    FROM `tabItem Price` tip2 
                                    WHERE tip1.item_code = tip2.item_code
                                    AND tip2.valid_from <= CURDATE()
                                );""", as_dict=True)
    return {item['item_code']: item for item in item_rates}

def get_md_member_rates():
    """
    Fetches the member-specific pricing rates for each `item_code` from the 'tabPricing Rule' table.

    The pricing rule has either no end date (`valid_upto` is NULL) or has a `valid_upto`
    date that has not yet passed. 
    
    The function performs a SQL query that joins the `tabPricing Rule Item Code` table with the `tabPricing Rule`
    table to retrieve the `rate` for each `item_code`.
    Returns:
        dict: A dictionary where the keys are `item_code` and the values are dictionaries containing
              the item pricing rule details, including the `rate`.
    """
    item_member_rates = frappe.db.sql("""SELECT tpric.*, tpr.rate, tpr.applicable_for 
                                FROM `tabPricing Rule Item Code` tpric
                                JOIN `tabPricing Rule` tpr 
                                    ON tpric.parent = tpr.name
                                WHERE tpr.applicable_for = 'Customer Group'
                                AND (tpr.valid_upto IS NULL OR NOT tpr.valid_upto <= CURDATE());""", as_dict=True)
    return {item['item_code']: item for item in item_member_rates}


@frappe.whitelist()
def get_member_annual_invoice(id):
    invoices = frappe.get_all(
    "Sales Invoice",
    filters={
        "mv_mitgliedschaft": id,
        "ist_mitgliedschaftsrechnung": 1},
    fields=['name', 'mitgliedschafts_jahr', 'grand_total', 'due_date', 'status', 'payment_reminder_level', 'outstanding_amount']
)

    # Determine base URL from request
    host = frappe.request.host or ""
    scheme = frappe.request.scheme or "https"
    base_url = f"{scheme}://{host}"

    for sinv in invoices:
        signature = frappe.get_doc("Sales Invoice", sinv.name).get_signature()
        sinv['pdf_link'] = f"{base_url}/api/method/mvd.mvd.v2.api.get_annual_invoice_pdf?invoice_name={sinv['name']}&signature={signature}"
        sinv.pop('name', None)
    return invoices

@frappe.whitelist(allow_guest=True)
def get_annual_invoice_pdf(invoice_name=None, signature=False):
    try:
        from erpnextswiss.erpnextswiss.guest_print import get_pdf_as_guest
        return get_pdf_as_guest(doctype="Sales Invoice", name=invoice_name, format="Automatisierte Mitgliedschaftsrechnung", key=signature)
    except Exception as err:
        return ['500 Internal Server Error', str(err)]
