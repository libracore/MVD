# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import add_days, today, now
from frappe.utils.csvutils import to_csv as make_csv

class Spendenversand(Document):
    def validate(self):
        if int(self.sektionsspezifisch) == 1 and not self.sektion_id:
            frappe.throw("Bitte wählen Sie eine Sektion aus.")
        if int(self.sprachspezifisch) == 1 and not self.sprache:
            frappe.throw("Bitte wählen Sie eine Sprache aus.")
        if int(self.mitgliedtypspezifisch) == 1 and not self.mitgliedtyp:
            frappe.throw("Bitte wählen Sie einen Mitgliedtyp aus.")
        if int(self.regionsspezifisch) == 1 and not self.region:
            frappe.throw("Bitte wählen Sie eine Region aus.")
    
    def before_submit(self):
        if self.status == 'Neu':
            self.status = 'Vorgemerkt'

def spenden_versand(doc):
    fr_list = []
    try:
        sektion = ''
        sprache = ''
        mitgliedtyp = ''
        region = ''
        keine_gesperrten_adressen = ''
        keine_kuendigungen = ''
        if int(doc.sektionsspezifisch) == 1:
            sektion = """ AND `sektion_id` = '{sektion_id}'""".format(sektion_id=doc.sektion_id)
        if int(doc.sprachspezifisch) == 1:
            sprache = """ AND `language` = '{sprache}'""".format(sprache=doc.sprache)
        if int(doc.mitgliedtypspezifisch) == 1:
            mitgliedtyp = """ AND `mitgliedtyp_c` = '{mitgliedtyp}'""".format(mitgliedtyp=doc.mitgliedtyp)
        if int(doc.regionsspezifisch) == 1:
            region = """ AND `region` = '{region}'""".format(region=doc.region)
        if int(doc.inkl_gesperrt) == 1:
            keine_gesperrten_adressen = """ AND `adressen_gesperrt` != 1"""
        if int(doc.keine_kuendigungen) == 1:
            keine_kuendigungen = """ AND (`kuendigung` < '2000-01-01' OR `kuendigung` IS NULL)"""
        
        mitgliedschaften = frappe.db.sql("""SELECT
                                                `name`
                                            FROM `tabMitgliedschaft`
                                            WHERE `status_c` = 'Regulär'
                                            {sektion}{sprache}{mitgliedtyp}{region}{keine_gesperrten_adressen}{keine_kuendigungen}""".format(sektion=sektion, \
                                                                                                                                            sprache=sprache, \
                                                                                                                                            mitgliedtyp=mitgliedtyp, \
                                                                                                                                            region=region, \
                                                                                                                                            keine_gesperrten_adressen=keine_gesperrten_adressen, \
                                                                                                                                            keine_kuendigungen=keine_kuendigungen), as_dict=True)
        
        for mitgliedschaft_name in mitgliedschaften:
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft_name.name)
            sektion = frappe.get_doc("Sektion", mitgliedschaft.sektion_id)
            fr = frappe.get_doc({
                "doctype": "Fakultative Rechnung",
                "mv_mitgliedschaft": mitgliedschaft.name,
                'due_date': add_days(today(), 30),
                'sektion_id': str(sektion.name),
                'sektions_code': str(sektion.sektion_id) or '00',
                'sales_invoice': '',
                'typ': 'Spende (Spendenversand)',
                'betrag': 0.00,
                'posting_date': today(),
                'company': sektion.company,
                'druckvorlage': '',
                'spenden_versand': doc.name
            })
            fr.insert(ignore_permissions=True)
            
            fr.submit()
            fr_list.append(fr.name)
        
        create_sammel_csv(fr_list, doc)
        
        doc.status = 'Abgeschlossen'
        doc.save()
    except Exception as err:
        doc.status = 'Fehlgeschlagen'
        doc.save()
        doc.add_comment('Comment', text='Fehler:<br>{0}'.format(err))
        
        if len(fr_list) > 0:
            for fr_doc in fr_list:
                fr = frappe.get_doc("Fakultative Rechnung", fr_doc)
                fr.cancel()
                fr.delete()

def create_sammel_csv(fr_list, spenden_versand):
    csv_data = get_csv_data(fr_list)

    csv_file = make_csv(csv_data)

    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": "spendenversand_{datetime}.csv".format(datetime=now().replace(" ", "_")),
        "folder": "Home/Attachments",
        "is_private": 1,
        "content": csv_file,
        "attached_to_doctype": 'Spendenversand',
        "attached_to_name": spenden_versand.name
    })
    _file.save()

    return

def get_csv_data(fr_list):
    data = []
    titel = [
        'firma',
        'zusatz_firma',
        'anrede',
        'vorname_1',
        'nachname_1',
        'vorname_2',
        'nachname_2',
        'zusatz_adresse',
        'strasse',
        'postfach',
        'postfach_plz',
        'postfach_ort',
        'plz',
        'ort',
        'betrag_1',
        'ref_nr_1',
        'kz_1',
        'faktura_nr',
        'mitglied_nr',
        'jahr_ausweis',
        'mitgliedtyp_c',
        'sektion_c',
        'region_c',
        'hat_email',
        'mahnung',
        'zeilen_art',
        'ausweis_vorname_1',
        'ausweis_nachname_1',
        'ausweis_vorname_2',
        'ausweis_nachname_2'
    ]
    data.append(titel)

    for fr_doc in fr_list:
        fr = frappe.get_doc("Fakultative Rechnung", fr_doc)
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", fr.mv_mitgliedschaft)
        
        # adressdaten
        strasse = mitgliedschaft.strasse or ''
        nummer = " " + mitgliedschaft.nummer if mitgliedschaft.nummer else ''
        nummer_zu = " " + mitgliedschaft.nummer_zu if mitgliedschaft.nummer_zu else ''
        zusatz_adresse = mitgliedschaft.zusatz_adresse or ''
        if int(mitgliedschaft.postfach) == 1:
            postfach = 'Postfach {pf}'.format(pf=mitgliedschaft.postfach_nummer or '')
        else:
            postfach = ''
        postfach_plz = ''
        postfach_ort = ''
        plz = mitgliedschaft.plz or ''
        ort = mitgliedschaft.ort or ''
        
        # kontaktdaten
        vorname_1 = mitgliedschaft.vorname_1 or ''
        nachname_1 = mitgliedschaft.nachname_1 or ''
        ausweis_vorname_1 = mitgliedschaft.vorname_1 or ''
        ausweis_nachname_1 = mitgliedschaft.nachname_1 or ''
        if int(mitgliedschaft.hat_solidarmitglied) == 1:
            vorname_2 = mitgliedschaft.vorname_2 or ''
            nachname_2 = mitgliedschaft.nachname_2 or ''
            ausweis_vorname_2 = mitgliedschaft.vorname_2 or ''
            ausweis_nachname_2 = mitgliedschaft.nachname_2 or ''
        else:
            vorname_2 = ''
            nachname_2 = ''
            ausweis_vorname_2 = ''
            ausweis_nachname_2 = ''
        firma = mitgliedschaft.firma or ''
        zusatz_firma = mitgliedschaft.zusatz_firma or ''
        anrede = mitgliedschaft.anrede_c or ''
        
        # allgemein
        mitglied_nr = mitgliedschaft.mitglied_nr
        jahr_ausweis = mitgliedschaft.bezahltes_mitgliedschaftsjahr if mitgliedschaft.bezahltes_mitgliedschaftsjahr > 0 else ''
        mitgliedtyp_c = mitgliedschaft.mitgliedtyp_c
        sektion_c = mitgliedschaft.sektion_id
        region_c = mitgliedschaft.region or ''
        hat_email = 1 if mitgliedschaft.e_mail_1 else 0
        
        # rechnungsdaten
        betrag_1 = 0.00
        mahnung = 0
        zeilen_art = 'R'
        ref_nr_1 = fr.qrr_referenz
        kz_1 = fr.qrr_referenz
        faktura_nr = fr.name
            
        _data = [
            firma,
            zusatz_firma,
            anrede,
            vorname_1,
            nachname_1,
            vorname_2,
            nachname_2,
            zusatz_adresse,
            strasse + nummer + nummer_zu,
            postfach,
            postfach_plz,
            postfach_ort,
            plz,
            ort,
            betrag_1,
            ref_nr_1,
            kz_1,
            faktura_nr,
            mitglied_nr,
            jahr_ausweis,
            mitgliedtyp_c,
            sektion_c,
            region_c,
            hat_email,
            mahnung,
            zeilen_art,
            ausweis_vorname_1,
            ausweis_nachname_1,
            ausweis_vorname_2,
            ausweis_nachname_2
        ]
        data.append(_data)

    return data
