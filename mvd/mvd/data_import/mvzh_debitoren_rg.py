# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import pandas as pd
from tqdm import tqdm
from frappe.utils.data import getdate
from frappe.utils import cint
import re

'''
    Import offene Debitoren (Rechnugen) MVZH
    -----------------
    Prod:
    sudo bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_debitoren_rg.import_from_file --kwargs "{'file_name': 'xyz.csv'}"
    Test:
    sudo bench --site test-libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_debitoren_rg.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'test-libracore.mieterverband.ch'}"
    Alte Dev VM (Oracle):
    bench execute mvd.mvd.data_import.mvzh_debitoren_rg.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'site1.local', 'bench': 'frappe', 'create_missing_users':1}"
    Multi-Bench VM:
    bench execute mvd.mvd.data_import.mvzh_debitoren_rg.import_from_file --kwargs "{'file_name': 'xyz.csv', 'site_name': 'mvd', 'bench': 'mvd'}"
'''
def import_from_file(file_name, site_name='libracore.mieterverband.ch', bench='frappe'):
    # display all coloumns for error handling
    pd.set_option('display.max_rows', None, 'display.max_columns', None)
    # read csv
    df = pd.read_csv('/home/frappe/{bench}-bench/sites/{site_name}/private/files/{file_name}'.format(site_name=site_name, file_name=file_name, bench=bench), sep=";", dtype=str, keep_default_na=False)

    print("Starte Import...")
    for index, row in tqdm(df.iterrows(), desc="Import Debitoren", unit=" Debitoren", total=len(df.index)):
        if frappe.db.exists("Mitgliedschaft", get_value(row, 'MitgliederID')):
            mitglied = frappe.get_doc("Mitgliedschaft", get_value(row, 'MitgliederID'))
            sinv = frappe.new_doc("Sales Invoice")
            # sinv.title = "Yves Roth Fotograf"
            sinv.naming_series = "R-.{sektions_code}.#####"
            sinv.customer = mitglied.kunde_mitglied if not mitglied.rg_kunde else mitglied.rg_kunde
            # sinv.customer_name = "Yves Roth Fotograf"
            sinv.tax_id = None
            sinv.is_pos = 0
            sinv.pos_profile = None
            sinv.offline_pos_name = None
            sinv.is_return = 0
            sinv.company = "MV Zürich"
            sinv.posting_date = getdate(get_value(row, 'Rechnungsdatum'))
            sinv.set_posting_time = 1
            sinv.due_date = getdate("2026-01-01")
            sinv.delivery_date = None
            sinv.payment_reminder_level = 0
            sinv.exclude_from_payment_reminder_until = None
            sinv.amended_from = None
            sinv.ist_mitgliedschaftsrechnung = 1
            sinv.ist_hv_rechnung = 0
            sinv.ist_spenden_rechnung = 0
            sinv.ist_sonstige_rechnung = 0
            sinv.manueller_rechnungstext = 0
            sinv.ohne_betrag = 0
            sinv.mv_kunde = None
            sinv.manuelle_adresseingabe = 0
            sinv.ma_name = None
            sinv.ma_adressen_zusatzzeile = None
            sinv.ma_strasse = None
            sinv.ma_nummer = None
            sinv.ma_plz = None
            sinv.ma_ort = None
            sinv.ma_laendercode = None
            sinv.manuelle_adresse = None
            sinv.mv_mitgliedschaft = get_value(row, 'MitgliederID')
            sinv.sektion_id = "MVZH"
            sinv.sektions_code = "33"
            sinv.mitgliedschafts_jahr = 2026
            sinv.druckvorlage = "Jahresrechnung Wohnen-MVZH" if "Wohnen" in get_value(row, 'Mitgliedertyp') else "Jahresrechnung MV Business-MVZH" if "Business" in get_value(row, 'Mitgliedertyp') else "Jahresrechnung Wohnen-MVZH"
            sinv.zugehoerige_fr = None
            sinv.rechnungs_jahresversand = None
            sinv.mrj = None
            sinv.mrj_sektions_selektion = None
            sinv.fast_mode = 0
            sinv.renaming_series = None
            sinv.druckvorlage_email = None
            sinv.druckvorlage_digitalrechnung = None
            sinv.mrj_pdf_erstellt = 0
            sinv.mrj_email_versendet = 0
            sinv.return_against = None
            sinv.update_billed_amount_in_sales_order = 0
            sinv.project = None
            sinv.cost_center = "Main - MVZH"
            sinv.po_no = None
            sinv.po_date = None
            sinv.customer_address = mitglied.adresse_mitglied if not mitglied.rg_adresse else mitglied.rg_adresse
            sinv.contact_person = mitglied.kontakt_mitglied if not mitglied.rg_kontakt else mitglied.rg_kontakt
            sinv.territory = "All Territories"
            sinv.shipping_address_name = mitglied.adresse_mitglied if not mitglied.rg_adresse else mitglied.rg_adresse
            sinv.company_address = "MV Zürich-Billing"
            sinv.currency = "CHF"
            sinv.conversion_rate = 1.0
            sinv.selling_price_list = "Standard Selling"
            sinv.price_list_currency = "CHF"
            sinv.plc_conversion_rate = 1.0
            sinv.ignore_pricing_rule = 0
            sinv.set_warehouse = None
            sinv.update_stock = 0
            sinv.scan_barcode = None
            sinv.taxes_and_charges = None
            sinv.shipping_rule = None
            sinv.tax_category = ""
            sinv.redeem_loyalty_points = 0
            sinv.loyalty_program = None
            sinv.loyalty_redemption_account = None
            sinv.loyalty_redemption_cost_center = None
            sinv.apply_discount_on = "Grand Total"
            sinv.additional_discount_percentage = 0
            sinv.discount_amount = 0
            sinv.allocate_advances_automatically = 0
            sinv.payment_terms_template = None
            sinv.cash_bank_account = None
            sinv.paid_amount = 0
            sinv.change_amount = 0
            sinv.account_for_change_amount = None
            sinv.write_off_amount = 0
            sinv.write_off_outstanding_amount_automatically = 0
            sinv.write_off_account = None
            sinv.write_off_cost_center = None
            sinv.tc_name = None
            sinv.terms = None
            sinv.letter_head = None
            sinv.group_same_items = 0
            sinv.language = "en"
            sinv.select_print_heading = None
            sinv.inter_company_invoice_reference = None
            sinv.customer_group = "All Customer Groups"
            sinv.campaign = None
            sinv.is_discounted = 0
            sinv.debit_to = "1310 - Debtors - MVZH"
            sinv.party_account_currency = "CHF"
            sinv.is_opening = "No"
            sinv.c_form_applicable = "No"
            sinv.c_form_no = None
            sinv.remarks = "No Remarks"
            sinv.sales_partner = None
            sinv.commission_rate = 0
            sinv.from_date = None
            sinv.to_date = None
            sinv.auto_repeat = None
            sinv.against_income_account = "Mitgliederbeiträge - MVZH"
            sinv.esr_reference = get_value(row, 'Referenznummer')
            sinv.esr_code = None
            sinv.is_proposed = 0
            sinv.enable_lsv = 0
            sinv.exported_to_abacus = 0
            sinv.mvzh_sinv_nr = get_value(row, 'Rechnungsnummer')
            sinv.mvzh_sinv_iban = None
            item = sinv.append("items", {})
            item.barcode = None
            item.item_code = "MVZH-MP" if "Wohnen" in get_value(row, 'Mitgliedertyp') else "MVZH-MG" if "Business Standard" in get_value(row, 'Mitgliedertyp') else "MVZH-MM" if "Business Mini" in get_value(row, 'Mitgliedertyp') else "MVZH-MP"
            # item.item_name = "Mitgliedschaft Geschäft"
            item.customer_item_code = None
            # item.description = "Mitgliedschaft Geschäft"
            item.remarks = None
            # item.item_group = "Vereinsmitgliedschaft"
            item.brand = None
            item.image = ""
            item.qty = 1
            item.stock_uom = "Jahr"
            item.uom = "Jahr"
            item.conversion_factor = 1
            item.stock_qty = 1
            item.price_list_rate = get_value(row, 'Betrag offen')
            item.rate = get_value(row, 'Betrag offen')
            item.margin_type = ""
            item.margin_rate_or_amount = 0
            item.rate_with_margin = 0
            item.discount_percentage = 0
            item.discount_amount = 0
            item.item_tax_template = None
            item.pricing_rules = None
            item.is_free_item = 0
            item.delivered_by_supplier = 0
            # item.income_account = "Mitgliederbeiträge - MVZH"
            item.is_fixed_asset = 0
            item.asset = None
            item.finance_book = None
            item.expense_account = None
            item.deferred_revenue_account = None
            item.service_stop_date = None
            item.enable_deferred_revenue = 0
            item.service_start_date = None
            item.service_end_date = None
            item.weight_per_unit = 0
            item.weight_uom = None
            item.warehouse = None
            item.target_warehouse = None
            item.quality_inspection = None
            item.batch_no = None
            item.allow_zero_valuation_rate = 0
            item.serial_no = None
            item.item_tax_rate = "{}"
            item.sales_order = None
            item.so_detail = None
            item.mitgliedschaft = None
            item.timesheet = None
            item.ts_detail = None
            item.delivery_note = None
            item.dn_detail = None
            item.cost_center = "Main - MVZH"

            sinv.insert(ignore_permissions=True)
            sinv.submit()
            frappe.db.commit()

def get_value(row, value):
    value = row[value]
    return value.strip()