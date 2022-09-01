# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.csvutils import to_csv as make_csv
from frappe.utils.data import now
from mvd.mvd.utils.manuelle_rechnungs_items import get_item_price

class RechnungsJahresversand(Document):
    pass

@frappe.whitelist()
def get_draft_csv(jahresversand=None):
    jahresversand = frappe.get_doc("Rechnungs Jahresversand", jahresversand)
    sektion = frappe.get_doc("Sektion", jahresversand.sektion_id)
    data = []
    header = [
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
        'betrag_2',
        'ref_nr_2',
        'kz_2',
        'faktura_nr',
        'mitglied_nr',
        'jahr_ausweis',
        'mitgliedtyp_c',
        'sektion_c',
        'region_c',
        'hat_email',
        'e_mail_1',
        'e_mail_2',
        'zeilen_art',
        'ausweis_vorname_1',
        'ausweis_nachname_1',
        'ausweis_vorname_2',
        'ausweis_nachname_2',
        'bezahlt_fuer'
    ]
    data.append(header)
    
    mitgliedschaften = frappe.db.sql("""SELECT
                                            `name`
                                        FROM `tabMitgliedschaft`
                                        WHERE `sektion_id` = '{sektion_id}'
                                        AND `status_c` = 'Regulär'
                                        AND `name` NOT IN (
                                            SELECT
                                                `mv_mitgliedschaft`
                                            FROM `tabSales Invoice`
                                            WHERE `mitgliedschafts_jahr` = '{mitgliedschafts_jahr}'
                                            AND `ist_mitgliedschaftsrechnung` = 1)""".format(sektion_id=jahresversand.sektion_id, mitgliedschafts_jahr=jahresversand.jahr), as_dict=True)
    
    for _mitgliedschaft in mitgliedschaften:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", _mitgliedschaft.name)
        row_data = []
        if mitgliedschaft.kundentyp == 'Unternehmen':
            row_data.append(mitgliedschaft.firma or '')
            row_data.append(mitgliedschaft.zusatz_firma or '')
        else:
            row_data.append("")
            row_data.append("")
        row_data.append(mitgliedschaft.anrede_c or '')
        row_data.append(mitgliedschaft.vorname_1 or '')
        row_data.append(mitgliedschaft.nachname_1 or '')
        if mitgliedschaft.hat_solidarmitglied:
            row_data.append(mitgliedschaft.vorname_2 or '')
            row_data.append(mitgliedschaft.nachname_2 or '')
        else:
            row_data.append("")
            row_data.append("")
        if mitgliedschaft.abweichende_rechnungsadresse:
            row_data.append(mitgliedschaft.rg_zusatz_adresse or '')
            strasse = ''
            strasse += mitgliedschaft.rg_strasse or ''
            strasse += " " + str(mitgliedschaft.rg_nummer or '')
            strasse += mitgliedschaft.rg_nummer_zu or ''
            row_data.append(strasse)
            if mitgliedschaft.rg_postfach:
                row_data.append(mitgliedschaft.rg_postfach_nummer or '')
                row_data.append("")
                row_data.append("")
            else:
                row_data.append("")
                row_data.append("")
                row_data.append("")
            row_data.append(mitgliedschaft.rg_plz or '')
            row_data.append(mitgliedschaft.rg_ort or '')
        else:
            row_data.append(mitgliedschaft.zusatz_adresse or '')
            strasse = ''
            strasse += mitgliedschaft.strasse or ''
            strasse += " " + str(mitgliedschaft.nummer or '')
            strasse += mitgliedschaft.nummer_zu or ''
            row_data.append(strasse)
            if mitgliedschaft.postfach:
                row_data.append(mitgliedschaft.postfach_nummer or '')
                row_data.append("")
                row_data.append("")
            else:
                row_data.append("")
                row_data.append("")
                row_data.append("")
            row_data.append(mitgliedschaft.plz or '')
            row_data.append(mitgliedschaft.ort or '')
            
        # ~ sinv = frappe.get_doc("Sales Invoice", row.sales_invoice)
        row_data.append(get_invcoice_amount(mitgliedschaft, sektion))
        row_data.append('Entwurfsdaten')
        row_data.append('')
        row_data.append(get_hv_rate(mitgliedschaft, sektion))
        row_data.append('Entwurfsdaten')
        row_data.append('')
        row_data.append('Entwurfsdaten')
        row_data.append(mitgliedschaft.mitglied_nr or '')
        row_data.append(jahresversand.jahr or '')
        row_data.append(mitgliedschaft.mitgliedtyp_c or '')
        row_data.append(mitgliedschaft.sektion_id or '')
        row_data.append('')
        row_data.append('')
        row_data.append(mitgliedschaft.e_mail_1 or '')
        row_data.append(mitgliedschaft.e_mail_2 or '')
        row_data.append('')
        row_data.append(mitgliedschaft.vorname_1 or '')
        row_data.append(mitgliedschaft.nachname_1 or '')
        if mitgliedschaft.hat_solidarmitglied:
            row_data.append(mitgliedschaft.vorname_2 or '')
            row_data.append(mitgliedschaft.nachname_2 or '')
        else:
            row_data.append("")
            row_data.append("")
        row_data.append('')
        data.append(row_data)
    
    csv_file = make_csv(data)
    file_name = "DRAFT_{titel}_{datetime}.csv".format(titel='Jahresversand-{sektion_id}-{jahr}'.format(sektion_id=jahresversand.sektion_id, jahr=jahresversand.jahr), datetime=now().replace(" ", "_"))
    
    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "folder": "Home/Attachments",
        "is_private": 1,
        "content": csv_file,
        "attached_to_doctype": 'Rechnungs Jahresversand',
        "attached_to_name": jahresversand.name
    })
    
    _file.insert()
    
    return 'done'

def get_invcoice_amount(mitgliedschaft, sektion):
    if int(mitgliedschaft.reduzierte_mitgliedschaft) != 1:
        if mitgliedschaft.mitgliedtyp_c == 'Privat':
            return get_item_price(sektion.mitgliedschafts_artikel)
        elif mitgliedschaft.mitgliedtyp_c == 'Geschäft':
            return get_item_price(sektion.mitgliedschafts_artikel_geschaeft)
        else:
            return 'FEHLER'
    else:
        return mitgliedschaft.reduzierter_betrag

def get_hv_rate(mitgliedschaft, sektion):
    if mitgliedschaft.mitgliedtyp_c == 'Privat':
        return get_item_price(sektion.hv_artikel)
    else:
        return ''
