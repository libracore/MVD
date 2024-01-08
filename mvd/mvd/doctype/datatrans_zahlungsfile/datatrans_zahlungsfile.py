# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import csv
from mvd.mvd.doctype.datatrans_report.datatrans_report import create_mitgliedschaften_pro_file

class DatatransZahlungsfile(Document):
    def read_file(self):
        physical_path = "/home/frappe/frappe-bench/sites/{0}{1}".format(frappe.local.site_path.replace("./", ""), self.datatrans_file)
        with open(physical_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['AMOUNT']:
                    datatrans_entry = self.append('datatrans_entries', {})
                    datatrans_entry.transdatetime = row['TRANSDATETIME']
                    datatrans_entry.cdscount = row['CDSCOUNT']
                    datatrans_entry.bookingperiod = row['BOOKINGPERIOD']
                    datatrans_entry.kku = row['KKU']
                    datatrans_entry.vunumber = row['VUNUMBER']
                    datatrans_entry.termid = row['TERMID']
                    datatrans_entry.cardnumber = row['CARDNUMBER']
                    datatrans_entry.expiry = row['EXPIRY']
                    datatrans_entry.authocode = row['AUTHOCODE']
                    datatrans_entry.booktyp = row['BOOKTYP']
                    datatrans_entry.currency = row['CURRENCY']
                    datatrans_entry.amount = row['AMOUNT']
                    datatrans_entry.refnumber = row['REFNUMBER']
                    datatrans_entry.status = 'Open'
                else:
                    if row['TRANSDATETIME'] == 'Total number of records':
                        self.total_number_of_records = row['CDSCOUNT']
                    elif row['TRANSDATETIME'] == 'Total number of debits':
                        self.total_number_of_debits = row['CDSCOUNT']
                    elif row['TRANSDATETIME'] == 'Total number of credits':
                        self.total_number_of_credits = row['CDSCOUNT']
                    elif row['TRANSDATETIME'] == 'Total debit amount':
                        self.total_debit_amount = row['CDSCOUNT']
                    elif row['TRANSDATETIME'] == 'Total credit amount':
                        self.total_credit_amount = row['CDSCOUNT']
                    elif row['TRANSDATETIME'] == 'Total settlement amount':
                        self.total_settlement_amount = row['CDSCOUNT']
                
        self.save()
    
    def process_data(self):
        for entry in self.datatrans_entries:
            if entry.status in ['Open', 'Mitglied: No Match', 'Webshop: No Match']:
                refnumber = entry.refnumber
                if refnumber:
                    if len(refnumber.split("_")) == 3:
                        if refnumber.split("_")[1] in ['MI', 'MH', 'GE', 'GW']:
                            # Mitgliedschaft
                            mitgliedschaft_lookup = frappe.db.sql("""
                                                                    SELECT
                                                                        `name`,
                                                                        `mitglied_nr`,
                                                                        `adressblock`,
                                                                        `online_haftpflicht`,
                                                                        `online_gutschrift`,
                                                                        `online_betrag`,
                                                                        `datum_online_verbucht`,
                                                                        `datum_online_gutschrift`,
                                                                        `online_payment_method`,
                                                                        `online_payment_zahlungsfile`
                                                                    FROM `tabMitgliedschaft`
                                                                    WHERE `online_payment_id` = '{refnumber}'
                                                                    ORDER BY `creation` ASC
                                                                    LIMIT 1""".format(refnumber=refnumber), as_dict=True)
                            if len(mitgliedschaft_lookup) > 0:
                                # fetch data from mitgliedschaft
                                entry.mitglied_id = mitgliedschaft_lookup[0].name
                                entry.mitglied_nr = mitgliedschaft_lookup[0].mitglied_nr
                                entry.adressblock = mitgliedschaft_lookup[0].adressblock.replace("\n", ", ")
                                entry.online_haftpflicht = mitgliedschaft_lookup[0].online_haftpflicht
                                entry.online_gutschrift = mitgliedschaft_lookup[0].online_gutschrift
                                entry.online_betrag = mitgliedschaft_lookup[0].online_betrag
                                entry.datum_online_verbucht = mitgliedschaft_lookup[0].datum_online_verbucht
                                entry.datum_online_gutschrift = mitgliedschaft_lookup[0].datum_online_gutschrift
                                entry.online_payment_method = mitgliedschaft_lookup[0].online_payment_method
                                
                                if mitgliedschaft_lookup[0].online_payment_zahlungsfile:
                                    # zu diesem Mitglied wurde bereits eine Datatrans Zahlung eingelesen
                                    entry.status = 'Mitglied: Doppelimport'
                                else:
                                    # achtung debit = D und credit = C
                                    if entry.booktyp == 'D':
                                        # Zahlung
                                        if float(entry.amount) != float(mitgliedschaft_lookup[0].online_betrag):
                                            # abweichender Betrag
                                            entry.status = 'Mitglied: Abweichender Betrag'
                                        else:
                                            # all good
                                            entry.status = 'Mitglied: Match'
                                            # update mitgliedschaft
                                            mitgl_update = frappe.db.sql("""UPDATE
                                                                                `tabMitgliedschaft`
                                                                            SET `online_payment_zahlungsfile` = '{zahlungsfile}'
                                                                            WHERE `name` = '{name}'""".format(zahlungsfile=self.name, name=mitgliedschaft_lookup[0].name), as_list=True)
                                    else:
                                        # Gutschrift
                                        entry.status = 'Mitglied: Gutschrift'
                            else:
                                entry.status = 'Mitglied: No Match'
                        else:
                            # Drucksachen
                            webshop_order_lookup = frappe.db.sql("""
                                                                    SELECT
                                                                        `name`
                                                                    FROM `tabWebshop Order`
                                                                    WHERE `online_payment_id` = '{refnumber}'
                                                                    ORDER BY `creation` ASC
                                                                    LIMIT 1""".format(refnumber=refnumber), as_dict=True)
                            if len(webshop_order_lookup) > 0:
                                webshop_order_update = frappe.db.sql("""UPDATE
                                                                            `tabWebshop Order`
                                                                        SET `online_payment_zahlungsfile` = '{zahlungsfile}'
                                                                        WHERE `name` = '{name}'""".format(zahlungsfile=self.name, name=webshop_order_lookup[0].name), as_list=True)
                                entry.webshop_order = webshop_order_lookup[0].name
                                entry.status = 'Webshop: Match'
                            else:
                                entry.status = 'Webshop: No Match'
        self.save()
    
    def reset_data(self):
        to_delete = []
        for entry in self.datatrans_entries:
            to_delete.append(entry.name)
            if entry.mitglied_id:
                # update mitgliedschaft
                mitgl_update = frappe.db.sql("""UPDATE
                                                    `tabMitgliedschaft`
                                                SET `online_payment_zahlungsfile` = NULL
                                                WHERE `name` = '{name}'""".format(name=entry.mitglied_id), as_list=True)
            
            if entry.webshop_order:
                # update websho order
                webshop_order_update = frappe.db.sql("""UPDATE
                                                    `tabWebshop Order`
                                                SET `online_payment_zahlungsfile` = NULL
                                                WHERE `name` = '{name}'""".format(name=entry.webshop_order), as_list=True)
        self.datatrans_entries = []
        self.save()
        delete_datatrans_entries = frappe.db.sql("""DELETE FROM `tabDatatrans Entry` WHERE `name` IN ({to_delete})""".format(to_delete="'{0}'".format("', '".join(to_delete))), as_list=True)
    
    def create_single_report(self):
        create_mitgliedschaften_pro_file(self)
    
    def create_reports(self):
        create_mitgliedschaften_pro_file(self)
        sektions_list = create_monatsreport_mvd(self)
        create_monatsreport_sektionen(self, sektions_list)

def create_monatsreport_mvd(datatrans_zahlungsfile):
    def get_sektions_values(sektion):
        def get_month(month):
            months = {
                'Januar': '01',
                'Februar': '02',
                'März': '03',
                'April': '04',
                'Mai': '05',
                'Juni': '06',
                'Juli': '07',
                'August': '08',
                'September': '09',
                'Oktober': '10',
                'November': '11',
                'Dezember': '12'
            }
            return months[month]
        def get_last_day(month):
            months = {
                'Januar': '31',
                'Februar': '30',
                'März': '31',
                'April': '30',
                'Mai': '31',
                'Juni': '30',
                'Juli': '31',
                'August': '31',
                'September': '30',
                'Oktober': '31',
                'November': '30',
                'Dezember': '31'
            }
            return months[month]
        
        priv = frappe.db.sql("""
                                SELECT
                                    SUM(`amount`) AS `qty`
                                FROM `tabDatatrans Entry`
                                WHERE `transdatetime` BETWEEN '{year}/{month}/01 00:00:00' AND '{year}/{month}/{last_day} 23:59:59'
                                AND `refnumber` LIKE '{sektion_short}_%'
                            """.format(year=datatrans_zahlungsfile.report_year, month=get_month(datatrans_zahlungsfile.report_month), \
                                        last_day=get_last_day(datatrans_zahlungsfile.report_month), sektion_short=sektion.replace("MV", "")), as_dict=True)[0].qty
        if priv:
            hv = frappe.db.sql("""
                                    SELECT
                                        COUNT(`name`) AS `qty`
                                    FROM `tabDatatrans Entry`
                                    WHERE `transdatetime` BETWEEN '{year}/{month}/01 00:00:00' AND '{year}/{month}/{last_day} 23:59:59'
                                    AND `refnumber` LIKE '{sektion_short}_MH%'
                                """.format(year=datatrans_zahlungsfile.report_year, month=get_month(datatrans_zahlungsfile.report_month), \
                                            last_day=get_last_day(datatrans_zahlungsfile.report_month), sektion_short=sektion.replace("MV", "")), as_dict=True)[0].qty
            priv = priv - (hv * 12)
            hv = hv * 12
            mitgliedschaften = frappe.db.sql("""
                                        SELECT
                                            `mitglied_nr`,
                                            `adressblock`,
                                            `transdatetime`,
                                            `refnumber`,
                                            `amount`
                                        FROM `tabDatatrans Entry`
                                        WHERE `transdatetime` BETWEEN '{year}/{month}/01 00:00:00' AND '{year}/{month}/{last_day} 23:59:59'
                                        AND `refnumber` LIKE '{sektion_short}_%'
                                    """.format(year=datatrans_zahlungsfile.report_year, month=get_month(datatrans_zahlungsfile.report_month), \
                                                last_day=get_last_day(datatrans_zahlungsfile.report_month), sektion_short=sektion.replace("MV", "")), as_dict=True)
        else:
            hv = 0
            priv = 0
            mitgliedschaften = []
        return priv, hv, mitgliedschaften
    
    main_html = '''
        <h1>Monatsreport alle Sektionen für MVD</h1>
    '''
    
    html = main_html
    
    sektions_list = []
    
    sektionen = frappe.db.sql("""SELECT `name` FROM `tabSektion` ORDER BY `name` ASC""", as_dict=True)
    for sektion in sektionen:
        if sektion.name != 'MVD':
            priv, hv, mitgliedschaften = get_sektions_values(sektion.name)
            abzug = ((priv + hv) / 100) * datatrans_zahlungsfile.kommissions_prozent
            sektions_dict = {}
            sektions_dict['name'] = sektion.name
            sektions_dict['priv'] = frappe.utils.fmt_money(priv)
            sektions_dict['hv'] = hv
            sektions_dict['zwi_tot'] = frappe.utils.fmt_money(priv + hv)
            sektions_dict['abzug'] = "-" + str(frappe.utils.fmt_money(abzug))
            sektions_dict['total'] = frappe.utils.fmt_money((priv + hv) - abzug)
            sektions_dict['mitgliedschaften'] = mitgliedschaften
            
            sektion_html = '''
                <table style="width: 100%;">
                    <thead>
                        <tr>
                            <th style="width: 70%;">{sektion}</th>
                            <th style="width: 30%;"></th>
                        </tr>
                    </thead>
                    <tbody
                        <tr>
                            <td>PRIV</td>
                            <td>{priv}</td>
                        </tr>
                        <tr>
                            <td>HV</td>
                            <td>{hv}</td>
                        </tr>
                        <tr>
                            <td>Zwischentotal</td>
                            <td>{zwi_tot}</td>
                        </tr>
                        <tr>
                            <td>abzüglich {kommissions_prozent}% Kommision</td>
                            <td>{abzug}</td>
                        </tr>
                        <tr>
                            <td>Total</td>
                            <td>{total}</td>
                        </tr>
                    </tbody>
                </table><br><br>
            '''.format(sektion=sektion.name, kommissions_prozent=datatrans_zahlungsfile.kommissions_prozent, \
                        priv=sektions_dict['priv'], hv=sektions_dict['hv'], zwi_tot=sektions_dict['zwi_tot'], \
                        abzug=sektions_dict['abzug'], total=sektions_dict['total'])
            sektions_list.append(sektions_dict)
            html += sektion_html
    
    report = frappe.get_doc({
        "doctype": "Datatrans Report",
        "report_typ": "Monatsreport MVD",
        "sektion": "MVD",
        "datatrans_zahlungsfile": datatrans_zahlungsfile.name,
        "content_code": html
    }).insert()
    
    return sektions_list



def create_monatsreport_sektionen(datatrans_zahlungsfile, sektions_list):
    for sektions_dict in sektions_list:
        html = '''
            <h1>Monatsreport Online-Zahlungen an Sektionen</h1>
            <table style="width: 100%;">
                <thead>
                    <tr>
                        <th style="width: 70%;">{sektion}</th>
                        <th style="width: 30%;"></th>
                    </tr>
                </thead>
                <tbody
                    <tr>
                        <td>PRIV</td>
                        <td>{priv}</td>
                    </tr>
                    <tr>
                        <td>HV</td>
                        <td>{hv}</td>
                    </tr>
                    <tr>
                        <td>Zwischentotal</td>
                        <td>{zwi_tot}</td>
                    </tr>
                    <tr>
                        <td>abzüglich {kommissions_prozent}% Kommision</td>
                        <td>{abzug}</td>
                    </tr>
                    <tr>
                        <td>Total</td>
                        <td>{total}</td>
                    </tr>
                </tbody>
            </table><br><br>
        '''.format(sektion=sektions_dict['name'], kommissions_prozent=datatrans_zahlungsfile.kommissions_prozent, \
                    priv=sektions_dict['priv'], hv=sektions_dict['hv'], zwi_tot=sektions_dict['zwi_tot'], \
                    abzug=sektions_dict['abzug'], total=sektions_dict['total'])
        
        if len(sektions_dict['mitgliedschaften']) > 0:
            mitgl_html = '''
                <table style="width: 100%;">
            '''
            for mitgliedschaft in sektions_dict['mitgliedschaften']:
                mitgl_html += '''
                    <tr>
                        <td>{mitglied_nr}</td>
                        <td>{adressblock}</td>
                        <td>{transdatetime}</td>
                        <td>{refnumber}</td>
                        <td style="text-align: right;">{amount}</td>
                    </tr>
                '''.format(mitglied_nr=mitgliedschaft.mitglied_nr, adressblock=mitgliedschaft.adressblock, \
                            transdatetime=mitgliedschaft.transdatetime, refnumber=mitgliedschaft.refnumber, \
                            amount=mitgliedschaft.amount)
            mitgl_html += '''</table>'''
            html += mitgl_html
    
        report = frappe.get_doc({
            "doctype": "Datatrans Report",
            "report_typ": "Monatsreport Sektion",
            "sektion": sektions_dict['name'],
            "datatrans_zahlungsfile": datatrans_zahlungsfile.name,
            "content_code": html
        }).insert()
    
    return
