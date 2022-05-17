# -*- coding: utf-8 -*-
# Copyright (c) 2021-2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from mvd.mvd.service_plattform.api import update_mvm
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import prepare_mvm_for_sp

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

@frappe.whitelist()
def flush_complete_queue():
    # ausgehende queues
    limit = int(frappe.db.get_single_value('Service Plattform API', 'flush_limit'))
    if limit > 0:
        limit = 'LIMIT {limit}'.format(limit=limit)
    else:
        limit = ''
    queues = frappe.db.sql("""SELECT `name` FROM `tabService Platform Queue` WHERE `status` = 'Open' AND `eingehend` != 1 ORDER BY `creation` ASC {limit}""".format(limit=limit), as_dict=True)
    for _queue in queues:
        queue = frappe.get_doc("Service Platform Queue", _queue.name)
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", queue.mv_mitgliedschaft)
        if mitgliedschaft.status_c not in ('Online-Anmeldung', 'Online-Beitritt', 'Online-Mutation'):
            update = False
            if int(queue.update) == 1:
                update = True
            prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
            update_status = update_mvm(prepared_mvm, update)
            queue.status = 'Closed'
            queue.objekt = str(prepared_mvm)
            queue.save(ignore_permissions=True)
            frappe.db.commit()
        else:
            frappe.log_error("Mitglied: {0}\nStatus: {1}".format(mitgliedschaft.name, mitgliedschaft.status_c), 'API Queue: Falscher Status')
