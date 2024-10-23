# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.csvutils import to_csv as make_csv
from frappe.utils.data import now, add_days, today
from mvd.mvd.utils.manuelle_rechnungs_items import get_item_price
from frappe.utils.background_jobs import enqueue
from mvd.mvd.utils.qrr_reference import get_qrr_reference
from frappe.utils import cint
import json

def create_invoices_as_json(jahresversand):
    jahresversand_doc = frappe.get_doc("Rechnungs Jahresversand", jahresversand)
    rjv_json = frappe.get_doc({'doctype': "RJV JSON"}).insert(ignore_permissions=True)
    if jahresversand_doc.status not in ['Abgeschlossen', 'Fehlgeschlagen', 'Storniert']:
        jahresversand_doc.status = 'Rechnungsdaten in Arbeit'
        jahresversand_doc.rechnungsdaten_json_link = rjv_json.name
        jahresversand_doc.add_comment('Comment', text='Beginne mit Rechnungsdaten Erzeugung...')
        jahresversand_doc.save()
        frappe.db.commit()
        
        sinv_list = []
        sektion = frappe.get_doc("Sektion", jahresversand_doc.sektion_id)
        company = frappe.get_doc("Company", sektion.company)
        due_date = add_days(today(), 30)
        item_defaults = {
            'Privat': [{"item_code": sektion.mitgliedschafts_artikel,"qty": 1, "cost_center": company.cost_center, "rate": get_item_price(sektion.mitgliedschafts_artikel).get("price")}],
            'Geschäft': [{"item_code": sektion.mitgliedschafts_artikel_geschaeft,"qty": 1, "cost_center": company.cost_center, "rate": get_item_price(sektion.mitgliedschafts_artikel).get("price")}]
        }
        current_series_index = (frappe.db.get_value("Series", "RJ-{0}".format(str(sektion.sektion_id) or '00'), "current", order_by = "name") or 0) + 1
        current_fr_series_index = (frappe.db.get_value("Series", "FRJ-{0}".format(str(sektion.sektion_id) or '00'), "current", order_by = "name") or 0) + 1

        filters = ''
        if int(jahresversand_doc.sprach_spezifisch) == 1:
            filters += """ AND `language` = '{language}'""".format(language=jahresversand_doc.language)
        if int(jahresversand_doc.mitgliedtyp_spezifisch) == 1:
            filters += """ AND `mitgliedtyp_c` = '{mitgliedtyp}'""".format(mitgliedtyp=jahresversand_doc.mitgliedtyp)
        if int(jahresversand_doc.region_spezifisch) == 1:
            filters += """ AND `region` = '{region}'""".format(region=jahresversand_doc.region)
        
        mitgliedschaften = frappe.db.sql("""SELECT
                                                `name`,
                                                `ist_geschenkmitgliedschaft`,
                                                `reduzierte_mitgliedschaft`,
                                                `reduzierter_betrag`,
                                                `rg_kunde`,
                                                `kunde_mitglied`,
                                                `kontakt_mitglied`,
                                                `rg_adresse`,
                                                `adresse_mitglied`,
                                                `rg_kontakt`,
                                                `bezahltes_mitgliedschaftsjahr`,
                                                `mitgliedtyp_c`
                                            FROM `tabMitgliedschaft`
                                            WHERE `sektion_id` = '{sektion_id}'
                                            AND `status_c` = 'Regulär'
                                            AND `name` NOT IN (
                                                SELECT
                                                    `mv_mitgliedschaft`
                                                FROM `tabSales Invoice`
                                                WHERE `mitgliedschafts_jahr` = '{mitgliedschafts_jahr}'
                                                AND `ist_mitgliedschaftsrechnung` = 1
                                                AND `docstatus` = 1)
                                            AND `name` NOT IN (
                                                SELECT
                                                    `mv_mitgliedschaft`
                                                FROM `tabSales Invoice`
                                                WHERE `rechnungs_jahresversand` = '{jahresversand}'
                                                AND `docstatus` = 1)
                                            AND (`kuendigung` IS NULL or `kuendigung` > '{mitgliedschafts_jahr}-12-31')
                                            AND `bezahltes_mitgliedschaftsjahr` < {mitgliedschafts_jahr}
                                            {filters}""".format(sektion_id=jahresversand_doc.sektion_id, jahresversand=jahresversand, mitgliedschafts_jahr=jahresversand_doc.jahr, filters=filters), as_dict=True)
        
        try:
            rg_loop = 1
            for mitgliedschaft in mitgliedschaften:
                # ------------------------------------------------------------------------------------
                # ------------------------------------------------------------------------------------
                '''
                    Geschenkmitgliedschaften sowie Gratis Mitgliedschaften werden NICHT berücksichtigt
                '''
                # ------------------------------------------------------------------------------------
                skip = False
                if int(mitgliedschaft.ist_geschenkmitgliedschaft) == 1:
                    skip = True
                if int(mitgliedschaft.reduzierte_mitgliedschaft) == 1 and not mitgliedschaft.reduzierter_betrag > 0:
                    skip = True
                # ------------------------------------------------------------------------------------
                # ------------------------------------------------------------------------------------
                
                if not skip:
                    if not mitgliedschaft.rg_kunde:
                        customer = mitgliedschaft.kunde_mitglied
                        contact = mitgliedschaft.kontakt_mitglied
                        if not mitgliedschaft.rg_adresse:
                            address = mitgliedschaft.adresse_mitglied
                        else:
                            address = mitgliedschaft.rg_adresse
                    else:
                        customer = mitgliedschaft.rg_kunde
                        address = mitgliedschaft.rg_adresse
                        contact = mitgliedschaft.rg_kontakt
                    
                    item = item_defaults.get(mitgliedschaft.mitgliedtyp_c)
                    if cint(mitgliedschaft.reduzierte_mitgliedschaft) == 1 and mitgliedschaft.reduzierter_betrag > 0:
                        item[0]["rate"] = mitgliedschaft.reduzierter_betrag
                    
                    sinv = frappe.get_doc({
                        "doctype": "Sales Invoice",
                        "ist_mitgliedschaftsrechnung": 1,
                        "mv_mitgliedschaft": mitgliedschaft.name,
                        "company": sektion.company,
                        "cost_center": company.cost_center,
                        "customer": customer,
                        "customer_address": address,
                        "contact_person": contact,
                        'mitgliedschafts_jahr': jahresversand_doc.jahr,
                        'due_date': due_date,
                        'debit_to': company.default_receivable_account,
                        'sektions_code': str(sektion.sektion_id) or '00',
                        'sektion_id': jahresversand_doc.sektion_id,
                        "items": item,
                        "druckvorlage": jahresversand_doc.druckvorlage if jahresversand_doc.druckvorlage else '',
                        "exclude_from_payment_reminder_until": '',
                        "rechnungs_jahresversand": jahresversand_doc.name,
                        "allocate_advances_automatically": 1,
                        "fast_mode": 1,
                        "esr_reference": '',
                        "outstanding_amount": item[0].get("rate"),
                        "naming_series": "RJ-.{sektions_code}.#####",
                        "renaming_series": "RJ-{0}{1}".format(str(sektion.sektion_id) or '00', str(current_series_index).rjust(5, "0"))
                    })
                    sinv.esr_reference = get_qrr_reference(fake_sinv=sinv)

                    fr = frappe.get_doc({
                        "doctype": "Fakultative Rechnung",
                        "mv_mitgliedschaft": mitgliedschaft.name,
                        'due_date': due_date,
                        'sektion_id': jahresversand_doc.sektion_id,
                        'sektions_code': str(sektion.sektion_id) or '00',
                        'sales_invoice': "RJ-{0}{1}".format(str(sektion.sektion_id) or '00', str(current_series_index).rjust(5, "0")),
                        'typ': 'HV',
                        'betrag': sektion.betrag_hv,
                        'posting_date': today(),
                        'company': sektion.company,
                        'druckvorlage': '',
                        'bezugsjahr': jahresversand_doc.jahr,
                        'spenden_versand': '',
                        "naming_series": "FRJ-.{sektions_code}.#####",
                        "renaming_series": "FRJ-{0}{1}".format(str(sektion.sektion_id) or '00', str(current_fr_series_index).rjust(5, "0"))
                    })
                    fr.qrr_referenz = get_qrr_reference(fake_fr=fr)

                    sinv_list.append([sinv.as_json(), fr.as_json()])
                    current_series_index += 1
                    current_fr_series_index += 1
            
            json_data = json.dumps(sinv_list, indent=2)
            rjv_json.rechnungsdaten_json = json_data
            rjv_json.save(ignore_permissions=True)
            jahresversand_doc.add_comment('Comment', text='Rechnungsdaten erstellt.')
            frappe.db.commit()

            create_csv_from_json(jahresversand_doc.name)
            
        except Exception as err:
            jahresversand_doc = frappe.get_doc("Rechnungs Jahresversand", jahresversand)
            jahresversand_doc.status = 'Fehlgeschlagen'
            jahresversand_doc.save()
            jahresversand_doc.add_comment('Comment', text='{0}'.format(str(err)))

def create_invoices_from_json(jahresversand):
    jahresversand_doc = frappe.get_doc("Rechnungs Jahresversand", jahresversand)
    rjv_json = frappe.get_doc("RJV JSON", jahresversand_doc.rechnungsdaten_json_link)
    retry = True if cint(jahresversand_doc.is_retry) == 1 else False
    sektion = frappe.get_doc("Sektion", jahresversand_doc.sektion_id)
    current_series_index = frappe.db.get_value("Series", "RJ-{0}".format(str(sektion.sektion_id) or '00'), "current", order_by = "name") or 0
    current_fr_series_index = frappe.db.get_value("Series", "FRJ-{0}".format(str(sektion.sektion_id) or '00'), "current", order_by = "name") or 0
    if jahresversand_doc.status == 'Vorgemerkt für Rechnungsverbuchung':
        jahresversand_doc.status = 'Rechnungsverbuchung in Arbeit'
        jahresversand_doc.add_comment('Comment', text='Beginne mit der Rechnungsverbuchung...')
        jahresversand_doc.save()
        frappe.db.commit()
        if retry:
            _already_created = frappe.db.sql("""SELECT `esr_reference` FROM `tabSales Invoice` WHERE `rechnungs_jahresversand` = '{0}'""".format(jahresversand), as_dict=True)
            already_created = [ac.esr_reference for ac in _already_created]
        try:
            invoices = json.loads(rjv_json.rechnungsdaten_json)
            sinv_counter = 0
            fr_counter = 0
            commit_counter = 0
            for invoice in invoices:
                skip = False
                sinv_doc = json.loads(invoice[0])
                if retry:
                    # if frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabSales Invoice` WHERE `esr_reference` = '{0}'""".format(sinv_doc.get("esr_reference")), as_dict=True)[0].qty > 0:
                    #     skip = True
                    if sinv_doc.get("esr_reference") in already_created:
                        skip = True
                if not skip:
                    sinv = frappe.get_doc(sinv_doc)
                    sinv.insert(ignore_permissions=True)
                    
                    sinv.docstatus = 1
                    sinv.save(ignore_permissions=True)
                    if sinv.name != sinv.renaming_series:
                        frappe.rename_doc("Sales Invoice", sinv.name, sinv.renaming_series, force=True)
                    

                    fr = frappe.get_doc(json.loads(invoice[1]))
                    fr.insert(ignore_permissions=True)
                    
                    fr.docstatus = 1
                    fr.save(ignore_permissions=True)
                    if fr.name != fr.renaming_series:
                        frappe.rename_doc("Fakultative Rechnung", fr.name, fr.renaming_series, force=True)
                    

                    commit_counter += 1
                    if commit_counter == 100:
                        frappe.db.commit()
                        commit_counter = 0
                sinv_counter += 1
                fr_counter += 1
            
            frappe.db.sql("""UPDATE `tabSeries` SET `current` = {0} WHERE `name` = 'RJ-{1}'""".format(current_series_index + sinv_counter, str(sektion.sektion_id) or '00'))
            frappe.db.sql("""UPDATE `tabSeries` SET `current` = {0} WHERE `name` = 'FRJ-{1}'""".format(current_fr_series_index + fr_counter, str(sektion.sektion_id) or '00'))
            jahresversand_doc.status = 'Abgeschlossen'
            jahresversand_doc.save()
            frappe.db.sql("""SET SQL_SAFE_UPDATES = 0;""", as_list=True)
            frappe.db.sql("""UPDATE `tabSales Invoice` SET `fast_mode` = 0 WHERE `rechnungs_jahresversand` = '{0}'""".format(jahresversand_doc.name), as_list=True)
            frappe.db.sql("""SET SQL_SAFE_UPDATES = 1;""", as_list=True)
        
        except Exception as err:
            jahresversand_doc.status = 'Fehlgeschlagen'
            jahresversand_doc.save()
            jahresversand_doc.add_comment('Comment', text='{0}'.format(str(err)))

def create_csv_from_json(jahresversand):
    jahresversand = frappe.get_doc("Rechnungs Jahresversand", jahresversand)
    rjv_json = frappe.get_doc("RJV JSON", jahresversand.rechnungsdaten_json_link)
    jahresversand.status = 'CSV in Arbeit'
    jahresversand.add_comment('Comment', text='Beginne mit CSV Erzeugung...')
    jahresversand.save()
    frappe.db.commit()
    try:
        data = []
        header = [
            'firma',
            'zusatz_firma',
            'anrede',
            'briefanrede',
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
            'bezahlt_fuer_firma',
            'bezahlt_fuer_name',
            'bezahlt_von_firma',
            'bezahlt_von_name',
            'spezielles'
        ]
        data.append(header)
        
        rechnungen = json.loads(rjv_json.rechnungsdaten_json)
        for _rechnung in rechnungen:
            rechnung = json.loads(_rechnung[0])
            hv = json.loads(_rechnung[1])
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", rechnung.get("mv_mitgliedschaft"))
            
            # ------------------------------------------------------------------------------------
            # ------------------------------------------------------------------------------------
            '''
                Geschenkmitgliedschaften sowie Gratis Mitgliedschaften werden NICHT berücksichtigt
            '''
            # ------------------------------------------------------------------------------------
            skip = False
            if mitgliedschaft.ist_geschenkmitgliedschaft:
                skip = True
            if mitgliedschaft.reduzierte_mitgliedschaft and not mitgliedschaft.reduzierter_betrag > 0:
                skip = True
            # ------------------------------------------------------------------------------------
            # ------------------------------------------------------------------------------------
            
            if not skip:
                row_data = []
                pseudo_zeile = False
                
                if mitgliedschaft.unabhaengiger_debitor and mitgliedschaft.abweichende_rechnungsadresse:
                    # fremdzahler
                    if mitgliedschaft.rg_kundentyp == 'Unternehmen':
                        row_data.append(mitgliedschaft.rg_firma or '')
                        row_data.append(mitgliedschaft.rg_zusatz_firma or '')
                    else:
                        row_data.append("")
                        row_data.append("")
                    row_data.append(mitgliedschaft.rg_anrede or '')
                    row_data.append(mitgliedschaft.rg_briefanrede or '')
                    row_data.append(mitgliedschaft.rg_vorname or '')
                    row_data.append(mitgliedschaft.rg_nachname or '')
                    row_data.append("")
                    row_data.append("")
                else:
                    # selbstzahler
                    if mitgliedschaft.kundentyp == 'Unternehmen':
                        row_data.append(mitgliedschaft.firma or '')
                        row_data.append(mitgliedschaft.zusatz_firma or '')
                    else:
                        row_data.append("")
                        row_data.append("")
                    row_data.append(mitgliedschaft.anrede_c or '')
                    row_data.append(mitgliedschaft.rg_briefanrede or '')
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
                        row_data.append("Postfach {0}".format(mitgliedschaft.rg_postfach_nummer or ''))
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
                        row_data.append("Postfach {0}".format(mitgliedschaft.postfach_nummer or ''))
                        row_data.append("")
                        row_data.append("")
                    else:
                        row_data.append("")
                        row_data.append("")
                        row_data.append("")
                    row_data.append(mitgliedschaft.plz or '')
                    row_data.append(mitgliedschaft.ort or '')
                row_data.append(rechnung.get("outstanding_amount") or 0.00)
                row_data.append(rechnung.get("esr_reference") or '')
                row_data.append('')
                row_data.append(hv.get("betrag") or 0.00)
                row_data.append(hv.get("qrr_referenz") or '')
                row_data.append('')
                row_data.append(rechnung.get("renaming_series") or '')
                
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
                
                if mitgliedschaft.unabhaengiger_debitor:
                    pseudo_zeile = True
                    if mitgliedschaft.kundentyp == 'Unternehmen':
                        # bezahlt_fuer_firma
                        bezahlt_fuer_firma = mitgliedschaft.firma or ''
                        bezahlt_fuer_firma += ' ' if mitgliedschaft.firma else ''
                        bezahlt_fuer_firma += mitgliedschaft.zusatz_firma or ''
                        row_data.append(bezahlt_fuer_firma)
                        # bezahlt_fuer_name
                        bezahlt_fuer_name = mitgliedschaft.anrede_c or ''
                        bezahlt_fuer_name += ' ' if mitgliedschaft.anrede_c else ''
                        bezahlt_fuer_name += mitgliedschaft.vorname_1 or ''
                        bezahlt_fuer_name += ' ' if mitgliedschaft.vorname_1 else ''
                        bezahlt_fuer_name += mitgliedschaft.nachname_1 or ''
                        row_data.append(bezahlt_fuer_name)
                    else:
                        # bezahlt_fuer_name
                        row_data.append('')
                        bezahlt_fuer_name = mitgliedschaft.anrede_c or ''
                        bezahlt_fuer_name += ' ' if mitgliedschaft.anrede_c else ''
                        bezahlt_fuer_name += mitgliedschaft.vorname_1 or ''
                        bezahlt_fuer_name += ' ' if mitgliedschaft.vorname_1 else ''
                        bezahlt_fuer_name += mitgliedschaft.nachname_1 or ''
                        row_data.append(bezahlt_fuer_name)
                else:
                    # bezahlt_fuer_firma
                    row_data.append('')
                    # bezahlt_fuer_name
                    row_data.append('')
                
                # bezahlt_von_firma
                row_data.append('')
                # bezahlt_von_name
                row_data.append('')
                
                if pseudo_zeile:
                    if mitgliedschaft.ist_geschenkmitgliedschaft:
                        row_data.append('Geschenkmitgliedschaft')
                    else:
                        row_data.append('Unabhängiger Debitor')
                else:
                    if mitgliedschaft.reduzierte_mitgliedschaft:
                        row_data.append('Reduzierte Mitgliedschaft')
                    else:
                        row_data.append('')
                
                data.append(row_data)
                
                if pseudo_zeile:
                    row_data = []
                    if mitgliedschaft.kundentyp == 'Unternehmen':
                        row_data.append(mitgliedschaft.firma or '')
                        row_data.append(mitgliedschaft.zusatz_firma or '')
                    else:
                        row_data.append("")
                        row_data.append("")
                    row_data.append(mitgliedschaft.anrede_c or '')
                    row_data.append(mitgliedschaft.briefanrede or '')
                    row_data.append(mitgliedschaft.vorname_1 or '')
                    row_data.append(mitgliedschaft.nachname_1 or '')
                    if mitgliedschaft.hat_solidarmitglied:
                        row_data.append(mitgliedschaft.vorname_2 or '')
                        row_data.append(mitgliedschaft.nachname_2 or '')
                    else:
                        row_data.append("")
                        row_data.append("")
                
                    row_data.append(mitgliedschaft.zusatz_adresse or '')
                    strasse = ''
                    strasse += mitgliedschaft.strasse or ''
                    strasse += " " + str(mitgliedschaft.nummer or '')
                    strasse += mitgliedschaft.nummer_zu or ''
                    row_data.append(strasse)
                    if mitgliedschaft.postfach:
                        row_data.append("Postfach {0}".format(mitgliedschaft.postfach_nummer or ''))
                        row_data.append("")
                        row_data.append("")
                    else:
                        row_data.append("")
                        row_data.append("")
                        row_data.append("")
                    row_data.append(mitgliedschaft.plz or '')
                    row_data.append(mitgliedschaft.ort or '')
                    
                    row_data.append('--')
                    row_data.append('--')
                    row_data.append('--')
                    row_data.append('--')
                    row_data.append('--')
                    row_data.append('--')
                    row_data.append('--')
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
                    
                    # bezahlt_fuer_firma
                    row_data.append('')
                    # bezahlt_fuer_name
                    row_data.append('')
                    
                    if mitgliedschaft.rg_kundentyp == 'Unternehmen':
                        # bezahlt_von_firma
                        bezahlt_von_firma = mitgliedschaft.rg_firma or ''
                        bezahlt_von_firma += ' ' if mitgliedschaft.rg_firma else ''
                        bezahlt_von_firma += mitgliedschaft.rg_zusatz_firma or ''
                        row_data.append(bezahlt_von_firma)
                        # bezahlt_von_name
                        bezahlt_von_name = mitgliedschaft.rg_anrede or ''
                        bezahlt_von_name += ' ' if mitgliedschaft.rg_anrede else ''
                        bezahlt_von_name += mitgliedschaft.rg_vorname or ''
                        bezahlt_von_name += ' ' if mitgliedschaft.rg_vorname else ''
                        bezahlt_von_name += mitgliedschaft.rg_nachname or ''
                        row_data.append(bezahlt_von_name)
                    else:
                        # bezahlt_von_name
                        row_data.append('')
                        bezahlt_von_name = mitgliedschaft.rg_anrede or ''
                        bezahlt_von_name += ' ' if mitgliedschaft.rg_anrede else ''
                        bezahlt_von_name += mitgliedschaft.rg_vorname or ''
                        bezahlt_von_name += ' ' if mitgliedschaft.rg_vorname else ''
                        bezahlt_von_name += mitgliedschaft.rg_nachname or ''
                        row_data.append(bezahlt_von_name)
                    
                    if mitgliedschaft.ist_geschenkmitgliedschaft:
                        row_data.append('Geschenkmitgliedschaft')
                    else:
                        if mitgliedschaft.reduzierte_mitgliedschaft:
                            row_data.append('Reduzierte Mitgliedschaft / Unabhängiger Debitor')
                        else:
                            row_data.append('Unabhängiger Debitor')
                    
                    data.append(row_data)
        
        csv_file = make_csv(data)
        file_name = "{titel}_{datetime}.csv".format(titel='Jahresversand-{sektion_id}-{jahr}'.format(sektion_id=jahresversand.sektion_id, jahr=jahresversand.jahr), datetime=now().replace(" ", "_"))
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home/Attachments",
            "is_private": 1,
            "content": csv_file,
            "attached_to_doctype": 'Rechnungs Jahresversand',
            "attached_to_name": jahresversand.name
        })
        
        _file.save()

        jahresversand.status = 'Rechnungsdaten und CSV erstellt'
        jahresversand.add_comment('Comment', text='CSV erstellt.')
        jahresversand.save()
        frappe.db.commit()
        
        return
    except frappe.DuplicateEntryError:
        jahresversand.status = 'Rechnungsdaten und CSV erstellt'
        jahresversand.add_comment('Comment', text='Identisches CSV existiert bereits.')
        jahresversand.save()
        frappe.db.commit()
        
        return