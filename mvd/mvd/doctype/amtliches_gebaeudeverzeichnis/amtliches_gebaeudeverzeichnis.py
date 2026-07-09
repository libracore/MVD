# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import requests
import zipfile
import io
import csv
from datetime import datetime
from frappe.model.document import Document

class AmtlichesGebaeudeverzeichnis(Document):
    pass

@frappe.whitelist()
def trigger_upload_job():
    frappe.enqueue(
        'mvd.mvd.doctype.amtliches_gebaeudeverzeichnis.amtliches_gebaeudeverzeichnis.run_sql_import',
        queue='long',
        timeout=3600
    )
    frappe.msgprint("Der Daten-Update wurde im Hintergrund gestartet. Dies kann einige Minuten dauern.")
    return True


def run_sql_import():
    url = "https://data.geo.admin.ch/ch.swisstopo.amtliches-gebaeudeadressverzeichnis/amtliches-gebaeudeadressverzeichnis_ch/amtliches-gebaeudeadressverzeichnis_ch_2056.csv.zip"
    
    try:
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            frappe.log_error(
                title="Fehler: Import Gebäudeverzeichnis (Download)",
                message="HTTP Status {0} - Die Datei konnte nicht von Swisstopo heruntergeladen werden.".format(response.status_code)
            )
            return

        content_bytes = io.BytesIO(response.content)
        csv_file_content = None

        if zipfile.is_zipfile(content_bytes):
            with zipfile.ZipFile(content_bytes) as z:
                csv_filenames = [f for f in z.namelist() if f.endswith('.csv')]
                if not csv_filenames:
                    frappe.log_error(
                        title="Fehler: Import Gebäudeverzeichnis (Format)",
                        message="Das ZIP-Archiv enthält keine CSV-Datei."
                    )
                    return
                
                csv_filename = csv_filenames[0]
                with z.open(csv_filename) as f:
                    csv_file_content = f.read().decode('utf-8-sig')
        else:
            csv_file_content = response.content.decode('utf-8-sig')

        if not csv_file_content:
            frappe.log_error(
                title="Fehler: Import Gebäudeverzeichnis (Leer)",
                message="Der heruntergeladene Inhalt ist leer oder konnte nicht gelesen werden."
            )
            return

        frappe.db.sql("DELETE FROM `tabAmtliches Gebaeudeverzeichnis`")

        now_time = frappe.db.escape(frappe.utils.now_datetime())
        content = io.StringIO(csv_file_content)
        reader = csv.DictReader(content, delimiter=';')

        batch = []
        for row in reader:
            zip_parts = row.get('ZIP_LABEL', '').split(' ', 1)
            plz = zip_parts[0] if len(zip_parts) > 0 else ""
            wohnort = zip_parts[1] if len(zip_parts) > 1 else ""
            
            raw_date = row.get('ADR_MODIFIED')
            if raw_date:
                try:
                    d = datetime.strptime(raw_date, '%d.%m.%Y').strftime('%Y-%m-%d')
                    formatted_date = "'{0}'".format(d)
                except ValueError:
                    formatted_date = 'NULL'
            else:
                formatted_date = 'NULL'

            val = "({0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}, {10}, 'Administrator', 'Administrator', {11}, {12}, 0)".format(
                                frappe.db.escape(row.get('ADR_EGAID', '')),
                                frappe.db.escape(row.get('STN_LABEL', '')),
                                frappe.db.escape(row.get('ADR_NUMBER', '')),
                                frappe.db.escape(plz),
                                frappe.db.escape(wohnort),
                                frappe.db.escape(row.get('COM_FOSNR', '')),
                                frappe.db.escape(row.get('COM_NAME', '')),
                                frappe.db.escape(row.get('COM_CANTON', '')),
                                formatted_date,
                                row.get('ADR_EASTING') or 0,
                                row.get('ADR_NORTHING') or 0,
                                now_time,
                                now_time
                            )
            batch.append(val)
            if len(batch) >= 5000:
                execute_raw_sql(batch)
                batch = []
                
        if batch:
            execute_raw_sql(batch)

        frappe.db.commit()

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            title="Fehler: Import Gebäudeverzeichnis",
            message="Fehler beim Ausführen des Imports:\n{0}\n\nTraceback:\n{1}".format(str(e), frappe.get_traceback())
        )
        

def execute_raw_sql(batch):
    query = """
        INSERT INTO `tabAmtliches Gebaeudeverzeichnis` 
        (name, stn_label, adr_number, plz, wohnort, com_fosnr, com_name, com_canton, adr_modified, adr_easting, adr_northing, owner, modified_by, creation, modified, docstatus)
        VALUES {0}
    """.format(", ".join(batch))
    frappe.db.sql(query)

@frappe.whitelist()
def get_swisstopo_url(ADR_EGAID=None):
    if not ADR_EGAID: return

    adr_easting = frappe.db.get_value("Amtliches Gebaeudeverzeichnis", ADR_EGAID, 'adr_easting')
    adr_northing = frappe.db.get_value("Amtliches Gebaeudeverzeichnis", ADR_EGAID, 'adr_northing')

    return """
        https://map.geo.admin.ch/#/map?lang=de&center={adr_easting},{adr_northing}&z=9&topic=ech&layers=ch.swisstopo.amtliches-gebaeudeadressverzeichnis@features={ADR_EGAID}&bgLayer=ch.swisstopo.pixelkarte-farbe
    """.format(
        adr_easting=adr_easting,
        adr_northing=adr_northing,
        ADR_EGAID=ADR_EGAID
    )