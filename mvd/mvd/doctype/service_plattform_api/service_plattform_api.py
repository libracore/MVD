# -*- coding: utf-8 -*-
# Copyright (c) 2021-2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ServicePlattformAPI(Document):
    # this function will get a child value from a scope
    def get_value(self, scope, value):
        for c in self.connections:
            if c.connection == scope:
                return c.get(value)
    
    # this function will set a child value from a scope
    def set_value(self, scope, target, value):
        for c in self.connections:
            if c.connection == scope:
                c.set(target, value)
                self.save(ignore_permissions=True)
                frappe.db.commit()
                return True
        return False
