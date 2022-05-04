# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from mvd.mvd.service_plattform.api import update_mvm
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import prepare_mvm_for_sp
from frappe.utils.background_jobs import enqueue

class ServicePlatformQueue(Document):
    pass

def flush_queue(limit=100):
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
        update = False
        if int(queue.update) == 1:
            update = True
        prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
        update_status = update_mvm(prepared_mvm, update)
        queue.status = 'Closed'
        queue.save(ignore_permissions=True)
