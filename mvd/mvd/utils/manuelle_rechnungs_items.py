# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_item_price(item, customer_customer=None):
    customer_group = None
    if customer_customer:
        customer_group = frappe.db.get_value("Customer", customer_customer, "customer_group")
    if customer_group == 'Mitglied':
        # Get the parent Pricing Rule from Pricing Rule Item Code
        parent_rule = frappe.db.get_value("Pricing Rule Item Code", {"item_code": item}, "parent")
        if parent_rule:
            # Get the rate from the parent Pricing Rule, considering valid_from <= today
            price = frappe.db.sql("""
                SELECT rate
                FROM `tabPricing Rule`
                WHERE name = '{parent_rule}'
                AND valid_from <= CURDATE()
                ORDER BY valid_from DESC
                LIMIT 1
            """.format(parent_rule=parent_rule), as_dict=True)
            print('*****')
            print('*****')
            print(price)
            print(parent_rule)
            print('*****')
            print('*****')
    else:
        price = frappe.db.sql("""SELECT `price_list_rate` FROM `tabItem Price` WHERE `price_list` = 'Standard Selling' AND `item_code` = '{item}' AND `valid_from` <= CURDATE() ORDER BY `valid_from` DESC LIMIT 1""".format(item=item), as_dict=True)
    description = frappe.db.sql("""SELECT `description` FROM `tabItem` WHERE `name` = '{0}'""".format(item), as_dict=True)[0].description
    if len(price) > 0:
        if customer_group == 'Mitglied':
            return {
                'price': price[0].rate,
                'description': description
            }
        else:
            return {
                'price': price[0].price_list_rate,
                'description': description
            }
    else:
        return {
            'price': 0,
            'description': description
        }