# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import now
from mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft import create_mitgliedschaftsrechnung
from frappe.utils.background_jobs import enqueue
import time
from frappe.utils.csvutils import to_csv as make_csv
from frappe.desk.form.load import get_attachments

class MVJahresversand(Document):
    def validate(self):
        if self.start_on and not self.end_on:
            args = {'jahresversand': self.name}
            enqueue("mvd.mvd.doctype.mv_jahresversand.mv_jahresversand.create_invoices", queue='long', job_name='Jahresversand {sektion_id} {jahr}'.format(sektion_id=self.sektion_id, jahr=self.jahr), timeout=5000, **args)
            frappe.msgprint('Der Background-Job "{titel}" wurde gestartet'.format(titel='Jahresversand {sektion_id} {jahr}'.format(sektion_id=self.sektion_id, jahr=self.jahr)))

    def on_trash(self):
        if self.docstatus != 2:
            to_delete = []
            for sinv in self.invoices:
                to_delete.append(sinv.sales_invoice)
            
            self.invoices = []
            self.save()
            
            for sinv in to_delete:
                sinv = frappe.get_doc("Sales Invoice", sinv)
                sinv.delete()
    
    def on_cancel(self):
        for sinv in self.invoices:
            sinv = frappe.get_doc("Sales Invoice", sinv.sales_invoice)
            sinv.cancel()
    
    def on_submit(self):
        args = {'jahresversand': self.name}
        enqueue("mvd.mvd.doctype.mv_jahresversand.mv_jahresversand.submit_invoices", queue='long', job_name='Buchen von Jahresversand {sektion_id} {jahr}'.format(sektion_id=self.sektion_id, jahr=self.jahr), timeout=5000, **args)
        frappe.msgprint('Der Background-Job "{titel}" wurde gestartet'.format(titel='Buchen von Jahresversand {sektion_id} {jahr}'.format(sektion_id=self.sektion_id, jahr=self.jahr)))

def submit_invoices(jahresversand):
    time.sleep(3)
    jahresversand = frappe.get_doc("MV Jahresversand", jahresversand)
    for sinv in jahresversand.invoices:
        sinv = frappe.get_doc("Sales Invoice", sinv.sales_invoice)
        sinv.submit()
    attachments = get_attachments(jahresversand.doctype, jahresversand.name)
    for attachment in attachments:
        attachment = frappe.get_doc("File", attachment.name)
        attachment.delete()
    get_csv(jahresversand=jahresversand.name, draft=False)
    frappe.publish_realtime(message='Der Background-Job "{titel}" wurde beendet'.format(titel='Buchen von Jahresversand {sektion_id} {jahr}'.format(sektion_id=jahresversand.sektion_id, jahr=jahresversand.jahr)),
                        event='msgprint')

def create_invoices(jahresversand):
    time.sleep(3)
    jahresversand = frappe.get_doc("MV Jahresversand", jahresversand)
    mitgliedschaften = frappe.db.sql("""SELECT `name` FROM `tabMV Mitgliedschaft` WHERE `sektion_id` = '{sektion_id}' AND `status_c` = 'Regulär'""".format(sektion_id=jahresversand.sektion_id), as_dict=True)
    for mitgliedschaft in mitgliedschaften:
        sinv = create_mitgliedschaftsrechnung(mitgliedschaft.name)
        row = jahresversand.append('invoices', {})
        row.mv_mitgliedschaft = mitgliedschaft.name
        row.sales_invoice = sinv
    jahresversand.end_on = now()
    jahresversand.save()
    frappe.publish_realtime(message='Der Background-Job "{titel}" wurde beendet'.format(titel='Jahresversand {sektion_id} {jahr}'.format(sektion_id=jahresversand.sektion_id, jahr=jahresversand.jahr)),
                        event='msgprint')

@frappe.whitelist()
def get_csv(jahresversand=None, draft=True):
    jahresversand = frappe.get_doc("MV Jahresversand", jahresversand)
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
    for row in jahresversand.invoices:
        mitgliedschaft = frappe.get_doc("MV Mitgliedschaft", row.mv_mitgliedschaft)
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
        sinv = frappe.get_doc("Sales Invoice", row.sales_invoice)
        row_data.append(sinv.grand_total or '')
        row_data.append(sinv.esr_reference or '')
        row_data.append('')
        row_data.append(sinv.grand_total or '')
        row_data.append(sinv.esr_reference or '')
        row_data.append('')
        row_data.append(sinv.name or '')
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
    if draft:
        file_name = "DRAFT_Jahresversand_{titel}_{datetime}.csv".format(titel='Jahresversand {sektion_id} {jahr}'.format(sektion_id=jahresversand.sektion_id, jahr=jahresversand.jahr), datetime=now().replace(" ", "_"))
    else:
        file_name = "{titel}_{datetime}.csv".format(titel='Jahresversand {sektion_id} {jahr}'.format(sektion_id=jahresversand.sektion_id, jahr=jahresversand.jahr), datetime=now().replace(" ", "_"))
    
    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "folder": "Home/Attachments",
        "is_private": 1,
        "content": csv_file,
        "attached_to_doctype": 'MV Jahresversand',
        "attached_to_name": jahresversand.name
    })
    
    _file.save()
    
    return 'done'
