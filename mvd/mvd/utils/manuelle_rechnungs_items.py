# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_item_price(item):
    price = frappe.db.sql("""SELECT `price_list_rate` FROM `tabItem Price` WHERE `price_list` = 'Standard Selling' AND `item_code` = '{item}' AND `valid_from` <= CURDATE() ORDER BY `valid_from` DESC LIMIT 1""".format(item=item), as_dict=True)
    if len(price) > 0:
        return price[0].price_list_rate
    else:
        return 0
