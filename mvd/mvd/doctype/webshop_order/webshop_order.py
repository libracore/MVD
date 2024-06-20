# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json

class WebshopOrder(Document):
    def validate(self):
        try:
            order_data = json.loads(self.request)

            if not self.online_payment_id:
                if order_data['payment_id']:
                    self.online_payment_id = order_data['payment_id']
            
            if not self.artikel_json:
                items = []
                for key in order_data:
                    if 'artikel_nr' in key:
                        item = {
                            'item': order_data[key],
                            'typ': None,
                            'qty': 0,
                            'amount': 0,
                            'mwst': 0
                        }
                        items.append(item)
                
                item_loop = 1
                for item in items:
                    item['typ'] = order_data['artikeltyp_{0}'.format(item_loop)]
                    item['qty'] = order_data['anzahl_{0}'.format(item_loop)]
                    item['amount'] = order_data['betrag_{0}'.format(item_loop)]
                    item['mwst'] = order_data['mwst_satz_{0}'.format(item_loop)]
                    item_loop += 1
                
                data_dict = {
                    'items': items,
                    'details': {
                        'versandkosten': order_data['versandkosten'],
                        'totalbetrag': order_data['totalbetrag'],
                        'bestellung_nr': order_data['bestellung_nr']
                    }
                }
                json_formatted_data_dict = json.dumps(data_dict, indent=2)
                self.artikel_json = json_formatted_data_dict
            
            self.strassen_nr = order_data['strassen_nr']
            self.tel_m = order_data['tel_m']
            self.email = order_data['email']
            self.tel_p = order_data['tel_p']
            self.strasse = order_data['strasse']
            self.vorname = order_data['vorname']
            self.postfach = order_data['postfach']
            self.anrede = order_data['anrede']
            self.firma = order_data['firma']
            self.mitgliedschaft_nr = order_data['mitgliedschaft_nr']
            self.ort = order_data['ort']
            self.nachname = order_data['nachname']
            self.plz = order_data['plz']
        except Exception as err:
            frappe.log_error("{0}\n{1}".format(err, frappe.utils.get_traceback()), 'Webshop Order; Validation Failed')


def create_order_from_api(kwargs=None):
    if (kwargs):
        try:
            json_formatted_str = json.dumps(kwargs, indent=2)
            webshop_order = frappe.get_doc({
                "doctype": "Webshop Order",
                "request": json_formatted_str
            }).insert(ignore_permissions=True)
            return raise_200()
        except Exception as err:
            return raise_xxx(500, '', err, daten=kwargs)

# Success Return
def raise_200(answer='Success'):
    frappe.local.response.http_status_code = 200
    frappe.local.response.message = answer
    return ['200 Success', answer]

# Error Return
def raise_xxx(code, title, message, daten=None):
    frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(code, title, message, frappe.utils.get_traceback(), daten or ''), 'SP API Error!')
    frappe.local.response.http_status_code = code
    frappe.local.response.message = message
    return ['{code} {title}'.format(code=code, title=title), {
        "error": {
            "code": code,
            "message": "{message}".format(message=message)
        }
    }]
