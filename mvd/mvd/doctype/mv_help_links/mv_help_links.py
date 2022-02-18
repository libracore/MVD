# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class MVHelpLinks(Document):
    pass

@frappe.whitelist()
def get_help_links():
    sql_query = """SELECT * FROM `tabMV Help Links`"""
    links = frappe.db.sql(sql_query, as_dict=True)
    if links:
        return links
    else:
        return False
