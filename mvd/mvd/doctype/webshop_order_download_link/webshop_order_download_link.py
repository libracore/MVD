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
    # Erzeugt download links für die Downloadbaren Items
    # die Bedingungs ist ein "-D" im Name
    # bei bereits bestehenden Download links wird kein neuer erzeugt, man kann also problemlos drauf klicken
    # falls man neue Links erzeugen will muss man den Eintrag löschen 
    items = frappe.get_all("Item", filters={"item_code": ["like", "%-D"]}, fields=["name", "item_code"])
    for item in items:
        latest_file = frappe.get_all(
            "File",
            filters={
                "attached_to_name": item.item_code,
                "file_name": ["like", "%.pdf"]
            },
            fields=["name"],
            order_by="creation desc",
            limit=1
        )

        existing_name = frappe.db.exists("Webshop Order Download Link", {"item": item.name})
        if existing_name:
            existing_doc = frappe.get_doc("Webshop Order Download Link", existing_name)
            if latest_file:
                existing_doc.file = latest_file[0].name
                existing_doc.save(ignore_permissions=True)
            continue  # nothing else to do for existing entries

        doc = frappe.new_doc("Webshop Order Download Link")
        doc.item = item.name
        doc.item_code = item.item_code
        doc.download_hash = frappe.generate_hash("", 32)
        doc.download_link = "{url}/api/method/mvd.mvd.v2.api.webshop_download?token={hash}".format(
            url=frappe.utils.get_url(),
            hash=doc.download_hash
        )

        if latest_file:
            doc.file = latest_file[0].name

        doc.insert(ignore_permissions=True)
