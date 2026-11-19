# -*- coding: utf-8 -*-
# Copyright (c) 2023-2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from mvd.mvd.utils.mail_drafts import draft_name


class EmailDrafts(Document):
    def autoname(self):
        self.name = draft_name(self.doctype_reference, self.docname, self.user)
