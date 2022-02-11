# -*- coding: utf-8 -*-
# Copyright (c) 2018-2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import datetime
import json

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
                        'reminder_level': level
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
                    'currency': currency
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
