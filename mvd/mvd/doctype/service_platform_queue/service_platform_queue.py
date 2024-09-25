# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from mvd.mvd.service_plattform.api import update_mvm
from mvd.mvd.doctype.mitgliedschaft.utils import prepare_mvm_for_sp
from frappe.utils.background_jobs import enqueue
import json
from frappe.utils import cint

class ServicePlatformQueue(Document):
    pass

def flush_queue(limit=100):
    # ausgehende queues
    limit = int(frappe.db.get_single_value('Service Plattform API', 'flush_limit'))
    if limit > 0:
        limit = 'LIMIT {limit}'.format(limit=limit)
    else:
        limit = ''
    queues = frappe.db.sql("""SELECT `name` FROM `tabService Platform Queue` WHERE `status` IN ('Open', 'Failed') AND `eingehend` != 1 ORDER BY `creation` ASC {limit}""".format(limit=limit), as_dict=True)
    block_list = {}
    for _queue in queues:
        queue = frappe.get_doc("Service Platform Queue", _queue.name)
        if queue.mv_mitgliedschaft in block_list:
            queue.add_comment('Comment', text='Update ist durch fehlgeschlagenes Update {0} blockiert.'.format(block_list[queue.mv_mitgliedschaft]))
        else:
            if queue.status == 'Failed' and queue.bad_request >= 1:
                queue.add_comment('Comment', text='Update wird ignoriert. Vorgängiger BadRequest')
                if queue.mv_mitgliedschaft not in block_list:
                    block_list[queue.mv_mitgliedschaft] = queue.name
            else:
                mitgliedschaft = frappe.get_doc("Mitgliedschaft", queue.mv_mitgliedschaft)
                if mitgliedschaft.sektion_id != 'M+W-Abo':
                    if mitgliedschaft.status_c not in ('Online-Beitritt', 'Online-Mutation'):
                        update = False
                        if int(queue.update) == 1:
                            update = True
                        prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
                        update_status, possible_error, possible_error_code = update_mvm(prepared_mvm, update, return_error=True)
                        if cint(update_status) == 1:
                            queue.status = 'Closed'
                        else:
                            queue.status = 'Failed'
                            queue.error_count = queue.error_count + 1
                            queue.add_comment('Comment', text='{0}'.format(possible_error))
                            if queue.mv_mitgliedschaft not in block_list:
                                block_list[queue.mv_mitgliedschaft] = queue.name
                            if possible_error_code == 400:
                                queue.bad_request = queue.bad_request + 1
                        json_formatted_str = json.dumps(prepared_mvm, indent=2)
                        queue.objekt = json_formatted_str
                        queue.save(ignore_permissions=True)
                    else:
                        frappe.log_error("Mitglied: {0}\nStatus: {1}".format(mitgliedschaft.name, mitgliedschaft.status_c), 'API Queue: Falscher Status')
                else:
                    queue.status = 'Ignore'
                    queue.add_comment('Comment', text='Update wird ignoriert. Sektion = M+W-Abo')
                    queue.save(ignore_permissions=True)
