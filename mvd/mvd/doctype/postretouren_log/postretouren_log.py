# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from mvd.mvd.doctype.postretouren_log.postretourhandler import PostRetourHandler
from mvd.mvd.doctype.postretouren_log.libracore_facade import LibraCoreFacade
from frappe.utils.background_jobs import enqueue

class PostretourenLog(Document):
    def manual_start(self):
        sitename = frappe.utils.get_host_name() if frappe.utils.get_host_name() not in ['mvd:8000', 'dev.msmr.ch:8000'] else 'mvd'
        benchname = 'frappe-bench' if frappe.utils.get_host_name() not in ['mvd:8000', 'dev.msmr.ch:8000'] else 'mvd-bench'
        csv_files = []
        _csv_files = frappe.db.sql("""SELECT `file_url` FROM `tabFile` WHERE `attached_to_doctype` = 'Postretouren Log' AND `attached_to_name` = '{0}'""".format(self.name), as_dict=True)
        for csv_file in _csv_files:
            csv_files.append("/home/frappe/{0}/sites/{1}{2}".format(benchname, sitename, csv_file.file_url))
        
        self.status = 'WiP'
        self.save()
        frappe.db.commit()
        self.reload()

        args = {
            'postretouren_log': self,
            'csv_files': csv_files if len(csv_files) > 0 else None
        }
        enqueue("mvd.mvd.doctype.postretouren_log.postretouren_log.process_post_retouren", queue='long', job_name='Verarbeitung Postretouren Log', timeout=5000, **args)
        return

def start_post_retouren_process():
    new_postretouren_log = frappe.get_doc({
        'doctype': 'Postretouren Log',
        'status': 'Open'
    })
        
    new_postretouren_log.insert(ignore_permissions=True)
    frappe.db.commit()

    # Prüfung ob alle Vorgängigen Postretouren Log's verarbeitet wurden. Wenn ja, starten...
    existing_open_postretouren_logs = frappe.db.sql("""SELECT COUNT(`name`) AS `qty FROM `tabPostretouren Log` WHERE `status` IN ('Open', 'WiP')""", as_dict=True)
    if existing_open_postretouren_logs[0].qty > 0:
        # Stoppen der autom. Verarbeitung, da nicht alle Vorgängigen Postretouren Log's verarbeitet wurden.
        return
    
    new_postretouren_log.status = 'WiP'
    new_postretouren_log.save()
    frappe.db.commit()
    new_postretouren_log.reload()
    
    args = {
        'postretouren_log': new_postretouren_log
    }
    enqueue("mvd.mvd.doctype.postretouren_log.postretouren_log.process_post_retouren", queue='long', job_name='Verarbeitung Postretouren Log', timeout=5000, **args)
    return

def process_post_retouren(postretouren_log, csv_files=None):
    pr_handler = PostRetourHandler()
    libracore = LibraCoreFacade()

    # get zip File
    # libracore.get_zipfile_from_post_connector(postretouren_log.name)
    
    # extract csv from zip file
    # csv_files = libracore.get_csv_files_from_zip(postretouren_log.name)

    # get csv files
    if not csv_files:
        csv_files = libracore.get_csv_files_from_post(postretouren_log.name)
    
    # Aufgrund der Problemathik aus Ticket #1531 wird hier im Main-Prozess der DB-Commit ausgeführt (anstelle in den einzelnen Sub-Prozessen)
    commit_counter = 0

    for csv_file in csv_files:
        # Prüfung ob das entsprechende CSV bereits verarbeitet wurde. Wenn ja -> Skip
        skip_file = False
        for handled_post_file in postretouren_log.handled_post_files:
            if handled_post_file.file == csv_file:
                skip_file = True
        if skip_file:
            continue

        file = open(csv_file, 'r', encoding="utf-16-le")
        lines = file.read().splitlines()
        if len(lines) < 2:
            libracore.log("File should have 2 or more Lines. The following file is ignored: {0}".format(csv_file.split("/")[len(csv_file.split("/"))-1]), postretouren_log, "Warning")
        else:
            for line in lines[1:]:
                commit_counter += 1
                columns = line.split("\t")

                if len(columns) != 56:
                    libracore.log("Line should have 56 columns. The following line is ignored: {0}".format(line), postretouren_log, "Warning")
                    continue

                if len(columns[12]) != 26:
                    libracore.log("Custom Field 12 should have length 26. The following line is ignored: {0}".format(line), postretouren_log, "Warning")
                    continue

                if libracore.post_retour_exists(columns[2], columns[3], postretouren_log):
                    libracore.log("PostRetour ({0}, {1}) has already been processed, skip it".format(columns[2], columns[3]), postretouren_log, "Skip")
                    continue

                (pr, pn) = pr_handler.get_post_objects(columns)
                pr.rawData = line

                libracore.handle_post_objects(pr, pn, postretouren_log)
                libracore.set_post_retour_as_handled(columns[2], columns[3], postretouren_log)

                # Aufgrund der Problemathik aus Ticket #1531 wird hier im Main-Prozess der DB-Commit ausgeführt (anstelle in den einzelnen Sub-Prozessen)
                if commit_counter == 10:
                    postretouren_log.save(ignore_permissions=True)
                    frappe.db.commit()
                    postretouren_log.reload()
                    commit_counter = 0

        file.close()
        # Mark File as handled
        file_row = postretouren_log.append('handled_post_files', {})
        file_row.file = csv_file
        postretouren_log.save(ignore_permissions=True)
        frappe.db.commit()
        postretouren_log.reload()
        commit_counter = 0
    
    libracore.set_postretouren_status(postretouren_log)
    postretouren_log.save(ignore_permissions=True)
    return
