# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from rq import Queue, Worker
from frappe.utils.background_jobs import get_redis_conn

@frappe.whitelist()
def is_job_already_running(jobname):
    running = get_info(jobname)
    return running

@frappe.whitelist()
def is_mitglied_related_job_running(mitdlied_nr):
    running = get_info(mitdlied_nr, contains=True)
    return running

def get_info(jobname, contains=False):
    from rq import Queue, Worker
    from frappe.utils.background_jobs import get_redis_conn
    conn = get_redis_conn()
    queues = Queue.all(conn)
    workers = Worker.all(conn)
    jobs = []

    def add_job(j, name):
        if j.kwargs.get('site')==frappe.local.site:
            jobs.append({
                'job_name': str(j.kwargs.get('job_name')),
                'queue': name
            })

    for w in workers:
        j = w.get_current_job()
        if j:
            add_job(j, w.name)

    for q in queues:
        if q.name != 'failed':
            for j in q.get_jobs(): add_job(j, q.name)
    
    found_job = False
    for job in jobs:
        if contains:
            if jobname in job['job_name']:
                found_job = True
        else:
            if job['job_name'] == jobname:
                found_job = True

    return found_job