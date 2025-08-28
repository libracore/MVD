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
	# Zusätzliche PLZ die wir aus dem Postverzeichnis extrahiert haben. Die Extraktion ist unter der Funktion als Blockkommentar
	fehlende_plz =[['1001', 'VD'], ['1002', 'VD'], ['1014', 'VD'], ['1200', 'GE'], ['1211', 'GE'], ['1401', 'VD'], ['1702', 'FR'],
		['1704', 'FR'], ['1707', 'FR'], ['1708', 'FR'], ['1701', 'FR'], ['1951', 'VS'], ['2001', 'NE'], ['2004', 'NE'], 
		['2007', 'NE'], ['2009', 'NE'], ['2002', 'NE'], ['2003', 'NE'], ['2006', 'NE'], ['2302', 'NE'], ['2303', 'NE'],
		['2301', 'NE'], ['2500', 'BE'], ['2501', 'BE'], ['3000', 'BE'], ['3001', 'BE'], ['3002', 'BE'], ['3003', 'BE'],
		['3321', 'BE'], ['3401', 'BE'], ['3402', 'BE'], ['3601', 'BE'], ['3602', 'BE'], ['3607', 'BE'], ['4000', 'BS'],
		['4002', 'BS'], ['4003', 'BS'], ['4004', 'BS'], ['4005', 'BS'], ['4007', 'BS'], ['4009', 'BS'], ['4010', 'BS'],
		['4011', 'BS'], ['4012', 'BS'], ['4013', 'BS'], ['4015', 'BS'], ['4016', 'BS'], ['4018', 'BS'], ['4019', 'BS'],
		['4020', 'BS'], ['4024', 'BS'], ['4025', 'BS'], ['4030', 'BS'], ['4032', 'BS'], ['4091', 'BS'], ['4501', 'SO'],
		['4502', 'SO'], ['4503', 'SO'], ['4601', 'SO'], ['4801', 'AG'], ['4901', 'BE'], ['5001', 'AG'], ['5201', 'AG'],
		['5401', 'AG'], ['5402', 'AG'], ['6000', 'LU'], ['6002', 'LU'], ['6160', 'LU'], ['6301', 'ZG'], ['6501', 'TI'],
		['6506', 'TI'], ['6601', 'TI'], ['6604', 'TI'], ['6836', 'TI'], ['6901', 'TI'], ['6902', 'TI'], ['6903', 'TI'],
		['6904', 'TI'], ['6905', 'TI'], ['6906', 'TI'], ['7001', 'GR'], ['7004', 'GR'], ['7006', 'GR'], ['7007', 'GR'],
		['8000', 'ZH'], ['8010', 'ZH'], ['8080', 'ZH'], ['8021', 'ZH'], ['8022', 'ZH'], ['8023', 'ZH'], ['8024', 'ZH'],
		['8027', 'ZH'], ['8031', 'ZH'], ['8033', 'ZH'], ['8034', 'ZH'], ['8036', 'ZH'], ['8039', 'ZH'], ['8040', 'ZH'],
		['8042', 'ZH'], ['8058', 'ZH'], ['8061', 'ZH'], ['8063', 'ZH'], ['8088', 'ZH'], ['8090', 'ZH'], ['8091', 'ZH'],
		['8092', 'ZH'], ['8093', 'ZH'], ['8099', 'ZH'], ['8201', 'SH'], ['8202', 'SH'], ['8204', 'SH'], ['8301', 'ZH'],
		['8401', 'ZH'], ['8402', 'ZH'], ['8410', 'ZH'], ['8411', 'ZH'], ['8501', 'TG'], ['8502', 'TG'], ['8503', 'TG'],
		['8612', 'ZH'], ['8613', 'ZH'], ['8622', 'ZH'], ['8639', 'ZH'], ['8813', 'ZH'], ['9001', 'SG'], ['9004', 'SG'],
		['9006', 'SG'], ['9007', 'SG'], ['9013', 'SG'], ['9102', 'AR'], ['8238', 'SH'], ['6303', 'ZG'], ['7003', 'GR'],
		['3024', 'BE'], ['3030', 'BE'], ['6908', 'TI'], ['6009', 'LU'], ['5232', 'AG'], ['6341', 'ZG'], ['9029', 'SG'],
		['1709', 'FR'], ['8879', 'SG'], ['1811', 'VD'], ['3609', 'BE'], ['8070', 'ZH'], ['8071', 'ZH'], ['1631', 'FR'],
		['3040', 'BE'], ['4040', 'BL'], ['6007', 'LU'], ['8759', 'GL'], ['9020', 'SG'], ['9026', 'SG'], ['6031', 'LU'],
		['6021', 'LU'], ['6391', 'OW'], ['6281', 'LU'], ['6011', 'LU'], ['6061', 'OW'], ['6371', 'NW'], ['6431', 'SZ'],
		['9471', 'SG'], ['9401', 'SG'], ['9501', 'SG'], ['4509', 'SO'], ['4070', 'BS'], ['6602', 'TI'], ['9201', 'SG'],
		['8510', 'TG'], ['3050', 'BE'], ['8086', 'ZH'], ['8085', 'ZH'], ['2010', 'NE'], ['8285', 'TG'], ['4039', 'BS'],
		['2510', 'BE'], ['1310', 'VD'], ['8098', 'ZH'], ['4620', 'SO'], ['8183', 'ZH'], ['8325', 'ZH'], ['8520', 'TG'],
		['8343', 'ZH'], ['8087', 'ZH'], ['9024', 'SG'], ['4609', 'SO'], ['1818', 'VD'], ['1440', 'VD'], ['4034', 'BS'],
		['4035', 'BS'], ['4089', 'BS'], ['8068', 'ZH'], ['3071', 'BE'], ['4033', 'BS'], ['3039', 'BE'], ['4042', 'BL'],
		['8081', 'ZH'], ['8901', 'ZH'], ['3041', 'BE'], ['4041', 'BS'], ['4075', 'BS'], ['1019', 'VD'], ['1039', 'VD'],
		['6346', 'ZG'], ['3085', 'BE'], ['1300', 'VD'], ['4621', 'SO'], ['6590', 'TI'], ['1919', 'VS'], ['8096', 'ZH'],
		['4808', 'AG'], ['4807', 'AG'], ['8011', 'ZH'], ['8060', 'ZH'], ['4809', 'AG'], ['8059', 'ZH'], ['3017', 'BE'],
		['9301', 'SG'], ['8074', 'ZH'], ['3029', 'BE'], ['8012', 'ZH'], ['8970', 'ZH'], ['9023', 'SG'], ['1953', 'VS'],
		['8030', 'ZH'], ['4604', 'SO'], ['2305', 'NE'], ['4028', 'BS'], ['8509', 'TG'], ['8403', 'ZH'], ['6302', 'ZG'],
		['3802', 'BE'], ['8025', 'ZH'], ['8015', 'ZH'], ['4605', 'SO'], ['6591', 'TI'], ['7200', 'GR'], ['1960', 'VS'],
		['4810', 'AG'], ['8018', 'ZH'], ['8017', 'ZH'], ['8920', 'ZH'], ['9021', 'SG'], ['8150', 'ZH'], ['5030', 'AG'],
		['4134', 'BL'], ['8870', 'GL'], ['8300', 'ZH'], ['6131', 'LU'], ['4135', 'BL'], ['9321', 'TG']]
	
	fehlende_plz_df = pd.DataFrame(fehlende_plz, columns=["PLZ", "Kantonskürzel"])
	# Append to the original DataFrame
	df = pd.concat([df, fehlende_plz_df], ignore_index=True)
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

# Extraktion der fehlenden PLZ Daten
""" with open("./Adressverzeichnis_Post", "r", encoding="latin1") as f:
    lines = [line for line in f if line.startswith("01;")] # nur die sind relevant

# Create an in-memory text buffer
data = io.StringIO("".join(lines))

# Read with pandas
ndf = pd.read_csv(
    data,
    sep=";",
    header=None,
    engine="python",
    dtype=str
)
ndf = ndf[[4, 8, 9]] # 4 ist plz, 8 ist Ortschaftsname und 9 ist Kantonskürzel
mdf = ndf[~ndf[4].isin(df["PLZ"].astype(str))]
mdf = mdf.drop_duplicates(subset=[4, 9], keep='first')
mdf = mdf[~mdf[9].isin(["FL", "IT"])] # drop Liechtenstein and Italien
mdf.loc[mdf[8] == 'Büsingen', 9] = 'SH'
mdf = mdf[[4,9]]
fehlende_plz = mdf.values.tolist()
 """

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