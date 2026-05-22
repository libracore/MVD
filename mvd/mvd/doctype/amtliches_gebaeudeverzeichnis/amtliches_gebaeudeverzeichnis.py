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
	
	response = requests.get(url, stream=True)
	if response.status_code != 200:
		frappe.throw("Download fehlgeschlagen.")

	frappe.db.sql("DELETE FROM `tabAmtliches Gebaeudeverzeichnis`")
	frappe.db.commit()

	with zipfile.ZipFile(io.BytesIO(response.content)) as z:
		csv_filename = [f for f in z.namelist() if f.endswith('.csv')][0]
		now_time = frappe.db.escape(frappe.utils.now_datetime())
		with z.open(csv_filename) as f:
			content = io.TextIOWrapper(f, encoding='utf-8-sig')
			reader = csv.DictReader(content, delimiter=';')

			batch = []
			for row in reader:
				zip_parts = row['ZIP_LABEL'].split(' ', 1)
				plz = zip_parts[0] if len(zip_parts) > 0 else ""
				wohnort = zip_parts[1] if len(zip_parts) > 1 else ""
				d = datetime.strptime(row.get('ADR_MODIFIED'), '%d.%m.%Y').strftime('%Y-%m-%d')
				formatted_date = "'{0}'".format(d)
				val = "({0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}, {10}, 'Administrator', 'Administrator', {11}, {12}, 0)".format(
									frappe.db.escape(row.get('ADR_EGAID')),
									frappe.db.escape(row.get('STN_LABEL')),
									frappe.db.escape(row.get('ADR_NUMBER')),
									frappe.db.escape(plz),
									frappe.db.escape(wohnort),
									frappe.db.escape(row.get('COM_FOSNR')),
									frappe.db.escape(row.get('COM_NAME')),
									frappe.db.escape(row.get('COM_CANTON')),
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


def execute_raw_sql(batch):
	query = """
		INSERT INTO `tabAmtliches Gebaeudeverzeichnis` 
		(name, stn_label, adr_number, plz, wohnort, com_fosnr, com_name, com_canton, adr_modified, adr_easting, adr_northing, owner, modified_by, creation, modified, docstatus)
		VALUES {0}
	""".format(", ".join(batch))
	frappe.db.sql(query)
	frappe.db.commit()