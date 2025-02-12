# -*- coding: utf-8 -*-
# Copyright (c) 2022-2024, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from bs4 import BeautifulSoup

def get_camt_file(file_path, test=False):
    try:
        physical_path = "/home/frappe/frappe-bench/sites/{0}{1}".format(frappe.local.site_path.replace("./", ""), file_path)
        with open(physical_path, 'r') as f:
            content = f.read()
        soup = BeautifulSoup(content, 'lxml')
        iban = soup.document.bktocstmrdbtcdtntfctn.ntfctn.acct.id.iban.get_text()
        if test:
            return True
        else:
            return soup
    except:
        return False

def get_default_customer(sektion):
    default_customer = frappe.get_doc("Sektion", sektion).default_customer
    return default_customer

def camt_status_update(camt_import, status):
    frappe.db.set_value('CAMT Import', camt_import, 'status', status)

def erfasse_rg_match(camt_import):
    new_rg_match_qty = frappe.db.get_value('CAMT Import', camt_import, 'rg_match_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'rg_match_qty', new_rg_match_qty)

def erfasse_ausgelesene_zahlungen(transaction_reference, unique_reference, date, received_amount, camt_import):
    ausgelesene_zahlungen = frappe.db.get_value('CAMT Import', camt_import, 'ausgelesene_zahlungen')
    qty = frappe.db.get_value('CAMT Import', camt_import, 'ausgelesene_zahlungen_qty') + 1
    if ausgelesene_zahlungen:
        ausgelesene_zahlungen += '\n{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    else:
        ausgelesene_zahlungen = '{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    frappe.db.set_value('CAMT Import', camt_import, 'ausgelesene_zahlungen', ausgelesene_zahlungen)
    frappe.db.set_value('CAMT Import', camt_import, 'ausgelesene_zahlungen_qty', qty)

def erfasse_eingelesene_zahlungen(transaction_reference, unique_reference, date, received_amount, camt_import):
    eingelesene_zahlungen = frappe.db.get_value('CAMT Import', camt_import, 'eingelesene_zahlungen')
    qty = frappe.db.get_value('CAMT Import', camt_import, 'eingelesene_zahlungen_qty') + 1
    if eingelesene_zahlungen:
        eingelesene_zahlungen += '\n{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    else:
        eingelesene_zahlungen = '{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    frappe.db.set_value('CAMT Import', camt_import, 'eingelesene_zahlungen', eingelesene_zahlungen)
    frappe.db.set_value('CAMT Import', camt_import, 'eingelesene_zahlungen_qty', qty)
    no_match_qty = frappe.db.get_value('CAMT Import', camt_import, 'anz_unmatched_payments') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'anz_unmatched_payments', no_match_qty)

def erfasse_nicht_eingelesene_zahlungen(transaction_reference, unique_reference, date, received_amount, camt_import):
    nicht_eingelesene_zahlungen = frappe.db.get_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen')
    qty = frappe.db.get_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen_qty') + 1
    if nicht_eingelesene_zahlungen:
        nicht_eingelesene_zahlungen += '\n{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    else:
        nicht_eingelesene_zahlungen = '{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    frappe.db.set_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen', nicht_eingelesene_zahlungen)
    frappe.db.set_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen_qty', qty)

def erfasse_fehlgeschlagenes_auslesen(transaction, err, camt_import):
    fehlgeschlagenes_auslesen = frappe.db.get_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen')
    qty = frappe.db.get_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen_qty') + 1
    if fehlgeschlagenes_auslesen:
        fehlgeschlagenes_auslesen += '\n{0}\n{1}\n-----------------------------'.format(transaction, err)
    else:
        fehlgeschlagenes_auslesen = '{0}\n{1}\n-----------------------------'.format(transaction, err)
    frappe.db.set_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen', fehlgeschlagenes_auslesen)
    frappe.db.set_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen_qty', qty)

def sinv_lookup(qrr_ref, betrag):
    """
    Diese Funktion sucht nach gebuchten Sales Invoices anhand der QRR-Referenznummer aus der CAMT-Zahlung
    
    Mögliche Antwort Cases:
    -----------------------
    - Check: True & info: Sinv Match
        -> Zahlung wird erstellt und gegen Sinv verbucht (insofern Sinv unbezahlt)
    
    - Check: False & info: Multi-Sinvs
        -> Unzugewiesene Zahlung wird erstellt
    
    - Check: False & info: No Sinvs
        -> Unzugewiesene Zahlung wird erstellt
    
    - Check: False & info: Paid Fak
        -> Zugewiesene, aber unverbuchte Zahlung wird erstellt
    """
    sinvs = frappe.db.sql("""SELECT
                                `name` AS `sinv`,
                                `customer`,
                                `mv_mitgliedschaft`,
                                `mv_kunde`,
                                `outstanding_amount`,
                                `sektion_id` AS `sektion`,
                                `company`
                            FROM `tabSales Invoice`
                            WHERE `docstatus` = 1
                            AND REPLACE(`esr_reference`, ' ', '') = '{qrr_ref}'
                            AND `outstanding_amount` > 0""".format(qrr_ref=qrr_ref), as_dict=True)
    
    if len(sinvs) > 0:
        # Sinv gefunden
        if len(sinvs) > 1:
            # mehere Sinvs gefunden -> erzeuge unzugewiesene Zahlung
            return False
        else:
            # unique match -> erzeuge Zahlung
            return sinvs[0]
    else:
        # sinv nicht gefunden, starte suche nach Fakultativer Rechnung
        return fak_lookup(qrr_ref, betrag)

def fak_lookup(qrr_ref, betrag):
    """
    Diese Funktion sucht nach gebuchten Fakultativen Rechnungen anhand der QRR-Referenznummer aus der CAMT-Zahlung
    """
    faks = frappe.db.sql("""SELECT *
                            FROM `tabFakultative Rechnung`
                            WHERE `docstatus` = 1
                            AND REPLACE(`qrr_referenz`, ' ', '') = '{qrr_ref}'
                            AND `status` = 'Unpaid'""".format(qrr_ref=qrr_ref), as_dict=True)
    
    if len(faks) > 0:
        # FK gefunden
        if len(faks) > 1:
            # mehere Fakultative Rechungen gefunden -> erzeuge unzugewiesene Zahlung
            return False
        else:
            # unique match -> umwandlung Fakultative Rechnung in Sales Invoice
            from mvd.mvd.doctype.camt_import.utils import create_unpaid_sinv
            return create_unpaid_sinv(faks[0].name, betrag)
    else:
        # FK nicht gefunden -> erzeuge unzugewiesene Zahlung
        return False

def camt_gebuchte_zahlung_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'verbuchte_zahlung_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'verbuchte_zahlung_qty', qty)

def camt_mitgliedschaften_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'mitgliedschaften_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'mitgliedschaften_qty', qty)

def camt_hv_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'hv_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'hv_qty', qty)

def camt_spenden_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'spenden_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'spenden_qty', qty)

def camt_produkte_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'produkte_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'produkte_qty', qty)

def camt_ueberzahlung_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'ueberzahlung_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'ueberzahlung_qty', qty)

def camt_zugewiesen_nicht_verbucht_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'zugewiesen_unverbucht_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'zugewiesen_unverbucht_qty', qty)

@frappe.whitelist()
def aktualisiere_camt_uebersicht(camt_import):
    # verbuchte Zahlungen
    verbuchte_zahlungen = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 1""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'verbuchte_zahlung_qty', verbuchte_zahlungen)
    
    # nicht zugewiesene Zahlungen
    nicht_zugewiesene_zahlungen = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 0
                                            AND `camt_status` = 'Nicht zugewiesen'""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'anz_unmatched_payments', nicht_zugewiesene_zahlungen)
    
    # zugewiesene aber unverbuchte Zahlungen
    zugewiesen_unverbucht_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 0
                                            AND `mv_mitgliedschaft` IS NOT NULL""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'zugewiesen_unverbucht_qty', zugewiesen_unverbucht_qty)
    
    # Verbuchte Zahlungen welche ein Guthaben auslösen
    guthaben_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 1
                                            AND `unallocated_amount` > 0""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'guthaben_qty', guthaben_qty)
    
    # Stornierte Zahlungen
    storno_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 2""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'stornierte_zahlungen_qty', storno_qty)
    
    # HV, Mitgliedschaften, Produkte und Spenden
    gebuchte_pes = frappe.db.sql("""SELECT `name`
                                    FROM `tabPayment Entry`
                                    WHERE `camt_import` = '{camt_import}'
                                    AND `docstatus` = 1""".format(camt_import=camt_import), as_dict=True)
    # reset old values
    frappe.db.set_value('CAMT Import', camt_import, 'mitgliedschaften_qty', 0)
    frappe.db.set_value('CAMT Import', camt_import, 'hv_qty', 0)
    frappe.db.set_value('CAMT Import', camt_import, 'spenden_qty', 0)
    frappe.db.set_value('CAMT Import', camt_import, 'produkte_qty', 0)
    
    # set new values
    for pe in gebuchte_pes:
        pe_doc = frappe.get_doc("Payment Entry", pe.name)
        if len(pe_doc.references) > 0:
            for reference in pe_doc.references:
                if int(frappe.db.get_value('Sales Invoice', reference.reference_name, 'ist_mitgliedschaftsrechnung')) == 1:
                    camt_mitgliedschaften_update(camt_import)
                elif int(frappe.db.get_value('Sales Invoice', reference.reference_name, 'ist_hv_rechnung')) == 1:
                    camt_hv_update(camt_import)
                elif int(frappe.db.get_value('Sales Invoice', reference.reference_name, 'ist_spenden_rechnung')) == 1:
                    camt_spenden_update(camt_import)
                elif int(frappe.db.get_value('Sales Invoice', reference.reference_name, 'ist_sonstige_rechnung')) == 1:
                    camt_produkte_update(camt_import)
    
    # update report data
    verbuchte_zahlungen_gegen_rechnung = frappe.db.sql("""SELECT
                                                            SUM(`amount`) AS `amount`,
                                                            `item_code`,
                                                            `income_account`
                                                        FROM `tabSales Invoice Item` WHERE `parent` IN (
                                                            SELECT DISTINCT
                                                                `reference_name`
                                                            FROM `tabPayment Entry Reference`
                                                            WHERE `parent` IN (
                                                                SELECT
                                                                    `name`
                                                                FROM `tabPayment Entry`
                                                                WHERE `camt_import` = '{camt_import}'
                                                                AND `docstatus` = 1
                                                            )
                                                        )
                                                        GROUP BY `item_code`""".format(camt_import=camt_import), as_dict=True)
    
    verbuchte_guthaben = frappe.db.sql("""SELECT
                                                SUM(`unallocated_amount`) AS `amount`,
                                                `mv_mitgliedschaft` AS `mitgliedschaft`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `mv_mitgliedschaft` IS NOT NULL
                                            AND `docstatus` = 1
                                            AND `unallocated_amount` > 0
                                            GROUP BY `mv_mitgliedschaft`""".format(camt_import=camt_import), as_dict=True)
    
    falsch_verbuchte_guthaben = frappe.db.sql("""SELECT
                                                        `unallocated_amount` AS `amount`,
                                                        `name`
                                                    FROM `tabPayment Entry`
                                                    WHERE `camt_import` = '{camt_import}'
                                                    AND (
                                                        `mv_mitgliedschaft` IS NULL
                                                        AND
                                                        `mv_kunde` IS NULL
                                                    )
                                                    AND `docstatus` = 1""".format(camt_import=camt_import), as_dict=True)
    
    nicht_gebuchte_pes = frappe.db.sql("""SELECT `name`
                                    FROM `tabPayment Entry`
                                    WHERE `camt_import` = '{camt_import}'
                                    AND `docstatus` != 1""".format(camt_import=camt_import), as_dict=True)
    
    report_data = ''
    # nicht eingelesene Zahlungen
    if int(frappe.db.get_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen_qty')) > 0:
        report_data += """<p style="color: red;"><br>Achtung; {0} Zahlung(en) konnte(n) <u>nicht</u> eingelesen werden!</p>""".format(frappe.db.get_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen_qty'))
    # Artikel und Ertragskonten Aufschlüsselung
    ertragskonten = {}
    if len(verbuchte_zahlungen_gegen_rechnung) > 0:
        # Artikel Aufschlüsselung
        totalbetrag = 0
        report_data += """<h3>Aufschlüsselung nach Artikel</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Artikel</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                </tr>"""
        for entry in verbuchte_zahlungen_gegen_rechnung:
            if entry.income_account in ertragskonten:
                ertragskonten[entry.income_account] += entry.amount
            else:
                ertragskonten[entry.income_account] = entry.amount
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0} ({1})</td>
                                <td style="text-align: right;">{2}</td>
                            </tr>""".format(frappe.get_value("Item", entry.item_code, "item_name"), frappe.get_value("Item", entry.item_code, "sektion_id"), "{:,.2f}".format(entry.amount).replace(",", "'"))
            totalbetrag += entry.amount
        report_data += """
                        <tr>
                            <td style="text-align: left;"><b>Total</b></td>
                            <td style="text-align: right;"><b>{0}</b></td>
                        </tr>""".format("{:,.2f}".format(totalbetrag).replace(",", "'"))
        
        report_data += """</tbody></table>"""
        
        # Ertragskonten Aufschlüsselung
        totalbetrag = 0
        report_data += """<h3>Aufschlüsselung nach Ertragskonten</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Ertragskonto</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                </tr>"""
        for key, value in ertragskonten.items():
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0}</td>
                                <td style="text-align: right;">{1}</td>
                            </tr>""".format(key, "{:,.2f}".format(value).replace(",", "'"))
            totalbetrag += value
        report_data += """
                        <tr>
                            <td style="text-align: left;"><b>Total</b></td>
                            <td style="text-align: right;"><b>{0}</b></td>
                        </tr>""".format("{:,.2f}".format(totalbetrag).replace(",", "'"))
        
        report_data += """</tbody></table>"""
    
    # Verbuchte Guthaben
    if len(verbuchte_guthaben) > 0:
        report_data += """<h3>Verbuchte Guthaben</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Mitglied</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                </tr>"""
        for entry in verbuchte_guthaben:
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0}</td>
                                <td style="text-align: right;">{1}</td>
                            </tr>""".format("""<a href="/desk#Form/Mitgliedschaft/{0}">""".format(entry.mitgliedschaft) + str(frappe.get_value("Mitgliedschaft", entry.mitgliedschaft, "mitglied_nr")) + """</a>""", \
                            "{:,.2f}".format(entry.amount).replace(",", "'"))
        report_data += """</tbody></table>"""
    
    # Falsch verbuchte Guthaben
    if len(falsch_verbuchte_guthaben) > 0:
        report_data += """<h3>Falsch verbuchte Guthaben</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Zahlung</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                </tr>"""
        for entry in falsch_verbuchte_guthaben:
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0}</td>
                                <td style="text-align: right;">{1}</td>
                            </tr>""".format("""<a href="/desk#Form/Payment Entry/{pe}">{pe}</a>""".format(pe=entry.name), "{:,.2f}".format(entry.amount).replace(",", "'"))
        report_data += """</tbody></table>"""
    
    # Zahlungsliste (Unverbucht)
    if len(nicht_gebuchte_pes) > 0:
        report_data += """<h3>Zahlungsliste (Unverbucht)</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Mitgliedschaft</b></td>
                                    <td style="text-align: left;"><b>Details</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                    <td style="text-align: right;"><b>Status</b></td>
                                </tr>"""
        for pe in nicht_gebuchte_pes:
            pe_doc = frappe.get_doc("Payment Entry", pe.name)
            if pe_doc.mv_mitgliedschaft:
                mitgliedschafts_link_string = """<a href="/desk#Form/Mitgliedschaft/{0}">""".format(pe_doc.mv_mitgliedschaft) + str(frappe.get_value("Mitgliedschaft", pe_doc.mv_mitgliedschaft, "mitglied_nr")) + """</a>"""
            else:
                mitgliedschafts_link_string = '---'
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0}</td>
                                <td style="text-align: left;">{1}</td>
                                <td style="text-align: right;">{2}</td>
                                <td style="text-align: right;">{3}</td>
                            </tr>""".format(mitgliedschafts_link_string, \
                            pe_doc.remarks, \
                            "{:,.2f}".format(pe_doc.paid_amount).replace(",", "'"), \
                            'Entwurf' if pe_doc.docstatus == 0 else 'Storniert')
        report_data += """</tbody></table>"""
    
    # Zahlungsliste (Verbucht)
    if len(gebuchte_pes) > 0:
        report_data += """<h3>Zahlungsliste (Verbucht)</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Mitgliedschaft</b></td>
                                    <td style="text-align: left;"><b>Details</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                </tr>"""
        for pe in gebuchte_pes:
            pe_doc = frappe.get_doc("Payment Entry", pe.name)
            if pe_doc.mv_mitgliedschaft:
                hyperlink = """<a href="/desk#Form/Mitgliedschaft/{0}">""".format(pe_doc.mv_mitgliedschaft) + str(frappe.get_value("Mitgliedschaft", pe_doc.mv_mitgliedschaft, "mitglied_nr")) + """</a>"""
            elif pe_doc.mv_kunde:
                hyperlink = """<a href="/desk#Form/Kunden/{0}">""".format(pe_doc.mv_kunde) + str(pe_doc.mv_kunde) + """</a>"""
            else:
                hyperlink = """---"""
            
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0}</td>
                                <td style="text-align: left;">{1}</td>
                                <td style="text-align: right;">{2}</td>
                            </tr>""".format(hyperlink, \
                            pe_doc.remarks, \
                            "{:,.2f}".format(pe_doc.paid_amount).replace(",", "'"))
        report_data += """</tbody></table>"""
    
    
    frappe.db.set_value('CAMT Import', camt_import, 'report', report_data)
    
    # setzen Status = Closed wenn verbucht = eingelesen
    alter_status = frappe.db.get_value('CAMT Import', camt_import, 'status')
    if alter_status != 'Failed':
        if alter_status != 'Zahlungen eingelesen':
            draft_pe_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabPayment Entry` WHERE `docstatus` = 0 AND `camt_import` = '{camt_import}'""".format(camt_import=camt_import), as_dict=True)[0].qty
            if draft_pe_qty > 0:
                frappe.db.set_value('CAMT Import', camt_import, 'status', 'Verarbeitet')
            else:
                frappe.db.set_value('CAMT Import', camt_import, 'status', 'Closed')