# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from frappe.utils import cint
from frappe.utils.data import today, add_days
from frappe import sendmail
from frappe.core.doctype.communication.email import make
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr, get_adressblock, get_rg_adressblock
from mvd.mvd.utils.qrr_reference import get_qrr_reference
import re

class WebshopOrder(Document):
    def validate(self):
        if self.v2 != 1:
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
                                'item_index': str(key).replace("artikel_nr_", "")
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
                    self.tel_p = order_data['tel_p'] if order_data['tel_p'] != self.tel_m else None
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

        elif self.v2 == 1:
            try:
                order_data = json.loads(self.request)

                # --- Payment ID ---
                if not self.online_payment_id:
                    if "transaction_uuid" in order_data:
                        self.online_payment_id = order_data["transaction_uuid"]

                # --- Artikel / Items ---
                if not self.artikel_json and "items" in order_data:
                    items = []
                    for idx, it in enumerate(order_data["items"], start=1):
                        item = {
                            "item": it.get("item_code"),
                            "typ": None, # es werden aber andere Infos geschickt ->it.get("title"),
                            "qty": cint(it.get("quantity", 0)),
                            "amount": float(it.get("itemTotalPrice", 0)),
                            "mwst": 0,  # wird auch nicht gesendet v2 payload
                            "item_index": str(idx),
                        }
                        items.append(item)

                    data_dict = {
                        "items": items,
                        "details": {
                            "versandkosten": (
                                order_data.get("payrexx_data", {})
                                        .get("invoice", {})
                                        .get("shippingAmount", 0)
                                if isinstance(order_data.get("payrexx_data"), dict)
                                else 0
                            ), # das kann "null" sein -> gibt das ein Problem?
                            "totalbetrag": order_data.get("total_cart"),
                            "bestellung_nr": order_data.get("order_number"),
                        },
                    }
                    self.artikel_json = json.dumps(data_dict, indent=2)

                # --- Kundendaten ---
                if cint(not self.kundendaten_geladen) == 1:
                    billing_contact = order_data.get("billing_address") if isinstance(order_data.get("billing_address"), dict) else {} # if empty they come as lists -> [] else as dict
                    shipping_contact = order_data.get("shipping_address") if isinstance(order_data.get("shipping_address"), dict) else {}

                    payrexx_data = order_data.get("payrexx_data") or {}
                    payrexx_contact = payrexx_data.get("contact", {}) if isinstance(payrexx_data, dict) else {}

                    # falsche Logik im Webshop weswegen wir bei Übereinstimmung die Rechnungsadresse in unsere Lieferadresse schreiben
                    if order_data.get("abweichende_lieferadresse") == "false":
                        self.vorname = billing_contact.get("firstname") or None
                        self.nachname = billing_contact.get("lastname") or None
                        self.email = billing_contact.get("email")
                        self.plz = billing_contact.get("zip") or None
                        self.ort = billing_contact.get("city") or None
                        self.strasse, self.strassen_nr = split_street_and_number(billing_contact.get("address") or "")
                        self.tel_m = payrexx_contact.get("phone") or None
                        self.tel_p = None # veraltet brauchen wir in Zukunft nicht mehr
                        self.adress_zusatz = billing_contact.get("addition") or None
                        self.postfach = billing_contact.get("po_box") or None
                        self.anrede = None  # salutation can only appear in payrexx data
                        self.firma = billing_contact.get("company") or None  
                        self.abweichende_rechnungsadresse = 0

                    if order_data.get("abweichende_lieferadresse") == "true":
                        # Lieferadresse
                        self.vorname = shipping_contact.get("firstname") or None
                        self.nachname = shipping_contact.get("lastname") or None
                        self.email = billing_contact.get("email")
                        self.plz = shipping_contact.get("zip") or None
                        self.ort = shipping_contact.get("city") or None
                        self.strasse, self.strassen_nr = split_street_and_number(shipping_contact.get("address") or "")
                        self.tel_m = payrexx_contact.get("phone") or None
                        self.tel_p = None # veraltet brauchen wir in Zukunft nicht mehr
                        self.adress_zusatz = shipping_contact.get("addition") or None
                        self.postfach = shipping_contact.get("po_box") or None
                        self.anrede = None  # salutation can only appear in payrexx data
                        self.firma = shipping_contact.get("company") or None
                        self.abweichende_rechnungsadresse = 1
                        # Rechnungsadresse falls vorhanden
                        self.rg_vorname = billing_contact.get("firstname") or None
                        self.rg_nachname = billing_contact.get("lastname") or None
                        self.rg_plz = billing_contact.get("zip") or None
                        self.rg_ort = billing_contact.get("city") or None
                        self.rg_strasse, self.rg_strassen_nr = split_street_and_number(billing_contact.get("address") or "")
                        self.rg_adress_zusatz = billing_contact.get("addition") or None
                        self.rg_postfach = billing_contact.get("po_box") or None
                        self.rg_firma = billing_contact.get("company") or None

                    # Mitgliedschaft (from new "member_id" or "member_nr")
                    member_id = order_data.get("member_id")
                    member_nr = order_data.get("member_nr")
                    if member_id:
                        self.mv_mitgliedschaft = member_id
                    elif member_nr:
                        self.mv_mitgliedschaft = get_mitglied_id_from_nr(member_nr)

                    # Faktura Kunde
                    if self.mv_mitgliedschaft:
                        faktura_kunden = frappe.db.sql(
                            """SELECT `name` FROM `tabKunden` 
                            WHERE `mv_mitgliedschaft` = '{0}'"""
                            .format(self.mv_mitgliedschaft),
                            as_dict=True,
                        )
                        if len(faktura_kunden) == 1:
                            self.faktura_kunde = faktura_kunden[0].name

                        mitgl = frappe.get_doc("Mitgliedschaft", self.mv_mitgliedschaft)
                        self.adressblock = get_adressblock(mitgl)
                        self.rg_adressblock = get_rg_adressblock(mitgl)

                    self.kundendaten_geladen = 1

            except Exception as err:
                frappe.log_error(
                    "{0}\n{1}".format(err, frappe.utils.get_traceback()),
                    "Webshop Order V2; Validation Failed",
                )

    def create_faktura_kunde(self):
        kunde = frappe.get_doc({
            "doctype":"Kunden",
            "mv_mitgliedschaft": self.mv_mitgliedschaft,
            "sektion_id": "MVD",
            'language': 'de',
            'kundentyp': 'Unternehmen' if self.firma else 'Einzelperson',
            'anrede': self.anrede,
            'vorname': self.vorname,
            'nachname': self.nachname,
            'firma': self.firma,
            'zusatz_firma': self.rg_firma if self.rg_firma else None,
            'tel_p': self.tel_p,
            'tel_m': self.tel_m,
            'tel_g': None,
            'e_mail': self.email,
            'strasse': self.strasse,
            'zusatz_adresse': self.adress_zusatz if self.adress_zusatz else None,
            'nummer': self.strassen_nr,
            'nummer_zu': None,
            'plz': self.plz,
            'ort': self.ort,
            'postfach': 1 if self.postfach else 0,
            'land': 'Schweiz',
            'postfach_nummer': self.postfach if self.postfach else None,
            'abweichende_rechnungsadresse': self.abweichende_rechnungsadresse if self.abweichende_rechnungsadresse else 0,
            'rg_vorname': self.rg_vorname if self.rg_vorname else None,
            'rg_vorname': self.rg_nachname if self.rg_nachname else None,
            'rg_zusatz_adresse': self.rg_adress_zusatz if self.rg_adress_zusatz else None,
            'rg_strasse': self.rg_strasse if self.rg_strasse else None,
            'rg_nummer': self.rg_strassen_nr if self.rg_strassen_nr else None,
            'rg_nummer_zu': None,
            'rg_postfach': None,
            'rg_postfach_nummer': self.rg_postfach if self.rg_postfach else None,
            'rg_plz': self.plz if self.plz else None,
            'rg_ort': self.ort if self.ort else None,
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
        kunde.kundentyp = 'Unternehmen' if self.firma else 'Einzelperson'
        kunde.anrede = self.anrede
        kunde.vorname = self.vorname
        kunde.nachname = self.nachname
        kunde.firma = self.firma
        kunde.zusatz_firma = self.rg_firma if self.rg_firma else None
        kunde.tel_p = self.tel_p
        kunde.tel_m = self.tel_m
        kunde.tel_g = None
        kunde.e_mail = self.email
        kunde.strasse = self.strasse
        kunde.zusatz_adresse = self.adress_zusatz if self.adress_zusatz else None
        kunde.nummer = self.strassen_nr
        kunde.nummer_zu = None
        kunde.plz = self.plz if self.plz else None
        kunde.ort = self.ort if self.ort else None
        kunde.postfach = 1 if self.postfach else 0
        kunde.land = 'Schweiz'
        kunde.postfach_nummer = self.postfach if self.postfach else None
        kunde.abweichende_rechnungsadresse = self.abweichende_rechnungsadresse if self.abweichende_rechnungsadresse else 0
        kunde.rg_vorname if self.rg_vorname else None
        kunde.rg_zusatz_adresse = self.rg_adress_zusatz if self.rg_adress_zusatz else None
        kunde.rg_strasse = self.rg_strasse if self.rg_strasse else None
        kunde.rg_nummer = self.rg_strassen_nr if self.rg_strassen_nr else None
        kunde.rg_nummer_zu = None
        kunde.rg_postfach = None
        kunde.rg_postfach_nummer = self.rg_postfach if self.rg_postfach else None
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
            'customer_group': frappe.db.get_value("Customer", frappe.db.get_value("Kunden", self.faktura_kunde, "kunde_kunde"), "customer_group"),
            'sektion_id': 'MVD',
            'ist_sonstige_rechnung': 1,
            'mv_kunde': self.faktura_kunde,
            'customer_adress': frappe.db.get_value("Kunden", self.faktura_kunde, "adresse_kunde"),
            'contact_person': frappe.db.get_value("Kunden", self.faktura_kunde, "kontakt_kunde"),
            'items': items_list,
            'taxes_and_charges': 'MVD Gemischt - MVD',
            'druckvorlage': 'MVD Rechnung-MVD' if not self.online_payment_id else 'MVD Lieferschein-MVD',
            'mv_mitgliedschaft': self.mv_mitgliedschaft,
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

        # --- send confirmation email ---
        send_invoice_confirmation_email(self.email, sinv.name)

        return sinv.name



def create_order_from_api(kwargs=None, v2=0):
    if (kwargs):
        try:
            json_formatted_str = json.dumps(kwargs, indent=2)
            webshop_order = frappe.get_doc({
                "doctype": "Webshop Order",
                "request": json_formatted_str,
                "v2": v2
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

def split_street_and_number(address: str):
    """
    Splits an address string into street name and house number.
    Example: 'Oberdorfstrasse 15a' -> ('Oberdorfstrasse', '15a')
    """
    if not address:
        return None, None

    # Match "street name" + "house number" at end
    match = re.match(r'^(.*?)[,\s]+(\d+\s?[a-zA-Z]?)$', address.strip())
    if match:
        street = match.group(1).strip()
        number = match.group(2).strip()
        return street, number

    # Fallback: whole string as street, no number
    return address.strip(), None

def send_invoice_confirmation_email(email, sinv_name):
    if not email:
        return

    try:
        subject = f"Bestätigung Ihrer Bestellung"

        # Render print format of Sales Invoice
        message = frappe.get_print(
            "Sales Invoice", sinv_name, print_format="Webshop Bestätigungs-Email"
        )

        # Create Communication
        comm = make(
            recipients=[email],
            sender=frappe.get_value("Email Account", {"default_outgoing": 1}, "email_id"),
            subject=subject,
            content=message,
            doctype="Sales Invoice",
            name=sinv_name,
            send_email=False
        )["name"]

        # Queue the email
        sendmail(
            recipients=[email],
            subject=subject,
            message=message,
            delayed=True,
            reference_doctype="Sales Invoice",
            reference_name=sinv_name,
            communication=comm
        )

    except Exception as err:
        frappe.log_error(
            "{0}\n\n{1}".format(err, frappe.utils.get_traceback()),
            f"Sales Invoice Confirmation Email Error ({sinv_name})"
        )
