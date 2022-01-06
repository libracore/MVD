# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from mvd.mvd.utils.qrr_reference import get_qrr_reference

class FakultativeRechnung(Document):
    def before_submit(self):
        self.qrr_referenz = get_qrr_reference(fr=self.name)
