# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd
import zipfile
import requests
import io
from frappe.model.document import Document

class SektionPLZZuordnung(Document):
	pass

def prepare_data():
	link_ortschaftsverzeichnis = "https://data.geo.admin.ch/ch.swisstopo-vd.ortschaftenverzeichnis_plz/ortschaftenverzeichnis_plz/ortschaftenverzeichnis_plz_4326.csv.zip"
	response = requests.get(link_ortschaftsverzeichnis)
	with zipfile.ZipFile(io.BytesIO(response.content)) as z:
		# Get the correct CSV file inside the folder
		csv_file = [f for f in z.namelist() if f.endswith(".csv")][0]  
		# Read CSV directly from the ZIP
		df = pd.read_csv(z.open(csv_file),delimiter=';')

	# Liechtenstein rausfiltern (vom Schluss ohne Kanton)
	df = df.loc[df['Kantonskürzel'].isnull() == False]
	# Spalten die nicht gebraucht werden rausfiltern
	df = df[["Ortschaftsname", "PLZ", "Kantonskürzel"]]
	# Drop duplicates
	df = df.drop_duplicates(subset=['PLZ', 'Kantonskürzel'])
	df = df[["PLZ", "Kantonskürzel"]]

	# Map of Kantons to Sektion
	kanton_to_sektion = {
		'LU': 'MVLU', 'NW': 'MVLU', 'OW': 'MVLU', 'UR': 'MVLU',
		'AI': 'MVOS', 'AR': 'MVOS', 'TG': 'MVOS', 'SG': 'MVOS', 'GL': 'MVOS',
		'FR': 'MVDF',
		'SO': 'MVSO',
		'ZH': 'MVZH',
		'BE': 'MVBE',
		'AG': 'MVAG',
		'GR': 'MVGR',
		'SH': 'MVSH',
		'ZG': 'MVZG',
		'BS': 'MVBS',
		'SZ': 'MVSZ',
		'TI': 'ASI',
		'NE': 'ASLOCA', 'JU': 'ASLOCA', 'GE': 'ASLOCA', 'VS': 'ASLOCA', 'VD': 'ASLOCA',
	}

	# PLZs that map to MVBL regardless of Kanton
	mvbl_plz_set = {
		2471, 2472, 2473, 2474, 2475, 2476, 2477, 2478, 2479, 2480, 2481,
		2611, 2612, 2613, 2614, 2615, 2616, 2617, 2618, 2619, 2620, 2621, 2622
	}

	def assign_section(row):
		plz = row['PLZ']
		kanton = row['Kantonskürzel']

		if kanton == 'BL' or plz in mvbl_plz_set:
			return 'MVBL'
		return kanton_to_sektion.get(kanton, 'Unknown')

	df['Sektion'] = df.apply(assign_section, axis=1)

	# Keep the duplicated PLZ based on the most occuring Sektion per PLZ
	duplicated_plz_list = df[df.duplicated(subset=['PLZ'], keep=False)]['PLZ'].astype(str).unique().tolist()
	plz_to_sektion = get_most_occured_sektion_per_plz(duplicated_plz_list)
	def filter_duplicated_row(row):
		plz = row['PLZ']
		sektion = row['Sektion']
		if plz in plz_to_sektion:
			sektion_to_keep = plz_to_sektion[plz]
			sektion_exists = ((df['PLZ'] == plz) & (df['Sektion'] == sektion_to_keep)).any()
			if sektion_exists:
				return sektion == sektion_to_keep
			else:
				return True
		else:
			return True
	df = df[df.apply(filter_duplicated_row, axis=1)]

	# Drop duplicates based on PLZ, keep the first - just to make sure that it is deduplicated
	df_unique_plz = df.drop_duplicates(subset=['PLZ'], keep='first')
	return df_unique_plz

@frappe.whitelist()
def upload_data():
	# Delete all existing records in the Doctype
	df = prepare_data()
	frappe.db.sql("DELETE FROM `tabSektion PLZ Zuordnung`")  # Deletes all records in Sektion PLZ Zuordnung
	frappe.db.commit()  # Commit the transaction to the database
	
	# Insert the new records into the Doctype (Sektion PLZ Zuordnung)
	for _, row in df.iterrows():
		# Create a new record in the "Sektion PLZ Zuordnung" Doctype
		doc = frappe.get_doc({
			'doctype': 'Sektion PLZ Zuordnung',
			'plz': row['PLZ'],
			'sektion': row['Sektion']
		})
		doc.insert()

	frappe.db.commit()
	return True 


def get_most_occured_sektion_per_plz(plz_list):
	results = frappe.get_all(
		"Mitgliedschaft",
		filters={"plz": ["in", plz_list]},
		fields=["plz", "sektion_id", "COUNT(*) as count"],
		group_by="plz, sektion_id"
	)
	grouped = {}

	for row in results:
		plz = row['plz']
		if plz not in grouped:
			grouped[plz] = row
		else:
			if row['count'] > grouped[plz]['count']:
				grouped[plz] = row

	final_selection = list(grouped.values())
	plz_to_sektion = {int(item['plz']): item['sektion_id'] for item in final_selection}
	return plz_to_sektion