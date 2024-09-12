# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.csvutils import to_csv as make_csv
from frappe.utils.data import now, getdate, add_days, today
from mvd.mvd.utils.manuelle_rechnungs_items import get_item_price
# from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import create_mitgliedschaftsrechnung
from frappe.utils.background_jobs import enqueue
# from frappe.utils import cint
from mvd.mvd.utils.qrr_reference import get_qrr_reference
import json

def create_invoices_as_json(jahresversand):
    jahresversand_doc = frappe.get_doc("Rechnungs Jahresversand", jahresversand)
    if jahresversand_doc.status == 'Vorgemerkt':
        jahresversand_doc.status = 'In Arbeit'
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
                                            {filters} LIMIT 500""".format(sektion_id=jahresversand_doc.sektion_id, jahresversand=jahresversand, mitgliedschafts_jahr=jahresversand_doc.jahr, filters=filters), as_dict=True)
        
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

                    # if mitgliedschaft.mitgliedtyp_c == 'Privat':
                    #     item = [{"item_code": sektion.mitgliedschafts_artikel,"qty": 1, "cost_center": company.cost_center}]
                    # elif mitgliedschaft.mitgliedtyp_c == 'Geschäft':
                    #     item = [{"item_code": sektion.mitgliedschafts_artikel_geschaeft,"qty": 1, "cost_center": company.cost_center}]
                    
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
                        "esr_reference": ''
                    })
                    sinv.esr_reference = get_qrr_reference(fake_sinv=sinv)
                    sinv_list.append(sinv.as_json())
                    # frappe.throw(str(sinv.as_json()))
                    # sinv.insert(ignore_permissions=True)
                    # sinv.esr_reference = get_qrr_reference(sales_invoice=sinv.name)
                    # sinv.save(ignore_permissions=True)
                    # sinv.docstatus = 1
                    # sinv.save(ignore_permissions=True)

                if rg_loop == 10:
                    frappe.db.commit()
                    rg_loop = 1
                else:
                    rg_loop += 1
            
            frappe.db.commit()
            
            # if last:
            json_data = json.dumps(sinv_list, indent=2)
            jahresversand_doc.rechnungsdaten_json = json_data
            jahresversand_doc.status = 'Rechnungsdaten erstellt'
            jahresversand_doc.save()
            jahresversand_doc.add_comment('Comment', text='Rechnungsdaten erstellt. Beginne mit CSV...')
            frappe.db.commit()
        
            # get_csv(jahresversand)
            create_csv_from_json(jahresversand_doc.name)

            create_invoices_from_json(jahresversand_doc.name)
            
        except Exception as err:
            jahresversand_doc = frappe.get_doc("Rechnungs Jahresversand", jahresversand)
            jahresversand_doc.status = 'Fehlgeschlagen'
            jahresversand_doc.save()
            jahresversand_doc.add_comment('Comment', text='{0}'.format(str(err)))

def create_csv_from_json(jahresversand):
    return

def create_invoices_from_json(jahresversand):
    jahresversand_doc = frappe.get_doc("Rechnungs Jahresversand", jahresversand)
    if jahresversand_doc.status == 'Rechnungsdaten erstellt':
        try:
            invoices = json.loads(jahresversand_doc.rechnungsdaten_json)
            for invoice in invoices:
                sinv = frappe.get_doc(json.loads(invoice))
                sinv.insert(ignore_permissions=True)
                sinv.docstatus = 1
                sinv.save(ignore_permissions=True)
            
            jahresversand_doc.status = 'Abgeschlossen'
            jahresversand_doc.save()
            frappe.db.sql("""SET SQL_SAFE_UPDATES = 0;""", as_list=True)
            frappe.db.sql("""UPDATE `tabSales Invoice` SET `fast_mode` = 0 WHERE `rechnungs_jahresversand` = '{0}'""".format(jahresversand_doc.name), as_list=True)
            frappe.db.sql("""SET SQL_SAFE_UPDATES = 1;""", as_list=True)
        
        except Exception as err:
            jahresversand_doc.status = 'Fehlgeschlagen'
            jahresversand_doc.save()
            jahresversand_doc.add_comment('Comment', text='{0}'.format(str(err)))