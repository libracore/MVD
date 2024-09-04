# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import csv
from mvd.mvd.doctype.datatrans_report.datatrans_report import create_mitgliedschaften_pro_file
from frappe.utils import cint
from frappe.utils.data import get_datetime, get_last_day

month_wrapper = {
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

class DatatransZahlungsfile(Document):
    def validate(self):
        if len(self.datatrans_entries) > 0:
            self.title = self.datatrans_entries[0].transdatetime.split(" ")[0]
    
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
                                                                        `mitgliedtyp_c`,
                                                                        `adressblock`,
                                                                        `online_haftpflicht`,
                                                                        `online_gutschrift`,
                                                                        `online_betrag`,
                                                                        `datum_online_verbucht`,
                                                                        `datum_online_gutschrift`,
                                                                        `online_payment_method`,
                                                                        `online_payment_zahlungsfile`,
                                                                        `mvb_typ`
                                                                    FROM `tabMitgliedschaft`
                                                                    WHERE `online_payment_id` = '{refnumber}'
                                                                    ORDER BY `creation` ASC
                                                                    LIMIT 1""".format(refnumber=refnumber), as_dict=True)
                            if len(mitgliedschaft_lookup) > 0:
                                # fetch data from mitgliedschaft
                                entry.mitglied_id = mitgliedschaft_lookup[0].name
                                entry.mitglied_nr = mitgliedschaft_lookup[0].mitglied_nr
                                entry.mitgliedtyp_c = mitgliedschaft_lookup[0].mitgliedtyp_c
                                entry.mvb_typ = mitgliedschaft_lookup[0].mvb_typ
                                entry.adressblock = mitgliedschaft_lookup[0].adressblock.replace("\n", ", ") if mitgliedschaft_lookup[0].adressblock else 'Keine Adresse'
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
        self.validate_verarbeitung()
        create_mitgliedschaften_pro_file(self)
    
    def create_reports(self):
        go = self.validate_verarbeitung()
        if go:
            create_mitgliedschaften_pro_file(self)
            sektions_list = create_monatsreport_mvd(self)
            create_monatsreport_sektionen(self, sektions_list)
            return 1
        else:
            return 'missing_files'
    
    def validate_verarbeitung(self):
        # alle Daten müssen verarbeitet sein
        for entry in self.datatrans_entries:
            if entry.status == 'Open':
                frappe.throw("Bitte zuerst die Daten verarbeiten.")
        
        # Prüfung ob fehlende Zahlungsfiles vorhanden (#1020)
        if not cint(self.ignore_missing_files) == 1:
            month = month_wrapper[self.report_month]
            year = self.report_year
            last_day = int(get_last_day(get_datetime("{0}-{1}-01 00:00:00".format(year, month))).strftime("%d"))
            not_found = []
            for day in range(1, last_day + 1):
                if day < 10:
                    day = '0{0}'.format(day)
                else:
                    day = '{0}'.format(day)
                found = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabDatatrans Zahlungsfile` WHERE `title` = '{0}'""".format('{0}/{1}/{2}'.format(year, month, day)), as_dict=True)[0].qty
                if found < 1:
                    not_found.append('{0}/{1}/{2}'.format(year, month, day))
            if len(not_found) > 0:
                self.missing_files = "<br>".join(not_found)
                self.save()
                return False
        
        return True

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
        def get_sektion_short(sektion):
            if sektion == "MVDF":
                return '''
                    (
                        `refnumber` LIKE 'FR_%'
                        OR
                        `refnumber` LIKE 'DF_%'
                    )
                '''
            if sektion == "MVAG":
                return '''
                    (
                        `refnumber` LIKE 'AG_%'
                        OR
                        `refnumber` LIKE 'BD_%'
                    )
                '''
            if sektion == "MVGR":
                return '''
                    (
                        `refnumber` LIKE 'GR_%'
                        OR
                        `refnumber` LIKE 'CH_%'
                    )
                '''
            return '''
                    `refnumber` LIKE '{sektion_short}_%'
                '''.format(sektion_short=sektion.replace("MV", ""))
        
        priv = frappe.db.sql("""
                                SELECT
                                    SUM(`amount`) AS `qty`
                                FROM `tabDatatrans Entry`
                                WHERE `transdatetime` BETWEEN '{year}/{month}/01 00:00:00' AND '{year}/{month}/{last_day} 23:59:59'
                                AND {sektion_short}
                                AND `mitgliedtyp_c` = 'Privat'
                                AND `status` NOT LIKE '%Doppelimport%'
                            """.format(year=datatrans_zahlungsfile.report_year, month=get_month(datatrans_zahlungsfile.report_month), \
                                        last_day=get_last_day(datatrans_zahlungsfile.report_month), sektion_short=get_sektion_short(sektion)), as_dict=True)[0].qty
        gesch = {}
        gesch['total'] = frappe.db.sql("""
                                SELECT
                                    IFNULL(SUM(`amount`), 0) AS `qty`
                                FROM `tabDatatrans Entry`
                                WHERE `transdatetime` BETWEEN '{year}/{month}/01 00:00:00' AND '{year}/{month}/{last_day} 23:59:59'
                                AND {sektion_short}
                                AND `mitgliedtyp_c` = 'Geschäft'
                                AND `status` NOT LIKE '%Doppelimport%'
                            """.format(year=datatrans_zahlungsfile.report_year, month=get_month(datatrans_zahlungsfile.report_month), \
                                        last_day=get_last_day(datatrans_zahlungsfile.report_month), sektion_short=get_sektion_short(sektion).replace("MV", "")), as_dict=True)[0].qty
        
        gesch['mini'] = frappe.db.sql("""
                                SELECT
                                    IFNULL(SUM(`amount`), 0) AS `qty`
                                FROM `tabDatatrans Entry`
                                WHERE `transdatetime` BETWEEN '{year}/{month}/01 00:00:00' AND '{year}/{month}/{last_day} 23:59:59'
                                AND {sektion_short}
                                AND `mitgliedtyp_c` = 'Geschäft'
                                AND `mvb_typ` LIKE '%mini%'
                                AND `status` NOT LIKE '%Doppelimport%'
                            """.format(year=datatrans_zahlungsfile.report_year, month=get_month(datatrans_zahlungsfile.report_month), \
                                        last_day=get_last_day(datatrans_zahlungsfile.report_month), sektion_short=get_sektion_short(sektion).replace("MV", "")), as_dict=True)[0].qty

        gesch['standard'] = frappe.db.sql("""
                                SELECT
                                    IFNULL(SUM(`amount`), 0) AS `qty`
                                FROM `tabDatatrans Entry`
                                WHERE `transdatetime` BETWEEN '{year}/{month}/01 00:00:00' AND '{year}/{month}/{last_day} 23:59:59'
                                AND {sektion_short}
                                AND `mitgliedtyp_c` = 'Geschäft'
                                AND `mvb_typ` LIKE '%standard%'
                                AND `status` NOT LIKE '%Doppelimport%'
                            """.format(year=datatrans_zahlungsfile.report_year, month=get_month(datatrans_zahlungsfile.report_month), \
                                        last_day=get_last_day(datatrans_zahlungsfile.report_month), sektion_short=get_sektion_short(sektion).replace("MV", "")), as_dict=True)[0].qty

        if priv:
            hv = frappe.db.sql("""
                                    SELECT
                                        COUNT(`name`) AS `qty`
                                    FROM `tabDatatrans Entry`
                                    WHERE `transdatetime` BETWEEN '{year}/{month}/01 00:00:00' AND '{year}/{month}/{last_day} 23:59:59'
                                    AND {sektion_short}
                                AND `status` NOT LIKE '%Doppelimport%'
                                """.format(year=datatrans_zahlungsfile.report_year, month=get_month(datatrans_zahlungsfile.report_month), \
                                            last_day=get_last_day(datatrans_zahlungsfile.report_month), sektion_short=get_sektion_short(sektion).replace("_%", "_MH%")), as_dict=True)[0].qty
            priv = priv - (hv * 10)
            hv = hv * 10
            mitgliedschaften = frappe.db.sql("""
                                        SELECT DISTINCT
                                            `mitglied_nr`,
                                            `adressblock`,
                                            `transdatetime`,
                                            `refnumber`,
                                            `amount`,
                                             `mitgliedtyp_c`
                                        FROM `tabDatatrans Entry`
                                        WHERE `transdatetime` BETWEEN '{year}/{month}/01 00:00:00' AND '{year}/{month}/{last_day} 23:59:59'
                                        AND {sektion_short}
                                        AND `status` NOT LIKE '%Doppelimport%'
                                        ORDER BY `mitgliedtyp_c` ASC, `mitglied_nr` ASC
                                    """.format(year=datatrans_zahlungsfile.report_year, month=get_month(datatrans_zahlungsfile.report_month), \
                                                last_day=get_last_day(datatrans_zahlungsfile.report_month), sektion_short=get_sektion_short(sektion)), as_dict=True)
        else:
            hv = 0
            priv = 0
            mitgliedschaften = []
        
        unbekannt = frappe.db.sql("""
                                SELECT
                                    IFNULL(SUM(`amount`), 0) AS `qty`
                                FROM `tabDatatrans Entry`
                                WHERE `transdatetime` BETWEEN '{year}/{month}/01 00:00:00' AND '{year}/{month}/{last_day} 23:59:59'
                                AND {sektion_short}
                                AND `mitgliedtyp_c` IS NULL
                                AND `status` NOT LIKE '%Doppelimport%'
                            """.format(year=datatrans_zahlungsfile.report_year, month=get_month(datatrans_zahlungsfile.report_month), \
                                        last_day=get_last_day(datatrans_zahlungsfile.report_month), sektion_short=get_sektion_short(sektion).replace("MV", "")), as_dict=True)[0].qty or 0
        return priv, gesch, hv, mitgliedschaften, unbekannt
    
    main_html = '''
        <h1>Monatsreport alle Sektionen für MVD</h1>
    '''
    
    html = main_html
    
    sektions_list = []
    gesammt_total_inkl_komm = 0
    gesammt_total_exkl_komm = 0
    
    sektionen = frappe.db.sql("""SELECT `name` FROM `tabSektion` ORDER BY `name` ASC""", as_dict=True)
    for sektion in sektionen:
        if sektion.name not in ('MVD', 'M+W-Abo', 'ASI', 'ASLOCA'):
            priv, gesch, hv, mitgliedschaften, unbekannt = get_sektions_values(sektion.name)
            abzug = ((priv + hv + gesch['total'] + unbekannt) / 100) * datatrans_zahlungsfile.kommissions_prozent
            sektions_dict = {}
            sektions_dict['name'] = sektion.name
            sektions_dict['priv'] = frappe.utils.fmt_money(priv)
            sektions_dict['gesch'] = frappe.utils.fmt_money(gesch['total'])
            sektions_dict['gesch_dict'] = gesch
            sektions_dict['hv'] = hv
            sektions_dict['unbekannt'] = frappe.utils.fmt_money(unbekannt)
            sektions_dict['zwi_tot'] = frappe.utils.fmt_money(priv + gesch['total'] + hv + unbekannt)
            sektions_dict['abzug'] = "-" + str(frappe.utils.fmt_money(abzug))
            sektions_dict['total'] = frappe.utils.fmt_money((priv + gesch['total'] + hv + unbekannt) - abzug)
            sektions_dict['mitgliedschaften'] = mitgliedschaften

            if sektion.name == 'MVZH':
                gesch_html = """
                    <tr>
                        <td>GESCH (Total)</td>
                        <td style="text-align: right;">{total}</td>
                    </tr>
                    <tr>
                        <td>GESCH (MV Business Mini)</td>
                        <td style="text-align: right;">{mini}</td>
                    </tr>
                    <tr>
                        <td>GESCH (MV Business Standard)</td>
                        <td style="text-align: right;">{standard}</td>
                    </tr>
                """.format(total=frappe.utils.fmt_money(sektions_dict['gesch_dict']['total']), \
                        mini=frappe.utils.fmt_money(sektions_dict['gesch_dict']['mini']), \
                        standard=frappe.utils.fmt_money(sektions_dict['gesch_dict']['standard']))
            else:
                gesch_html = """
                    <tr>
                        <td>GESCH</td>
                        <td style="text-align: right;">{gesch}</td>
                    </tr>
                """.format(gesch=frappe.utils.fmt_money(sektions_dict['gesch']))
            
            sektion_html = '''
                <table style="width: 100%;">
                    <thead>
                        <tr>
                            <th style="width: 70%;">{sektion}</th>
                            <th style="width: 30%; text-align: right;"></th>
                        </tr>
                    </thead>
                    <tbody
                        <tr>
                            <td>PRIV</td>
                            <td style="text-align: right;">{priv}</td>
                        </tr>
                        {gesch_html}
                        <tr>
                            <td>HV</td>
                            <td style="text-align: right;">{hv}</td>
                        </tr>
                        <tr>
                            <td>Unbekannt</td>
                            <td style="text-align: right;">{unbekannt}</td>
                        </tr>
                        <tr>
                            <td>Zwischentotal</td>
                            <td style="text-align: right;">{zwi_tot}</td>
                        </tr>
                        <tr>
                            <td>abzüglich {kommissions_prozent}% Kommision</td>
                            <td style="text-align: right;">{abzug}</td>
                        </tr>
                        <tr>
                            <td>Total</td>
                            <td style="text-align: right;">{total}</td>
                        </tr>
                    </tbody>
                </table><br><br>
            '''.format(sektion=sektion.name, kommissions_prozent=datatrans_zahlungsfile.kommissions_prozent, \
                        priv=sektions_dict['priv'], hv=sektions_dict['hv'], zwi_tot=sektions_dict['zwi_tot'], \
                        abzug=sektions_dict['abzug'], total=sektions_dict['total'], gesch_html=gesch_html, \
                        unbekannt=sektions_dict['unbekannt'])
            sektions_list.append(sektions_dict)
            html += sektion_html
            gesammt_total_exkl_komm += float(sektions_dict['total'].replace("'", ""))
            gesammt_total_inkl_komm += float(sektions_dict['zwi_tot'].replace("'", ""))
    
    html += '''
        <h3>Gesamttotal exkl. Kommision {0}</h3>
        <h3>Gesamttotal inkl. Kommision {1}</h3>
    '''.format(gesammt_total_exkl_komm, gesammt_total_inkl_komm)

    report = frappe.get_doc({
        "doctype": "Datatrans Report",
        "report_typ": "Monatsreport MVD",
        "sektion": "MVD",
        "datatrans_zahlungsfile": datatrans_zahlungsfile.name,
        "datum_zahlungsfile": datatrans_zahlungsfile.title,
        "content_code": html
    }).insert()
    
    return sektions_list



def create_monatsreport_sektionen(datatrans_zahlungsfile, sektions_list):
    for sektions_dict in sektions_list:
        if sektions_dict['name'] == 'MVZH':
            gesch_html = """
                <tr>
                    <td>GESCH (Total)</td>
                    <td style="text-align: right;">{total}</td>
                </tr>
                <tr>
                    <td>GESCH (MV Business Mini)</td>
                    <td style="text-align: right;">{mini}</td>
                </tr>
                <tr>
                    <td>GESCH (MV Business Standard)</td>
                    <td style="text-align: right;">{standard}</td>
                </tr>
            """.format(total=frappe.utils.fmt_money(sektions_dict['gesch_dict']['total']), \
                       mini=frappe.utils.fmt_money(sektions_dict['gesch_dict']['mini']), \
                       standard=frappe.utils.fmt_money(sektions_dict['gesch_dict']['standard']))
        else:
            gesch_html = """
                <tr>
                    <td>GESCH</td>
                    <td style="text-align: right;">{gesch}</td>
                </tr>
            """.format(gesch=frappe.utils.fmt_money(sektions_dict['gesch']))
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
                        <td style="text-align: right;">{priv}</td>
                    </tr>
                    {gesch_html}
                    <tr>
                        <td>HV</td>
                        <td style="text-align: right;">{hv}</td>
                    </tr>
                    <tr>
                        <td>Unbekannt</td>
                        <td style="text-align: right;">{unbekannt}</td>
                    </tr>
                    <tr>
                        <td>Zwischentotal</td>
                        <td style="text-align: right;">{zwi_tot}</td>
                    </tr>
                    <tr>
                        <td>abzüglich {kommissions_prozent}% Kommision</td>
                        <td style="text-align: right;">{abzug}</td>
                    </tr>
                    <tr>
                        <td>Total</td>
                        <td style="text-align: right;">{total}</td>
                    </tr>
                </tbody>
            </table><br><br>
        '''.format(sektion=sektions_dict['name'], kommissions_prozent=datatrans_zahlungsfile.kommissions_prozent, \
                    priv=sektions_dict['priv'], hv=sektions_dict['hv'], zwi_tot=sektions_dict['zwi_tot'], \
                    abzug=sektions_dict['abzug'], total=sektions_dict['total'], gesch_html=gesch_html, \
                    unbekannt=sektions_dict['unbekannt'])
        
        if len(sektions_dict['mitgliedschaften']) > 0:
            mitgl_html = '''
                <table style="width: 100%;">
            '''
            for mitgliedschaft in sektions_dict['mitgliedschaften']:
                mitgl_html += '''
                    <tr>
                        <td>{mitglied_nr}</td>
                        <td>{adressblock}<br>{mitgliedtyp_c}</td>
                        <td>{transdatetime}</td>
                        <td>{refnumber}</td>
                        <td style="text-align: right;">{amount}</td>
                    </tr>
                '''.format(mitglied_nr=mitgliedschaft.mitglied_nr, adressblock=mitgliedschaft.adressblock, \
                            transdatetime=mitgliedschaft.transdatetime, refnumber=mitgliedschaft.refnumber, \
                            amount=mitgliedschaft.amount, mitgliedtyp_c=mitgliedschaft.mitgliedtyp_c)
            mitgl_html += '''</table>'''
            html += mitgl_html
    
        report = frappe.get_doc({
            "doctype": "Datatrans Report",
            "report_typ": "Monatsreport Sektion",
            "sektion": sektions_dict['name'],
            "datatrans_zahlungsfile": datatrans_zahlungsfile.name,
            "datum_zahlungsfile": datatrans_zahlungsfile.title,
            "content_code": html
        }).insert()
    
    return
