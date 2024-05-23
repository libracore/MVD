# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from mvd.mvd.doctype.postretouren_log.postretourhandler import PostRetourHandler
from mvd.mvd.doctype.postretouren_log.libracore_facade import LibraCoreFacade

class PostretourenLog(Document):
    pass

def start_post_retouren_process():
    new_postretouren_log = frappe.get_doc({
        'doctype': 'Postretouren Log',
        'status': 'Open'
    })
        
    new_postretouren_log.insert(ignore_permissions=True)
    frappe.db.commit()

    new_postretouren_log.status = 'WiP'
    new_postretouren_log.save()
    frappe.db.commit()

    process_post_retouren(new_postretouren_log)

def process_post_retouren(postretouren_log):
    pr_handler = PostRetourHandler()
    libracore = LibraCoreFacade()

    # get zip File
    libracore.get_zipfile_from_post_connector(postretouren_log.name)
    
    # extract csv from zip file
    csv_files = libracore.get_csv_files_from_zip(postretouren_log.name)

    for csv_file in csv_files:
        file = open(csv_file, 'r', encoding="utf-16-le")
        lines = file.read().splitlines()
        if len(lines) < 2:
            libracore.log("File should have 2 or more Lines. The following file is ignored: {0}".format(csv_file.split("/")[len(csv_file.split("/"))-1]), postretouren_log, "Warning")
        else:
            for line in lines[1:]:
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

        file.close()
    
    libracore.set_postretouren_status(postretouren_log)
    postretouren_log.save(ignore_permissions=True)

    return
