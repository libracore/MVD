# -*- coding: utf-8 -*-
# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class DatatransReport(Document):
    pass

def create_mitgliedschaften_pro_file(datatrans_zahlungsfile):
    verbuchbare_zahlungen = {
        'anzahl': 0,
        'gutschriften': 0,
        'betrag': 0
    }
    nicht_verbuchbare_zahlungen = {
        'anderes': 0,
        'abweichender_betrag': 0,
        'no_match': 0,
        'anzahl': 0,
        'betrag': 0,
        'detail_liste': []
    }
    for entry in datatrans_zahlungsfile.datatrans_entries:
        nicht_verbuchbar_flag = False
        # Verbuchbar
        # -----------
        if entry.status in ['Mitglied: Match', 'Webshop: Match']:
            verbuchbare_zahlungen['anzahl'] += 1
            verbuchbare_zahlungen['betrag'] += float(entry.amount)
            
        elif entry.status in ['Mitglied: Gutschrift', 'Webshop: Gutschrift']:
            verbuchbare_zahlungen['anzahl'] += 1
            verbuchbare_zahlungen['gutschriften'] += 1
            verbuchbare_zahlungen['betrag'] += (float(entry.amount) * -1)
            
        # Nicht verbuchbar
        # -----------
        elif entry.status in ['Mitglied: No Match', 'Webshop: No Match']:
            nicht_verbuchbar_flag = True
            nicht_verbuchbare_zahlungen['no_match'] += 1
            nicht_verbuchbare_zahlungen['anzahl'] += 1
            if float(entry.amount) > 0:
                nicht_verbuchbare_zahlungen['betrag'] += float(entry.amount)
            else:
                nicht_verbuchbare_zahlungen['betrag'] += (float(entry.amount) * -1)
        
        elif entry.status in ['Mitglied: Abweichender Betrag', 'Webshop: Abweichender Betrag']:
            nicht_verbuchbar_flag = True
            nicht_verbuchbare_zahlungen['abweichender_betrag'] += 1
            nicht_verbuchbare_zahlungen['anzahl'] += 1
            nicht_verbuchbare_zahlungen['betrag'] += float(entry.amount)
        
        elif entry.status in ['Mitglied: Doppelimport', 'Webshop: Doppelimport']:
            nicht_verbuchbar_flag = True
            nicht_verbuchbare_zahlungen['anderes'] += 1
            nicht_verbuchbare_zahlungen['anzahl'] += 1
            if float(entry.amount) > 0:
                nicht_verbuchbare_zahlungen['betrag'] += float(entry.amount)
            else:
                nicht_verbuchbare_zahlungen['betrag'] += (float(entry.amount) * -1)
        
        if nicht_verbuchbar_flag:
            nicht_verbuchbare_zahlungen['detail_liste'].append({
                'match': entry.mitglied_nr or entry.webshop_order or '-',
                'empfaenger': entry.adressblock or '-',
                'valuta': entry.transdatetime or '-',
                'betrag': entry.amount or '-',
                'grund': entry.status
            })
    
    main_html = '''
        <h1>Zahlungsreport Datatrans  (Valuta bis n/a)</h1>
        <h2>Zahlungsdatei</h2>
        <table style="width: 100%;">
            <tr>
                <td style="text-align: left; width: 70%;">Filedatum</td>
                <td style="text-align: right; width: 30%;">n/a</td>
            </tr>
            <tr>
                <td style="text-align: left;">Anzahl Zahlungen (Total number of records)</td>
                <td style="text-align: right;">{total_number_of_records}</td>
            </tr>
            <tr>
                <td style="text-align: left;">Anzahl Zahlungen (Total number of debits)</td>
                <td style="text-align: right;">{total_number_of_debits}</td>
            </tr>
            <tr>
                <td style="text-align: left;">Anzahl Zahlungen (Total number of credits)</td>
                <td style="text-align: right;">{total_number_of_credits}</td>
            </tr>
            <tr>
                <td style="text-align: left;"><b>Totalbetrag (Total debit amount)</b></td>
                <td style="text-align: right;"><b>{total_debit_amount}</b></td>
            </tr>
            <tr>
                <td style="text-align: left;"><b>Totalbetrag (Total credit amount)</b></td>
                <td style="text-align: right;"><b>{total_credit_amount}</b></td>
            </tr>
            <tr>
                <td style="text-align: left;"><b>Totalbetrag (Total settlement amount)</b></td>
                <td style="text-align: right;"><b>{total_settlement_amount}</b></td>
            </tr>
        </table>
        <h2>Verbuchbare Zahlungen</h2>
        <table style="width: 100%;">
            <tr>
                <td style="text-align: left;">Anzahl verbuchbare Zahlungen</td>
                <td style="text-align: right;">{verbuchbare_zahlungen_anzahl}</td>
            </tr>
            <tr>
                <td style="text-align: left;">Davon Gutschriften</td>
                <td style="text-align: right;">{verbuchbare_zahlungen_gutschriften}</td>
            </tr>
            <tr>
                <td style="text-align: left;"><b>Verbuchbarer Betrag</b></td>
                <td style="text-align: right;"><b>{verbuchbare_zahlungen_betrag}</b></td>
            </tr>
        </table>
        <h2>Nicht verbuchbare Zahlungen</h2>
        <table style="width: 100%;">
            <tr>
                <td style="text-align: left;">Faktura/Mitgliedschaft doppelt bezahlt</td>
                <td style="text-align: right;">n/a</td>
            </tr>
            <tr>
                <td style="text-align: left;">Faktura/Mitgliedschaft doppelt gutgeschrieben</td>
                <td style="text-align: right;">n/a</td>
            </tr>
            <tr>
                <td style="text-align: left;">Faktura/Mitgliedschaft nicht gefunden</td>
                <td style="text-align: right;">{nicht_verbuchbare_zahlungen_no_match}</td>
            </tr>
            <tr>
                <td style="text-align: left;">Betrag stimmt nicht überein</td>
                <td style="text-align: right;">{nicht_verbuchbare_zahlungen_abweichender_betrag}</td>
            </tr>
            <tr>
                <td style="text-align: left;">Andere Gründe</td>
                <td style="text-align: right;">{nicht_verbuchbare_zahlungen_anderes}</td>
            </tr>
            <tr>
                <td style="text-align: left;">Anzahl unverbuchbare Zahlungen</td>
                <td style="text-align: right;">{nicht_verbuchbare_zahlungen_anzahl}</td>
            </tr>
            <tr>
                <td style="text-align: left;"><b>Nicht verbuchbarer Betrag</b></td>
                <td style="text-align: right;"><b>{nicht_verbuchbare_zahlungen_betrag}</b></td>
            </tr>
        </table>
    '''.format(total_number_of_records=datatrans_zahlungsfile.total_number_of_records, \
                total_settlement_amount=frappe.utils.fmt_money(datatrans_zahlungsfile.total_settlement_amount), \
                total_number_of_debits=datatrans_zahlungsfile.total_number_of_debits, \
                total_number_of_credits=datatrans_zahlungsfile.total_number_of_credits, \
                total_debit_amount=datatrans_zahlungsfile.total_debit_amount, \
                total_credit_amount=datatrans_zahlungsfile.total_credit_amount, \
                verbuchbare_zahlungen_anzahl=verbuchbare_zahlungen['anzahl'], \
                verbuchbare_zahlungen_gutschriften=verbuchbare_zahlungen['gutschriften'], \
                verbuchbare_zahlungen_betrag=verbuchbare_zahlungen['betrag'], \
                nicht_verbuchbare_zahlungen_no_match=nicht_verbuchbare_zahlungen['no_match'], \
                nicht_verbuchbare_zahlungen_abweichender_betrag=nicht_verbuchbare_zahlungen['abweichender_betrag'], \
                nicht_verbuchbare_zahlungen_anderes=nicht_verbuchbare_zahlungen['anderes'], \
                nicht_verbuchbare_zahlungen_anzahl=nicht_verbuchbare_zahlungen['anzahl'], \
                nicht_verbuchbare_zahlungen_betrag=nicht_verbuchbare_zahlungen['betrag'])
    
    html_nicht_verbucht = '''
        <h1>Nicht verbuchte Zahlungen</h1>
        <table style="width: 100%;">
            <thead>
                <tr>
                    <th style="border-bottom: 1px solid black;">Fak./Mitnr.</th>
                    <th style="border-bottom: 1px solid black;">EmpfängerIn</th>
                    <th style="border-bottom: 1px solid black;">Valuta</th>
                    <th style="border-bottom: 1px solid black;">Betrag</th>
                    <th style="border-bottom: 1px solid black;">Grund</th>
                </tr>
            </thead>
            <tbody>
    '''
    for nvz in nicht_verbuchbare_zahlungen['detail_liste']:
        html_nicht_verbucht += '''
            <tr>
                <td>{match}</td>
                <td>{empfaenger}</td>
                <td>{valuta}</td>
                <td>{betrag}</td>
                <td>{grund}</td>
            </tr>
        '''.format(match=nvz['match'], \
                    empfaenger=nvz['empfaenger'], \
                    valuta=nvz['valuta'], \
                    betrag=nvz['betrag'], \
                    grund=nvz['grund'])

    html_nicht_verbucht += '''
            </tbody>
        </table>
    '''
    
    html_gutschriften = '''
        <h1>Gutschriften</h1>
        <table style="width: 100%;">
            <thead>
                <tr>
                    <th style="border-bottom: 1px solid black;">Fak./Mitnr.</th>
                    <th style="border-bottom: 1px solid black;">EmpfängerIn</th>
                    <th style="border-bottom: 1px solid black;">Valuta</th>
                    <th style="border-bottom: 1px solid black;">Betrag</th>
                    <th style="border-bottom: 1px solid black;">Transaktions-ID</th>
                </tr>
            </thead>
            <tbody>
            <tr>
                <td>...</td>
                <td>...</td>
                <td>...</td>
                <td>...</td>
                <td>...</td>
            </tr>
            </tbody>
        </table>
    '''
    
    html_ausstehende_records = '''
        <h1>Ausstehende Datatrans-Zahlungsrecords</h1>
        <table style="width: 100%;">
            <thead>
                <tr>
                    <th style="border-bottom: 1px solid black;">Fak./Mitnr.</th>
                    <th style="border-bottom: 1px solid black;">EmpfängerIn</th>
                    <th style="border-bottom: 1px solid black;">Valuta</th>
                    <th style="border-bottom: 1px solid black;">Betrag</th>
                    <th style="border-bottom: 1px solid black;">Transaktions-ID</th>
                </tr>
            </thead>
            <tbody>
            <tr>
                <td>...</td>
                <td>...</td>
                <td>...</td>
                <td>...</td>
                <td>...</td>
            </tr>
            </tbody>
        </table>
    '''
    
    html = main_html + html_nicht_verbucht + html_gutschriften + html_ausstehende_records
    
    report = frappe.get_doc({
        "doctype": "Datatrans Report",
        "report_typ": "Mitgliedschaften pro File",
        "sektion": "MVD",
        "datatrans_zahlungsfile": datatrans_zahlungsfile.name,
        "content_code": html
    }).insert()
    
    return
