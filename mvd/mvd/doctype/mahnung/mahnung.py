# -*- coding: utf-8 -*-
# Copyright (c) 2018-2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import datetime
import json
from mvd.mvd.doctype.druckvorlage.druckvorlage import get_druckvorlagen

class Mahnung(Document):
    # this will apply all payment reminder levels in the sales invoices
    def update_reminder_levels(self):
        for invoice in self.sales_invoices:
            sales_invoice = frappe.get_doc("Sales Invoice", invoice.sales_invoice)
            sales_invoice.payment_reminder_level = invoice.reminder_level
            sales_invoice.save(ignore_permissions=True)
        return
    def reset_reminder_levels(self):
        for invoice in self.sales_invoices:
            sales_invoice = frappe.get_doc("Sales Invoice", invoice.sales_invoice)
            sales_invoice.payment_reminder_level = int(invoice.reminder_level) - 1
            sales_invoice.save(ignore_permissions=True)
        return
    # apply payment reminder levels on submit (server based)
    def on_submit(self):
        self.update_reminder_levels()
    def on_cancel(self):
        self.reset_reminder_levels()
    pass

# this function will create new payment reminders
@frappe.whitelist()
def create_payment_reminders(sektion_id):
    # check auto submit
    # ~ auto_submit = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "payment_reminder_auto_submit")
    
    # get company
    company = frappe.get_doc("Sektion", sektion_id).company
    # get all customers with open sales invoices
    sql_query = ("""SELECT `customer` 
            FROM `tabSales Invoice` 
            WHERE `outstanding_amount` > 0 
              AND `docstatus` = 1
              AND (`due_date` < CURDATE())
              AND ((`exclude_from_payment_reminder_until` IS NULL) OR (`exclude_from_payment_reminder_until` < CURDATE()))
              AND `company` = "{company}"
            GROUP BY `customer`;""".format(company=company))
    customers = frappe.db.sql(sql_query, as_dict=True)
    # get all sales invoices that are overdue
    if len(customers) > 0:
        max_level = 3
        for customer in customers:
            sql_query = ("""SELECT `name`, `due_date`, `posting_date`, `payment_reminder_level`, `grand_total`, `outstanding_amount` , `currency`, `mv_mitgliedschaft`
                    FROM `tabSales Invoice` 
                    WHERE `outstanding_amount` > 0 AND `customer` = '{customer}'
                      AND `docstatus` = 1
                      AND (`due_date` < CURDATE())
                      AND `company` = "{company}"
                      AND ((`exclude_from_payment_reminder_until` IS NULL) OR (`exclude_from_payment_reminder_until` < CURDATE()));
                    """.format(customer=customer.customer, company=company))
            open_invoices = frappe.db.sql(sql_query, as_dict=True)
            if open_invoices:
                now = datetime.now()
                invoices = []
                mitgliedschaften = []
                highest_level = 0
                total_before_charges = 0
                currency = None
                for invoice in open_invoices:
                    level = invoice.payment_reminder_level + 1
                    if level > max_level:
                        level = max_level
                    new_invoice = { 
                        'sales_invoice': invoice.name,
                        'amount': invoice.grand_total,
                        'outstanding_amount': invoice.outstanding_amount,
                        'posting_date': invoice.posting_date,
                        'due_date': invoice.due_date,
                        'reminder_level': level,
                        'ist_mitgliedschaftsrechnung': invoice.ist_mitgliedschaftsrechnung,
                        'mitgliedschafts_jahr': invoice.mitgliedschafts_jahr
                    }
                    if level > highest_level:
                        highest_level = level
                    total_before_charges += invoice.outstanding_amount
                    invoices.append(new_invoice)
                    currency = invoice.currency
                    if invoice.mv_mitgliedschaft:
                        mitgliedschaften.append({
                            'mv_mitgliedschaft': invoice.mv_mitgliedschaft
                        })
                # find reminder charge
                charge_matches = frappe.get_all("ERPNextSwiss Settings Payment Reminder Charge", 
                    filters={ 'reminder_level': highest_level },
                    fields=['reminder_charge'])
                reminder_charge = 0
                if charge_matches:
                    reminder_charge = charge_matches[0]['reminder_charge']
                druckvorlage = get_default_druckvorlage(sektion_id, frappe.get_value("Mitgliedschaft", mitgliedschaften[0]['mv_mitgliedschaft'], "language"))
                new_reminder = frappe.get_doc({
                    "doctype": "Mahnung",
                    "sektion_id": sektion_id,
                    "customer": customer.customer,
                    "mitgliedschaften": mitgliedschaften,
                    "hidden_linking": mitgliedschaften,
                    "date": "{year:04d}-{month:02d}-{day:02d}".format(
                        year=now.year, month=now.month, day=now.day),
                    "title": "{customer} {year:04d}-{month:02d}-{day:02d}".format(
                        customer=customer.customer, year=now.year, month=now.month, day=now.day),
                    "sales_invoices": invoices,
                    'highest_level': highest_level,
                    'total_before_charge': total_before_charges,
                    'reminder_charge': reminder_charge,
                    'total_with_charge': (total_before_charges + reminder_charge),
                    'company': company,
                    'currency': currency,
                    'druckvorlage': druckvorlage
                })
                reminder_record = new_reminder.insert(ignore_permissions=True)
                # ~ if int(auto_submit) == 1:
                    # ~ reminder_record.update_reminder_levels()
                    # ~ reminder_record.submit()
                frappe.db.commit()
        return 'Mahnungen wurden erstellt'
    else:
        return 'Keine Rechnungen zum Mahnen vorhanden'

# this allows to submit multiple payment reminders at once
@frappe.whitelist()
def bulk_submit(names):
    docnames = json.loads(names)
    for name in docnames:
        payment_reminder = frappe.get_doc("Payment Reminder", name)
        payment_reminder.update_reminder_levels()
        payment_reminder.submit()
    return

def get_default_druckvorlage(sektion, language):
    druckvorlage = frappe.get_list('Druckvorlage', fields='name', filters={'dokument': 'Mahnung', 'sektion_id': sektion, 'language': language or 'de', 'default': 1}, limit=1, ignore_ifnull=True)
    return druckvorlage[0].name

def get_mahnungs_qrrs(mahnung):
    mahnung = frappe.get_doc("Mahnung", mahnung)
    sektion = frappe.get_doc("Sektion", mahnung.sektion_id)
    bankkonto = frappe.get_doc("Account", sektion.account)
    qrrs = []
    for _sinv in mahnung.sales_invoices:
        sinv = frappe.get_doc("Sales Invoice", _sinv.sales_invoice)
        
        # receiver
        if sinv.company_address:
            cmp_addr = frappe.get_doc("Address", sinv.company_address)
            if cmp_addr:
                address_array = cmp_addr.address_line1.split(" ")
                address_line_item_count = len(address_array)
                cmp_country = frappe.get_doc("Country", cmp_addr.country)
                cmp_country_code = str(cmp_country.code).upper()
                cmp_address_line_detail = {'name': sinv.company, 'street': '', 'number': '', 'plz': cmp_addr.plz, 'city': cmp_addr.city, 'country': cmp_country_code }
                for i in range(0, (address_line_item_count - 1)):
                    cmp_address_line_detail['street'] = cmp_address_line_detail['street'] + " " + address_array[i]
                
                cmp_address_line_detail['number'] = address_array[address_line_item_count - 1]
                
                receiver_name = cmp_address_line_detail['name']
                receiver_street = cmp_address_line_detail['street']
                receiver_number = cmp_address_line_detail['number']
                receiver_pincode = cmp_address_line_detail['plz']
                receiver_town = cmp_address_line_detail['city']
                receiver_country = cmp_address_line_detail['country']
                
                if cmp_addr.postfach:
                    if cmp_addr.postfach_nummer:
                        receiver_street = 'Postfach'
                        receiver_number = cmp_addr['postfach_nummer']
                    else:
                        receiver_street = 'Postfach'
                        receiver_number = ' '
        else:
            receiver_name = False
            receiver_street = False
            receiver_number = False
            receiver_pincode = False
            receiver_town = False
            receiver_country = False
        
        # payer
        if sinv.customer_address:
            pay_addr = frappe.get_doc("Address", sinv.customer_address)
            if pay_addr:
                if pay_addr.postfach:
                    pay_country = frappe.get_doc("Country", pay_addr.country)
                    pay_country_code = str(pay_country.code).upper()
                    if pay_addr.postfach_nummer:
                        postfach_nummer = pay_addr.postfach_nummer
                    else:
                        postfach_nummer = ' '
                    
                    pay_address_line_detail = {'name': sinv.customer, 'street': 'Postfach', 'number': postfach_nummer, 'pin': pay_addr.pincode, 'city': pay_addr.city, 'country': pay_country_code }
                else:
                    pay_address_trimed = str(pay_addr.address_line1).strip()
                    pay_address_array = pay_address_trimed.split(" ")
                    pay_address_line_item_count = len(pay_address_array)
                    pay_country = frappe.get_doc("Country", pay_addr.country)
                    pay_country_code = str(pay_country.code).upper()
                    pay_address_line_detail = {'name': sinv.customer, 'street': '', 'number': '', 'pin': pay_addr.pincode, 'city': pay_addr.city, 'country': pay_country_code }
                    for i in range(0, (pay_address_line_item_count - 1)):
                        pay_address_line_detail['street'] = pay_address_line_detail['street'] + " " + pay_address_array[i]
                    
                    pay_address_line_detail['number'] = pay_address_array[pay_address_line_item_count - 1]
                
                payer_name = sinv.customer_name
                payer_street = pay_address_line_detail['street']
                payer_number = pay_address_line_detail['number']
                payer_pincode = pay_address_line_detail['pin']
                payer_town = pay_address_line_detail['city']
                payer_country = pay_address_line_detail['country']
                
                
                if not payer_street:
                    if payer_number:
                        payer_street = payer_number
                        payer_number = ' '
        else:
            payer_name = False
            payer_street = False
            payer_number = False
            payer_pincode = False
            payer_town = False
            payer_country = False
        
        qrr_dict = {
            'top_position': '191mm',
            'iban': bankkonto.iban or '',
            'reference': sinv.esr_reference,
            'reference_type': 'QRR',
            'currency': sinv.currency,
            'amount': "{:,.2f}".format(sinv.outstanding_amount).replace(",", "'"),
            'message': sinv.name,
            'additional_information': ' ',
            'receiver_name': receiver_name,
            'receiver_street': receiver_street,
            'receiver_number': receiver_number,
            'receiver_country': receiver_country,
            'receiver_pincode': receiver_pincode,
            'receiver_town': receiver_town,
            'payer_name': payer_name,
            'payer_street': payer_street,
            'payer_number': payer_number,
            'payer_country': payer_country,
            'payer_pincode': payer_pincode,
            'payer_town': payer_town
        }
        qrrs.append(qrr_dict)
    return qrrs
