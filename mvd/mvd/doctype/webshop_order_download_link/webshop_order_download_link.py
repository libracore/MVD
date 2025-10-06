# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class WebshopOrderDownloadLink(Document):
	pass

@frappe.whitelist()
def generate_download_links():
    from frappe.utils import now
    items = frappe.get_all("Item", filters={"item_code": ["like", "%-D"]}, fields=["name", "item_code"])
    for item in items:
        # Skip if already exists
        exists = frappe.db.exists("Webshop Order Download Link", {"item": item.name})
        if exists:
            continue

        doc = frappe.new_doc("Webshop Order Download Link")
        doc.item = item.name
        doc.item_code = item.item_code
        doc.download_hash = frappe.generate_hash("", 32)
        doc.download_link = f"http://localhost:8001/api/method/mvd.mvd.v2.api.webshop_download?token={doc.download_hash}" # needs to be replaced
        doc.file = "f55722c498" # neeeds to be replaced
        doc.insert(ignore_permissions=True)