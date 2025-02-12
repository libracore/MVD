# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from frappe.utils import cint
from frappe.utils.data import today, add_days
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr, get_adressblock, get_rg_adressblock
from mvd.mvd.utils.qrr_reference import get_qrr_reference

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
                            'mwst': 0,
                            'item_index': str(key).replace("artikel_nr", "")
                        }
                        items.append(item)
                
                for item in items:
                    item_index = item['item_index']
                    item['typ'] = order_data['artikeltyp_{0}'.format(item_index)]
                    item['qty'] = order_data['anzahl_{0}'.format(item_index)]
                    item['amount'] = order_data['betrag_{0}'.format(item_index)]
                    item['mwst'] = order_data['mwst_satz_{0}'.format(item_index)]
                
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
            
            if cint(not self.kundendaten_geladen) == 1:
                # Kundendaten
                self.strassen_nr = order_data['strassen_nr']
                self.tel_m = order_data['tel_m']
                self.email = order_data['email']
                self.tel_p = order_data['tel_p']
                self.strasse = order_data['strasse']
                self.vorname = order_data['vorname']
                self.postfach = order_data['postfach']
                self.anrede = order_data['anrede']
                self.firma = order_data['firma']
                self.ort = order_data['ort']
                self.nachname = order_data['nachname']
                self.plz = order_data['plz']

                # Mitgliedschaft
                self.mv_mitgliedschaft = get_mitglied_id_from_nr(order_data['mitgliedschaft_nr'])

                # Faktura Kunde
                if self.mv_mitgliedschaft:
                    faktura_kunden = frappe.db.sql("""SELECT `name` FROM `tabKunden` WHERE `mv_mitgliedschaft` = '{0}'""".format(self.mv_mitgliedschaft), as_dict=True)
                    if len(faktura_kunden) == 1:
                        self.faktura_kunde = faktura_kunden[0].name

                    mitgl = frappe.get_doc("Mitgliedschaft", self.mv_mitgliedschaft)
                    # Adressblock
                    self.adressblock = get_adressblock(mitgl)
                    # Rechnungs Adressblock
                    self.rg_adressblock = get_rg_adressblock(mitgl)

                self.kundendaten_geladen = 1
        except Exception as err:
            frappe.log_error("{0}\n{1}".format(err, frappe.utils.get_traceback()), 'Webshop Order; Validation Failed')
    
    def create_faktura_kunde(self):
        kunde = frappe.get_doc({
            "doctype":"Kunden",
            "mv_mitgliedschaft": self.mv_mitgliedschaft,
            "sektion_id": "MVD",
            'language': 'de',
            'kundentyp': 'Einzelperson',
            'anrede': self.anrede,
            'vorname': self.vorname,
            'nachname': self.nachname,
            'firma': self.firma,
            'zusatz_firma': None,
            'tel_p': self.tel_p,
            'tel_m': self.tel_m,
            'tel_g': None,
            'e_mail': self.email,
            'strasse': self.strasse,
            'zusatz_adresse':None,
            'nummer': self.strassen_nr,
            'nummer_zu': None,
            'plz': self.plz,
            'ort': self.ort,
            'postfach': 1 if self.postfach else 0,
            'land': 'Schweiz',
            'postfach_nummer': self.postfach if self.postfach else None,
            'abweichende_rechnungsadresse': 0,
            'rg_zusatz_adresse': None,
            'rg_strasse': None,
            'rg_nummer': None,
            'rg_nummer_zu': None,
            'rg_postfach': None,
            'rg_postfach_nummer': None,
            'rg_plz': None,
            'rg_ort': None,
            'rg_land': None,
            'daten_aus_mitgliedschaft': 0
        }).insert(ignore_permissions=True)
        
        self.faktura_kunde = kunde.name
        self.faktura_kunde_aktuell = 1
        
        self.save()
        return
    
    def update_faktura_kunde(self):
        kunde = frappe.get_doc("Kunden", self.faktura_kunde)
        kunde.mv_mitgliedschaft = self.mv_mitgliedschaft
        kunde.sektion_id = "MVD"
        kunde.language = 'de'
        kunde.kundentyp = 'Einzelperson'
        kunde.anrede = self.anrede
        kunde.vorname = self.vorname
        kunde.nachname = self.nachname
        kunde.firma = self.firma
        kunde.zusatz_firma = None
        kunde.tel_p = self.tel_p
        kunde.tel_m = self.tel_m
        kunde.tel_g = None
        kunde.e_mail = self.email
        kunde.strasse = self.strasse
        kunde.zusatz_adresse = None
        kunde.nummer = self.strassen_nr
        kunde.nummer_zu = None
        kunde.plz = self.plz
        kunde.ort = self.ort
        kunde.postfach = 1 if self.postfach else 0
        kunde.land = 'Schweiz'
        kunde.postfach_nummer = self.postfach if self.postfach else None
        kunde.abweichende_rechnungsadresse = 0
        kunde.rg_zusatz_adresse = None
        kunde.rg_strasse = None
        kunde.rg_nummer = None
        kunde.rg_nummer_zu = None
        kunde.rg_postfach = None
        kunde.rg_postfach_nummer = None
        kunde.rg_plz = None
        kunde.rg_ort = None
        kunde.rg_land = None
        kunde.daten_aus_mitgliedschaft = 0
        kunde.save()

        self.faktura_kunde_aktuell = 1
        self.save()
        return
    
    def create_sinv(self):
        item_json = json.loads(self.artikel_json)
        items_list = []
        for item in item_json['items']:
            if not frappe.db.exists("Item", item['item']):
                frappe.throw("Der Artikel {0} existiert nicht".format(item['item']))
            else:
                items_list.append({
                    'item_code': item['item'],
                    'qty': item['qty']
                })
        sinv = frappe.get_doc({
            'doctype': 'Sales Invoice',
            'company': 'MVD',
            'customer': frappe.db.get_value("Kunden", self.faktura_kunde, "kunde_kunde"),
            'sektion_id': 'MVD',
            'ist_sonstige_rechnung': 1,
            'mv_kunde': self.faktura_kunde,
            'customer_adress': frappe.db.get_value("Kunden", self.faktura_kunde, "adresse_kunde"),
            'contact_person': frappe.db.get_value("Kunden", self.faktura_kunde, "kontakt_kunde"),
            'items': items_list,
            'taxes_and_charges': 'MVD Gemischt - MVD',
            'druckvorlage': 'MVD Rechnung-MVD' if not self.online_payment_id else 'MVD Lieferschein-MVD',
            'due_date': add_days(today(), 30)
        }).insert(ignore_permissions=True)

        if self.online_payment_id:
            sinv.is_pos = 1
            sinv.pos_profile = 'MVD'
            row = sinv.append('payments', {})
            row.mode_of_payment = 'Credit Card'
            row.amount = sinv.outstanding_amount
        
        sinv.append_taxes_from_master()
        sinv.esr_reference = get_qrr_reference(sales_invoice=sinv.name)
        sinv.save(ignore_permissions=True)
        
        self.sinv = sinv.name
        self.save()

        return sinv.name



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
            return raise_xxx(500, '', err, daten=kwargs, error_log_title='500 > create_order_from_api')

# Success Return
def raise_200(answer='Success'):
    frappe.local.response.http_status_code = 200
    frappe.local.response.message = answer
    return ['200 Success', answer]

# Error Return
def raise_xxx(code, title, message, daten=None, error_log_title='SP API Error!'):
    frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(code, title, message, frappe.utils.get_traceback(), daten or ''), error_log_title)
    frappe.local.response.http_status_code = code
    frappe.local.response.message = message
    return ['{code} {title}'.format(code=code, title=title), {
        "error": {
            "code": code,
            "message": "{message}".format(message=message)
        }
    }]
