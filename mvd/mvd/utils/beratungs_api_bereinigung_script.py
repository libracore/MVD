# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.service_plattform.api import send_beratung
import time
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import prepare_mvm_for_sp
from frappe.utils.data import get_datetime_str

def nachsenden():
    frappe.db.set_value("Service Plattform API", "Service Plattform API", 'send_beratung_to_sp_unterbrechen', 1)
    frappe.db.commit()
    beratungen = frappe.db.sql("""SELECT `name` FROM `tabBeratung` WHERE `trigger_api` = 1""", as_dict=True)
    loop = 1
    total = len(beratungen)
    for ber in beratungen:
        print("Bereite versand vor...({0} von {1})".format(loop, total))
        try:
            beratung = frappe.get_doc("Beratung", ber.name)
            if beratung.sektion_id == 'MVZH':
                mitgliedschaft = frappe.get_doc("Mitgliedschaft", beratung.mv_mitgliedschaft)
                prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
                dokumente = []
                files = frappe.db.sql("""SELECT `name`, `file_name` FROM `tabFile` WHERE `attached_to_name` = '{0}'""".format(beratung.name), as_dict=True)
                for dok in files:
                    dok_data = {
                        "beratungDokumentId": dok.name,
                        "name": dok.file_name,
                        "datum": get_datetime_str(beratung.start_date).replace(" ", "T"),
                        "typ": str(dok.file_name.split(".")[len(dok.file_name.split(".")) - 1])
                    }
                    dokumente.append(dok_data)
                    
                json_to_send = {
                    "beratungId": beratung.name,
                    "mitglied": prepared_mvm,
                    "datumEingang": get_datetime_str(beratung.start_date).replace(" ", "T"),
                    "beratungskategorie": 'Mietzinserhöhung' if beratung.datum_mietzinsanzeige else 'Allgemeine Anfrage',
                    "telefonPrivatMobil": beratung.telefon_privat_mobil,
                    "email": beratung.raised_by,
                    "anderesMietobjekt": beratung.anderes_mietobjekt,
                    "frage": beratung.frage,
                    "datumBeginnFrist": get_datetime_str(beratung.datum_mietzinsanzeige).replace(" ", "T") if beratung.datum_mietzinsanzeige else get_datetime_str(beratung.start_date).replace(" ", "T"),
                    "dokumente": dokumente
                }
                
                create_beratungs_log(error=0, info=1, beratung=beratung.name, method='send_to_sp', title='Beratung an SP gesendet', json="{0}".format(str(json_to_send)))
                send_beratung(json_to_send, beratung.name)
            
            # remove mark for SP API
            frappe.db.set_value("Beratung", beratung.name, 'trigger_api', 0, update_modified=False)
            print("Versendet...({0} von {1})".format(loop, total))
        except Exception as err:
            # allgemeiner Fehler
            create_beratungs_log(error=1, info=0, beratung=None, method='send_to_sp', title='Exception', json="{0}".format(str(err)))
            print("Fehlgeschlagen...({0} von {1})".format(loop, total))
        time.sleep(120)
        print("Timeout abwarten...({0} von {1})".format(loop, total))
        loop += 1
    frappe.db.set_value("Service Plattform API", "Service Plattform API", 'send_beratung_to_sp_unterbrechen', 0)
    frappe.db.commit()

def create_beratungs_log(error=0, info=0, beratung=None, method=None, title=None, json=None):
    frappe.get_doc({
        'doctype': 'Beratungs Log',
        'error': error,
        'info': info,
        'beratung': beratung,
        'method': method,
        'title': title,
        'json': json
    }).insert(ignore_permissions=True)
    frappe.db.commit()
