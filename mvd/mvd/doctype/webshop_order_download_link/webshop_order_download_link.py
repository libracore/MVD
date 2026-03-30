# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, get_url, today

class WebshopOrderDownloadLink(Document):
    
    def before_save(self):
        if self.is_new():
            if self.pdf_file:
                self.generate_new_link()
            return

        old_doc = self.get_doc_before_save()
        if old_doc and self.pdf_file and self.pdf_file != old_doc.pdf_file:
            if old_doc.download_hash:
                self.append("link_history", {
                    "download_hash": old_doc.download_hash,
                    "download_link": old_doc.download_link,
                    "valid_until": add_days(today(), 14)
                })
            
            if self.pdf_file:
                self.generate_new_link()

    def generate_new_link(self):
        """Erzeugt einen neuen Hash und den Link"""
        self.download_hash = frappe.generate_hash(length=32)
        self.download_link = "{url}/api/method/mvd.mvd.v2.api.webshop_download?token={hash}".format(
            url=get_url(),
            hash=self.download_hash
        )
