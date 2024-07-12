# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.doctype.retouren.retouren import create_post_retouren
from mvd.mvd.doctype.postnotiz.postnotiz import create_postnotiz
from mvd.mvd.service_plattform.api import send_postnotiz_to_sp
import requests
import zipfile
import os
import pysftp


class PostNotizForServicePlatform:
    mitgliedId = ''
    mitgliedNummer = ''
    kategorie = ''
    notiz = ''

class LibraCoreFacade:
    def get_zipfile_from_post_connector(self, postretouren_log):
        url = frappe.db.get_value("Postretouren Einstellungen", "Postretouren Einstellungen", "url")
        basic_auth_username = frappe.db.get_value("Postretouren Einstellungen", "Postretouren Einstellungen", "basic_auth_username")
        basic_auth_password = frappe.db.get_value("Postretouren Einstellungen", "Postretouren Einstellungen", "basic_auth_password")
        response = requests.get(url, auth=(basic_auth_username, basic_auth_password))
        file_path = "/home/frappe/frappe-bench/sites/{0}/private/files/{1}.zip".format(frappe.utils.get_host_name(), postretouren_log).replace(":8000", "")
        with open(file_path, mode="wb") as file:
            file.write(response.content)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_url": "/private/files/{0}.zip".format(postretouren_log),
            "file_name": "{0}.zip".format(postretouren_log),
            "attached_to_name": postretouren_log,
            "attached_to_doctype": 'Postretouren Log',
            "folder": "Home/Attachments"})
        _file.save()

        return 

    def get_csv_files_from_zip(self, postretouren_log):
        # unzip the zip_file and return a list of CSV files.
        csv_files = []
        file_path = "/home/frappe/frappe-bench/sites/{0}/private/files/{1}.zip".format(frappe.utils.get_host_name(), postretouren_log).replace(":8000", "")
        zip_file = zipfile.ZipFile(file_path)
        for csv_file in zip_file.namelist():
            zip_file.extract(csv_file, "/home/frappe/frappe-bench/sites/{0}/private/files/".format(frappe.utils.get_host_name()).replace(":8000", ""))
            if not csv_file.endswith(".csv"):
                old_csv_file = csv_file
                csv_file = csv_file.split(".")[0] + ".csv"
                os.rename("/home/frappe/frappe-bench/sites/{0}/private/files/{1}".format(frappe.utils.get_host_name(), old_csv_file).replace(":8000", ""), "/home/frappe/frappe-bench/sites/{0}/private/files/{1}".format(frappe.utils.get_host_name(), csv_file).replace(":8000", ""))
            _file = frappe.get_doc({
                "doctype": "File",
                "file_url": "/private/files/{0}".format(csv_file),
                "file_name": "{0}".format(csv_file),
                "attached_to_name": postretouren_log,
                "attached_to_doctype": 'Postretouren Log',
                "folder": "Home/Attachments"})
            _file.save()
            csv_files.append("/home/frappe/frappe-bench/sites/{0}/private/files/{1}".format(frappe.utils.get_host_name(), csv_file).replace(":8000", ""))
        return csv_files
    
    def get_csv_files_from_post(self, postretouren_log):
        settings = frappe.get_doc("Postretouren Einstellungen", "Postretouren Einstellungen")
        csv_files = []
        try:
            with self.connect_sftp(settings) as sftp:
                for file_name in sftp.listdir(settings.target_path):
                    # fetch the file
                    local_file = os.path.join("/home/frappe/frappe-bench/sites/{0}/private/files/".format(frappe.utils.get_host_name()).replace(":8000", ""), file_name)
                    remote_file = os.path.join(settings.target_path, file_name)
                    sftp.get(remote_file, local_file)

                    # save file as attachment
                    _file = frappe.get_doc({
                        "doctype": "File",
                        "file_url": "/private/files/{0}".format(file_name),
                        "file_name": "{0}".format(file_name),
                        "attached_to_name": postretouren_log,
                        "attached_to_doctype": 'Postretouren Log',
                        "folder": "Home/Attachments"})
                    _file.save()
                    csv_files.append("/home/frappe/frappe-bench/sites/{0}/private/files/{1}".format(frappe.utils.get_host_name(), file_name).replace(":8000", ""))
                    
        except Exception as err:
           frappe.log_error( err, "get_csv_files_from_post Failed")

        return csv_files
    
    def connect_sftp(self, settings):
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        key_file = "/home/frappe/frappe-bench/sites/{0}{1}".format(frappe.utils.get_host_name(), settings.key_file).replace(":8000", "")
        
        connection = pysftp.Connection(
                settings.host, 
                port=int(settings.port),
                username=settings.user, 
                private_key=key_file,
                cnopts=cnopts
            )
        
        return connection


    def post_retour_exists(self, auftrags_nummer, sendungs_nummer, postretouren_log):
        # Return true if PostRetour already exists, false otherwise
        already_handled = False
        for handled in postretouren_log.handled_postretouren:
            if handled.auftrags_nummer == auftrags_nummer and handled.sendungs_nummer == sendungs_nummer:
                already_handled = True
        
        if not already_handled:
            qty = frappe.db.sql("""
                            SELECT COUNT(`name`) AS `qty`
                            FROM `tabHandled Postretouren`
                            WHERE `auftrags_nummer` = '{0}'
                            AND `sendungs_nummer` = '{1}'
                          """.format(auftrags_nummer, sendungs_nummer), as_dict=True)[0].qty
            if qty > 0:
                already_handled = True
        
        return already_handled
    
    def set_post_retour_as_handled(self, auftrags_nummer, sendungs_nummer, postretouren_log):
        already_set = False
        for handled in postretouren_log.handled_postretouren:
            if handled.auftrags_nummer == auftrags_nummer and handled.sendungs_nummer == sendungs_nummer:
                already_set = True
        if not already_set:
            row = postretouren_log.append('handled_postretouren', {})
            row.auftrags_nummer = auftrags_nummer
            row.sendungs_nummer = sendungs_nummer

        return
    
    def set_postretouren_status(self, postretouren_log):
        has_warnings_or_errors = False
        for log in postretouren_log.logs:
            if log.type in ("Warning", "Error"):
                has_warnings_or_errors = True
        
        if has_warnings_or_errors:
            postretouren_log.status = "Failed"
        else:
            postretouren_log.status = "Closed"
        
        return

    def handle_post_objects(self, postretour, postnotiz, postretouren_log):
        # Handle PostRetour and PostNotiz in LibraCore
        create_post_retouren_job, second_in_a_row = create_post_retouren(postretour)
        if create_post_retouren_job != 1:
            self.log("{0}: \n{1}".format(str(create_post_retouren_job), frappe.utils.get_traceback()), postretouren_log, "Error")

        # If 2 times in a row MW could not be delivered, add following text to the postnotiz object
        if second_in_a_row == 1:
            postnotiz.notiz += (" // Zwei aufeinander folgende M+W konnten nicht zugestellt werden. "
                                "Die Anzahl Zeitungen sollte auf 0 gesetzt werden")
        
        create_postnotiz_job = create_postnotiz(postnotiz, postretour, postretouren_log.name)
        if create_postnotiz_job != 1:
            self.log("{0}: \n{1}".format(str(create_postnotiz_job), frappe.utils.get_traceback()), postretouren_log, "Error")

        # If section is Zurich, create PostNotizForServicePlatform object and send to SP4
        if frappe.db.get_value("Mitgliedschaft", postretour.mitgliedId, "sektion_id") == 'MVZH':
            postnotiz_for_sp = PostNotizForServicePlatform()
            postnotiz_for_sp.mitgliedId = postretour.mitgliedId
            postnotiz_for_sp.mitgliedNummer = postnotiz.mitgliedNummer
            postnotiz_for_sp.kategorie = postnotiz.kategorie
            postnotiz_for_sp.notiz = postnotiz.notiz
            self.send_to_sp4(postnotiz_for_sp)
        return

    def send_to_sp4(self, postnotiz_for_sp):
        from mvd.mvd.doctype.mitgliedschaft.utils import prepare_mvm_for_sp
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", postnotiz_for_sp.mitgliedId)
        json_to_send = {
            "kategorie": postnotiz_for_sp.kategorie,
            "notiz": postnotiz_for_sp.notiz,
            "mitglied": prepare_mvm_for_sp(mitgliedschaft)
        }
        send_postnotiz_to_sp(json_to_send)
        return

    @staticmethod
    def get_mw_ausgabe(sequence_nr):
        return frappe.db.sql("""
                             SELECT `ausgabe_kurz`
                             FROM `tabMW`
                             WHERE `laufnummer` = '{retoure_mw_sequence_number}'
                             LIMIT 1""".format(retoure_mw_sequence_number=sequence_nr), as_dict=True)[0].ausgabe_kurz

    @staticmethod
    def log(message, postretouren_log, type):
        row = postretouren_log.append('logs', {})
        row.type = type
        row.message = message

        return