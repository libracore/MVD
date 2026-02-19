# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from mvd.mvd.doctype.mitgliedschaft.utils import get_anredekonvention
try:
    from jinja2 import pass_context as context_decorator
except ImportError:
    from jinja2 import contextfunction as context_decorator

class Druckvorlage(Document):
    def validate(self):
        if not self.deaktiviert:
            # self.validiere_inhalt() --> ist obsolet seit der CD Umstellung!
            self.set_validierungsstring()
            self.check_default()
        else:
            self.default = '0'
        self.titel = self.titel.replace("ä", "ae").replace("Ä", "Ae").replace("ö", "oe").replace("Ö", "Oe").replace("ü", "ue").replace("Ü", "Ue")
    
    def validiere_inhalt(self):
        if self.dokument in ('Anmeldung mit EZ', 'Interessent*Innenbrief mit EZ', 'Zuzug mit EZ'):
            if self.mitgliedtyp_c == 'Privat':
                if self.anzahl_seiten == '1':
                    frappe.throw("Es müssen mindestens 2 Seiten aktiviert werden (Mitgliedschaftsrechnung & HV Rechnung)")
                
                if self.anzahl_seiten == '2':
                    if self.seite_1_qrr == 'Keiner' or self.seite_2_qrr == 'Keiner':
                        frappe.throw("Bei 2 Seiten muss sowohl der Mitgliedschafts QRR wie auch der HV QRR ausgewählt werden.")
                    if self.seite_1_qrr == self.seite_2_qrr:
                        frappe.throw("Es kann nicht derselbe QRR Typ für Seite 1 wie auch Seite 2 gewählt werden.")
                
                if self.anzahl_seiten == '3':
                    self.seite_1_qrr = 'Keiner'
                    if self.seite_2_qrr == self.seite_3_qrr:
                        frappe.throw("Es kann nicht derselbe QRR Typ für Seite 2 wie auch Seite 3 gewählt werden.")
                
                mitgliedschaft = False
                hv = False
                if self.anzahl_seiten == '2':
                    if self.seite_1_qrr == 'Mitgliedschaft':
                        mitgliedschaft = True
                    if self.seite_1_qrr == 'HV':
                        hv = True
                    if self.seite_2_qrr == 'Mitgliedschaft':
                        mitgliedschaft = True
                    if self.seite_2_qrr == 'HV':
                        hv = True
                else:
                    if self.seite_2_qrr == 'Mitgliedschaft':
                        mitgliedschaft = True
                    if self.seite_2_qrr == 'HV':
                        hv = True
                    if self.seite_3_qrr == 'Mitgliedschaft':
                        mitgliedschaft = True
                    if self.seite_3_qrr == 'HV':
                        hv = True
                if not mitgliedschaft:
                    frappe.throw("Bitte wählen Sie als QRR Typ exakt einmal Mitgliedschaft aus.")
                if not hv:
                    frappe.throw("Bitte wählen Sie als QRR Typ exakt einmal HV aus.")
            elif self.mitgliedtyp_c == 'Geschäft':
                mitgliedschaft = 0
                hv = 0
                if self.anzahl_seiten == '1':
                    if self.seite_1_qrr == 'Mitgliedschaft':
                        mitgliedschaft += 1
                    if self.seite_1_qrr == 'HV':
                        hv += 1
                elif self.anzahl_seiten == '2':
                    if self.seite_1_qrr == 'Mitgliedschaft':
                        mitgliedschaft += 1
                    if self.seite_1_qrr == 'HV':
                        hv += 1
                    if self.seite_2_qrr == 'Mitgliedschaft':
                        mitgliedschaft += 1
                    if self.seite_2_qrr == 'HV':
                        hv += 1
                else:
                    if self.seite_2_qrr == 'Mitgliedschaft':
                        mitgliedschaft += 1
                    if self.seite_2_qrr == 'HV':
                        hv += 1
                    if self.seite_3_qrr == 'Mitgliedschaft':
                        mitgliedschaft += 1
                    if self.seite_3_qrr == 'HV':
                        hv += 1
                if mitgliedschaft != 1:
                    frappe.throw("Bitte wählen Sie als QRR Typ exakt einmal Mitgliedschaft aus.")
                if hv > 0:
                    frappe.throw("Der QRR Typ HV darf in Kombination mit Mitgliedtyp Geschäft nicht gewählt werden.")
                
        elif self.dokument == 'Begrüssung mit Ausweis':
            if self.doppelseitiger_druck != 1:
                frappe.throw("Aufgrund des Ausweises muss diese Druckvorlage doppelseitig sein.")
            
            ausweis_druck = 0
            if self.seite_1_ausweis:
                ausweis_druck += 1
            if self.seite_2_ausweis:
                ausweis_druck += 1
            if self.seite_3_ausweis:
                ausweis_druck += 1
            if ausweis_druck == 0:
                frappe.throw("Bitte mindestens eine Seite zum Andruck des Ausweises auswählen.")
            elif ausweis_druck > 1:
                frappe.throw("Bitte maximal eine Seite zum Andruck des Ausweises auswählen.")
            
            if ausweis_druck > 0:
                if self.doppelseitiger_druck != 1:
                    frappe.throw("Aufgrund des Ausweises muss diese Druckvorlage doppelseitig sein.")
                if self.seite_1_ausweis:
                    if not self.seite_1_referenzblock_ausblenden:
                        frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                if self.seite_2_ausweis:
                    if self.anzahl_seiten != '1':
                        if not self.seite_2_referenzblock_ausblenden:
                            if not self.seite_2_adressblock_ausblenden:
                                frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                if self.seite_3_ausweis:
                   if self.anzahl_seiten == '3':
                        if not self.seite_3_referenzblock_ausblenden:
                            if not self.seite_3_adressblock_ausblenden:
                                frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                                
        elif self.dokument == 'Zuzug ohne EZ':
            ausweis_druck = 0
            if self.seite_1_ausweis:
                ausweis_druck += 1
            if self.seite_2_ausweis:
                ausweis_druck += 1
            if self.seite_3_ausweis:
                ausweis_druck += 1
            
            if ausweis_druck > 0:
                if self.doppelseitiger_druck != 1:
                    frappe.throw("Aufgrund des Ausweises muss diese Druckvorlage doppelseitig sein.")
                if self.seite_1_ausweis:
                    if not self.seite_1_referenzblock_ausblenden:
                        frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                if self.seite_2_ausweis:
                    if self.anzahl_seiten != '1':
                        if not self.seite_2_referenzblock_ausblenden:
                            if not self.seite_2_adressblock_ausblenden:
                                frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                if self.seite_3_ausweis:
                   if self.anzahl_seiten == '3':
                        if not self.seite_3_referenzblock_ausblenden:
                            if not self.seite_3_adressblock_ausblenden:
                                frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                
        elif self.dokument in ('HV mit EZ', 'Spende mit EZ'):
            qrr_druck = 0
            if self.seite_1_qrr_spende_hv:
                qrr_druck += 1
            if self.seite_2_qrr_spende_hv:
                qrr_druck += 1
            if self.seite_3_qrr_spende_hv:
                qrr_druck += 1
            if qrr_druck == 0:
                frappe.throw("Bitte mindestens eine Seite zum Andruck des QRR Zahlteils auswählen.")
            elif qrr_druck > 1:
                frappe.throw("Bitte maximal eine Seite zum Andruck des QRR Zahlteils auswählen.")
        elif self.dokument == 'Korrespondenz':
            ausweis_druck = 0
            if self.seite_1_ausweis:
                ausweis_druck += 1
            if self.seite_2_ausweis:
                ausweis_druck += 1
            if self.seite_3_ausweis:
                ausweis_druck += 1
            if ausweis_druck > 0:
                if self.doppelseitiger_druck != 1:
                    frappe.throw("Aufgrund des Ausweises muss diese Druckvorlage doppelseitig sein.")
                if self.seite_1_ausweis:
                    if not self.seite_1_referenzblock_ausblenden:
                        frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                if self.seite_2_ausweis:
                    if self.anzahl_seiten != '1':
                        if not self.seite_2_referenzblock_ausblenden:
                            if not self.seite_2_adressblock_ausblenden:
                                frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                if self.seite_3_ausweis:
                   if self.anzahl_seiten == '3':
                        if not self.seite_3_referenzblock_ausblenden:
                            if not self.seite_3_adressblock_ausblenden:
                                frappe.throw("Aufgrund des Ausweises muss der Referenzblock ausgeblendet sein.")
                
    
    def set_validierungsstring(self):
        if self.dokument != 'Geschenkmitgliedschaft':
            if self.dokument != 'Mahnung':
                validierungsstring = ''
                validierungsstring += self.sektion_id + "-"
                validierungsstring += self.language + "-"
                validierungsstring += self.dokument + "-"
                validierungsstring += self.mitgliedtyp_c + "-"
                validierungsstring += str(self.reduzierte_mitgliedschaft)
            else:
                validierungsstring = ''
                validierungsstring += self.sektion_id + "-"
                validierungsstring += self.language + "-"
                validierungsstring += self.dokument + "-"
                validierungsstring += self.mitgliedtyp_c + "-"
                validierungsstring += self.mahntyp + "-"
                validierungsstring += self.mahnstufe + "-"
                validierungsstring += str(self.e_mail_vorlage) if self.e_mail_vorlage else '0'
                validierungsstring += '-'
                validierungsstring += str(self.reduzierte_mitgliedschaft)
        else:
            validierungsstring = ''
            validierungsstring += self.sektion_id + "-"
            validierungsstring += self.language + "-"
            validierungsstring += self.dokument + "-"
            validierungsstring += self.geschenkmitgliedschaft_dok_empfaenger
        
        self.validierungsstring = validierungsstring
    
    def check_default(self):
        anz_defaults = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabDruckvorlage` WHERE `validierungsstring` = '{validierungsstring}' AND `default` = 1 AND `name` != '{name}'""".format(validierungsstring=self.validierungsstring, name=self.name), as_dict=True)[0].qty
        if anz_defaults > 0:
            if self.default == 1:
                defaults = frappe.db.sql("""SELECT `name` FROM `tabDruckvorlage` WHERE `validierungsstring` = '{validierungsstring}' AND `default` = 1 AND `name` != '{name}'""".format(validierungsstring=self.validierungsstring, name=self.name), as_dict=True)
                for default in defaults:
                    frappe.db.sql("""UPDATE `tabDruckvorlage` SET `default` = 0 WHERE `name` = '{name}'""".format(name=default.name), as_list=True)
        else:
            if self.default != 1:
                self.default = 1
    
    def test_druck(self, test_dt, test_dn):
        frappe.db.set_value("Druckvorlage", self.name, "test_dt", test_dt, update_modified=False)
        frappe.db.set_value("Druckvorlage", self.name, "test_dn", test_dn, update_modified=False)
        return

@frappe.whitelist()
def get_druckvorlagen(sektion, dokument='Korrespondenz', mitgliedtyp=False, reduzierte_mitgliedschaft=False, language=False, serienbrief=False):
    user = frappe.session.user
    if "System Manager" in frappe.get_roles(user):
        sektionen_filter = """`sektion_id` IN ('{0}', '{1}')""".format(sektion, 'MVD')
    elif "MV_MVD" in frappe.get_roles(user):
        sektionen_filter = """`sektion_id` IN ('{0}', '{1}')""".format(sektion, 'MVD')
    else:
        sektionen_filter = """`sektion_id` = '{0}'""".format(sektion)
    
    if not serienbrief:
        additional_filters = ''
        if mitgliedtyp:
            additional_filters += """ AND `mitgliedtyp_c` = '{mitgliedtyp}'""".format(mitgliedtyp=mitgliedtyp)
        if language:
            additional_filters += """ AND `language` = '{language}'""".format(language=language)
        
        _alle_druckvorlagen = frappe.db.sql("""SELECT
                                                `name`,
                                                `default`
                                            FROM `tabDruckvorlage`
                                            WHERE {sektionen_filter}
                                            AND `deaktiviert` != 1
                                            AND `dokument` = '{dokument}'
                                            {additional_filters}""".format(sektionen_filter=sektionen_filter, dokument=dokument, additional_filters=additional_filters), as_dict=True)
        
        alle_druckvorlagen = []
        default_druckvorlage = ''
        for druckvorlage in _alle_druckvorlagen:
            if int(druckvorlage.default) == 1:
                default_druckvorlage = druckvorlage.name
            alle_druckvorlagen.append(druckvorlage.name)
        
        return {
            'alle_druckvorlagen': alle_druckvorlagen,
            'default_druckvorlage': default_druckvorlage
        }
    else:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", sektion)
        sektion = mitgliedschaft.sektion_id
        druckvorlagen = frappe.db.sql("""SELECT
                                                `name`
                                            FROM `tabDruckvorlage`
                                            WHERE `sektion_id` = '{sektion}'
                                            AND `deaktiviert` != 1
                                            AND `dokument` = '{dokument}'""".format(sektion=sektion, dokument=dokument), as_dict=True)
        
        alle_druckvorlagen = []
        for druckvorlage in druckvorlagen:
            alle_druckvorlagen.append(druckvorlage.name)
        
        return alle_druckvorlagen

def replace_mv_keywords(txt, mitgliedschaft, mahnung=False, idx=False, sinv=False, fr=False):
    nur_kunde = False
    try:
        mitgliedschaft.name
        if mitgliedschaft.doctype == 'Kunden':
            nur_kunde = True
    except:
        if 'MV-K' in mitgliedschaft:
            nur_kunde = True
            mitgliedschaft = frappe.get_doc("Kunden", mitgliedschaft)
        else:
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    
    if not nur_kunde:
        key_words = [
            {'key_word': '%%ANREDE%%', 'value': mitgliedschaft.briefanrede or get_anredekonvention(self=mitgliedschaft) if not mahnung and not sinv else mitgliedschaft.rg_briefanrede or get_anredekonvention(self=mitgliedschaft, rg=True)},
            {'key_word': '%%MIETGLIEDERNUMMER%%', 'value': mitgliedschaft.mitglied_nr},
            {'key_word': '%%ANREDE BESCHENKTE%%', 'value': mitgliedschaft.briefanrede or get_anredekonvention(self=mitgliedschaft)},
            {'key_word': '%%ANREDE SCHENKENDE%%', 'value': mitgliedschaft.rg_briefanrede or get_anredekonvention(self=mitgliedschaft, rg=True)},
            {'key_word': '%%VOR- NACHNAME BESCHENKTE%%', 'value': " ".join((mitgliedschaft.vorname_1 or '', mitgliedschaft.nachname_1 or ''))},
            {'key_word': '%%VOR- NACHNAME SCHENKENDE%%', 'value': " ".join((mitgliedschaft.rg_vorname or '', mitgliedschaft.rg_nachname or ''))},
            {'key_word': '%%DIGITALERECHNUNGLINK%%', 'value': "https://libracore.mieterverband.ch/digitalrechnung?hash={0}".format(mitgliedschaft.mitglied_hash) if mitgliedschaft.mitglied_hash else '(URL nicht verfügbar)'}
        ]
    else:
        key_words = [
            {'key_word': '%%MIETGLIEDERNUMMER%%', 'value': '---'},
            {'key_word': '%%ANREDE%%', 'value': get_anredekonvention(self=mitgliedschaft)}
        ]
    
    if sinv or fr:
        rechnungsjahr = ""
        if sinv:
            sinv = frappe.get_doc("Sales Invoice", sinv)
            amount = sinv.outstanding_amount
            rechnungsnummer = sinv.name
            rechnungsjahr = sinv.mitgliedschafts_jahr or ""
            key_words.append({
                'key_word': '%%ARTIKELTABELLE%%', 'value': get_item_table(sinv)
            })
            key_words.append({
                'key_word': '%%WEBSHOPDATUM%%', 'value': get_webshop_datum(sinv)
            })
        if fr:
            fr = frappe.get_doc("Fakultative Rechnung", fr)
            amount = fr.betrag
            rechnungsnummer = fr.name
        key_words.append({
            'key_word': '%%RECHNUNGSBETRAG%%', 'value': "{:,.2f}".format(amount).replace(",", "'")
        })
        key_words.append({
            'key_word': '%%RECHNUNGSNUMMER%%', 'value': rechnungsnummer
        })
        key_words.append({
            'key_word': '%%RECHNUNGSJAHR%%', 'value': str(rechnungsjahr)
        })
    
    if mahnung:
        mahnung = frappe.get_doc("Mahnung", mahnung)
        key_words.append({
            'key_word': '%%Gesamtbetrag_gemahnte_Rechnungen%%', 'value': "{:,.2f}".format(mahnung.total_with_charge).replace(",", "'")
        })
        key_words.append({
            'key_word': '%%RECHNUNGSDATUM%%', 'value': frappe.utils.get_datetime(mahnung.sales_invoices[idx].posting_date).strftime('%d.%m.%Y')
        })
        if mahnung.sales_invoices[idx].ist_mitgliedschaftsrechnung:
            if mahnung.sales_invoices[idx].amount == mahnung.sales_invoices[idx].outstanding_amount:
                key_words.append({
                    'key_word': '%%Jahresrechnung_Jahr%%', 'value': str(mahnung.sales_invoices[idx].mitgliedschafts_jahr)
                })
            else:
                key_words.append({
                    'key_word': '%%Jahresrechnung_Jahr%%', 'value': str(mahnung.sales_invoices[idx].mitgliedschafts_jahr) + ' (Restbetrag)'
                })
        else:
            if mahnung.sales_invoices[idx].amount == mahnung.sales_invoices[idx].outstanding_amount:
                key_words.append({
                    'key_word': '%%Jahresrechnung_Jahr%%', 'value': 'Rechnung vom ' + frappe.utils.get_datetime(mahnung.sales_invoices[idx].posting_date).strftime('%d.%m.%Y')
                })
            else:
                key_words.append({
                    'key_word': '%%Jahresrechnung_Jahr%%', 'value': 'Rechnung vom ' + frappe.utils.get_datetime(mahnung.sales_invoices[idx].posting_date).strftime('%d.%m.%Y') + ' (Restbetrag)'
                })
    for key_word in key_words:
        txt = txt.replace(key_word['key_word'], key_word['value'])
    return txt

def get_item_table(sinv):
    taxes = {}
    for tax in sinv.taxes:
        taxes[tax.description] = 0
    
    mwst = 0 if frappe.db.get_value("Sektion", sinv.sektion_id, "mwst_faktura_ausblenden") == 1 else 1
    
    table = """
                <table id="item_table" style="width: 100%;">
                    <thead>
                        <tr style="border-bottom: 1px solid black;">
                            <th style="text-align: left;">Anz.</th>
                            <th style="text-align: left;">Bezeichnung</th>
                            <th style="text-align: right;">Einzelpreis</th>
                            <th style="text-align: right;">Total</th>
                            <th style="text-align: right;">{mwst}</th>
                        </tr>
                    </thead>
                    <tbody>""".format(mwst="MWST" if mwst == 1 else '')
    for item in sinv.items:
        if item.description.replace("<div>", "").replace("</div>", "") == item.item_code:
            bezeichnung = item.item_name
        else:
            bezeichnung = item.description
        table += """
                    <tr>
                        <td style="text-align: left;">{qty}</td>
                        <td style="text-align: left;">{bez}</td>
                        <td style="text-align: right;">{einzp}</td>
                        <td style="text-align: right;">{total}</td>
                        <td style="text-align: right;">{mwst}</td>
                    </tr>""".format(qty=int(item.qty), \
                                    bez=bezeichnung, \
                                    einzp="{:,.2f}".format(item.rate).replace(",", "'"), \
                                    total="{:,.2f}".format(item.amount).replace(",", "'"), \
                                    mwst=item.item_tax_template or '0%' if mwst == 1 else '')
        if item.item_tax_template and item.item_tax_template in taxes:
            taxes[item.item_tax_template] += item.amount
    
    table += """
                <tr style="border-bottom: 1px solid black; border-top: 1px solid black;">
                    <td colspan="2" style="text-align: left;"><b>Total</b>{mwst}</td>
                    <td style="text-align: right;">Fr.</td>
                    <td style="text-align: right;">{grand_total}</td>
                    <td></td>
                </tr>""".format(grand_total="{:,.2f}".format(sinv.grand_total).replace(",", "'"), mwst=" (inkl. MWSt.)" if mwst == 1 else '')
    
    if mwst == 1:
        table += """
                    <tr style="line-height: 1;">
                        <td colspan="2" style="text-align: left; font-size: 8px;">Unsere MWST-Nr: CHE-100.822.971 MWST</td>
                        <td colspan="3" style="text-align: right;"><table style="width: 100%;">"""
        for tax in sinv.taxes:
            if tax.tax_amount > 0:
                table += """<tr style="line-height: 1;">
                                <td style="padding-top: 0px !important; text-align: right; font-size: 8px; padding-top: 0px !important; padding-bottom: 0px !important;">Satz:</td>
                                <td style="padding-top: 0px !important; text-align: right; font-size: 8px; padding-top: 0px !important; padding-bottom: 0px !important;">{satz}</td>
                                <td style="padding-top: 0px !important; text-align: right; font-size: 8px; padding-top: 0px !important; padding-bottom: 0px !important;">Betrag:</td>
                                <td style="padding-top: 0px !important; text-align: right; font-size: 8px; padding-top: 0px !important; padding-bottom: 0px !important;">{betrag}</td>
                                <td style="padding-top: 0px !important; text-align: right; font-size: 8px; padding-top: 0px !important; padding-bottom: 0px !important;">Steuer:</td>
                                <td style="padding-top: 0px !important; text-align: right; font-size: 8px; padding-top: 0px !important; padding-bottom: 0px !important;">{steuer}</td>
                            </tr>""".format(satz=tax.description, \
                                            betrag="{:,.2f}".format(taxes[tax.description]).replace(",", "'"), \
                                            steuer="{:,.2f}".format(tax.tax_amount).replace(",", "'"))
        table += """</table></td></tr>"""
    
    table += """
                    </tbody>
                </table>"""
    
    return table

def get_webshop_datum(sinv):
    webshop_orders = frappe.db.sql("""SELECT `creation` FROM `tabWebshop Order` WHERE `sinv` = '{0}' ORDER BY `creation` DESC""".format(sinv.name), as_dict=True)
    if len(webshop_orders) > 0:
        return frappe.utils.get_datetime(webshop_orders[0].creation).strftime('%d.%m.%Y')
    else:
        return ''

def get_doc_from_ctx(ctx):
    doc = ctx.get("doc", None)
    return doc or ctx

@context_decorator
def get_anrede(ctx):
    doc = get_doc_from_ctx(ctx)

    mv_mitgliedschaft = doc.get("mv_mitgliedschaft", False)
    if mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mv_mitgliedschaft)
        if doc.get("doctype") not in ["Sales Invoice", "Mahnung"]:
            return mitgliedschaft.briefanrede or get_anredekonvention(self=mitgliedschaft)
        else:
            return mitgliedschaft.rg_briefanrede or get_anredekonvention(self=mitgliedschaft, rg=True)
    
    mv_kunde = doc.get("mv_kunde", False)
    if mv_kunde:
        mitgliedschaft = frappe.get_doc("Kunden", mv_kunde)
        return get_anredekonvention(self=mitgliedschaft)

    return 'Guten Tag'

@context_decorator
def get_anrede_beschenkte(ctx):
    doc = get_doc_from_ctx(ctx)

    mv_mitgliedschaft = doc.get("mv_mitgliedschaft", False)
    if mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mv_mitgliedschaft)
        return mitgliedschaft.briefanrede or get_anredekonvention(self=mitgliedschaft)

    return 'Guten Tag'

@context_decorator
def get_anrede_schenkende(ctx):
    doc = get_doc_from_ctx(ctx)

    mv_mitgliedschaft = doc.get("mv_mitgliedschaft", False)
    if mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mv_mitgliedschaft)
        return mitgliedschaft.rg_briefanrede or get_anredekonvention(self=mitgliedschaft, rg=True)

    return 'Guten Tag'

@context_decorator
def get_mitgliedernummer(ctx):
    doc = get_doc_from_ctx(ctx)

    mitgliedernummer = '---'
    mv_mitgliedschaft = doc.get("mv_mitgliedschaft", False)
    if mv_mitgliedschaft:
        mitgliedernummer = frappe.db.get_value("Mitgliedschaft", doc.get("mv_mitgliedschaft"), "mitglied_nr")

    return mitgliedernummer

@context_decorator
def get_vor_und_nachname_beschenkte(ctx):
    doc = get_doc_from_ctx(ctx)

    mv_mitgliedschaft = doc.get("mv_mitgliedschaft", False)
    if mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mv_mitgliedschaft)
        return " ".join((mitgliedschaft.vorname_1 or '', mitgliedschaft.nachname_1 or ''))

    return '---'

@context_decorator
def get_vor_und_nachname_schenkende(ctx):
    doc = get_doc_from_ctx(ctx)

    mv_mitgliedschaft = doc.get("mv_mitgliedschaft", False)
    if mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mv_mitgliedschaft)
        return " ".join((mitgliedschaft.rg_vorname or '', mitgliedschaft.rg_nachname or ''))

    return '---'

@context_decorator
def get_digitalrechnung_link(ctx):
    doc = get_doc_from_ctx(ctx)

    mv_mitgliedschaft = doc.get("mv_mitgliedschaft", False)
    if mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mv_mitgliedschaft)
        return "https://libracore.mieterverband.ch/digitalrechnung?hash={0}".format(mitgliedschaft.mitglied_hash) if mitgliedschaft.mitglied_hash else '(URL nicht verfügbar)'

    return '(URL nicht verfügbar)'

@context_decorator
def get_austritt_per(ctx):
    doc = get_doc_from_ctx(ctx)
    mv_mitgliedschaft = doc.get("mv_mitgliedschaft", False)
    if mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mv_mitgliedschaft)
        if mitgliedschaft.kuendigung:
            return mitgliedschaft.kuendigung.strftime('%d.%m.%Y')
        else:
            return "ES GIBT KEIN KÜNDIGUNG PER DATUM"
        
    return '---'

@context_decorator
def get_eintrittsdatum(ctx):
    doc = get_doc_from_ctx(ctx)
    mv_mitgliedschaft = doc.get("mv_mitgliedschaft", False)
    if mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mv_mitgliedschaft)
        if mitgliedschaft.eintrittsdatum:
            return mitgliedschaft.eintrittsdatum.strftime('%d.%m.%Y')
        
    return '---'

@context_decorator
def get_versichertes_objekt(ctx):
    doc = get_doc_from_ctx(ctx)
    mv_mitgliedschaft = doc.get("mv_mitgliedschaft", False)
    if mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mv_mitgliedschaft)
        strasse = mitgliedschaft.objekt_strasse or ""
        hausnummer = mitgliedschaft.objekt_hausnummer or ""
        zusatz = mitgliedschaft.get("objekt_nummer_zu") or ""
        adresse = "{} {} {}".format(strasse, hausnummer, zusatz).strip().replace("  ", " ")

        return adresse if adresse else "---"
    
    return '---'
        
@context_decorator
def get_versichertes_objekt_ort(ctx):
    doc = get_doc_from_ctx(ctx)
    mv_mitgliedschaft = doc.get("mv_mitgliedschaft", False)
    if mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mv_mitgliedschaft)
        ort = mitgliedschaft.objekt_ort or ""

        return ort if ort else "---"

    return '---'

@context_decorator
def get_artikeltabelle(ctx):
    doc = get_doc_from_ctx(ctx)

    if doc.get("doctype") == "Sales Invoice":
        sinv = frappe.get_doc("Sales Invoice", doc.get("name"))
        return get_item_table(sinv)
    
    if doc.get("doctype") == "Mahnung":
        mahnung = frappe.get_doc("Mahnung", doc.get("name"))
        sinv = frappe.get_doc("Sales Invoice", mahnung.sales_invoices[0].sales_invoice)
        return get_item_table(sinv)
    
    return '---'

@context_decorator
def get_webshopdatum(ctx):
    doc = get_doc_from_ctx(ctx)

    if doc.get("doctype") == "Sales Invoice":
        sinv = frappe.get_doc("Sales Invoice", doc.get("name"))
        return get_webshop_datum(sinv)
    
    return '---'

@context_decorator
def get_rechnungsbetrag(ctx):
    doc = get_doc_from_ctx(ctx)

    if doc.get("doctype") == "Sales Invoice":
        return "{:,.2f}".format(doc.get("outstanding_amount")).replace(",", "'")

    if doc.get("doctype") == "Fakultative Rechnung":
        return "{:,.2f}".format(doc.get("betrag")).replace(",", "'")
    
    return '---'

@context_decorator
def get_rechnungsnummer(ctx):
    doc = get_doc_from_ctx(ctx)
    return doc.get("name")

@context_decorator
def get_rechnungsjahr(ctx):
    doc = get_doc_from_ctx(ctx)

    if doc.get("doctype") == "Sales Invoice":
        return doc.get("mitgliedschafts_jahr", "---")
    
    return '---'

@context_decorator
def get_gesamtbetrag_gemahnte_rechnungen(ctx):
    doc = get_doc_from_ctx(ctx)

    if doc.get("doctype") == "Mahnung":
        return "{:,.2f}".format(doc.get("total_with_charge")).replace(",", "'")
    
    return '---'

@context_decorator
def get_rechnungsdatum(ctx):
    doc = get_doc_from_ctx(ctx)

    if doc.get("doctype") == "Mahnung":
        mahnung = frappe.get_doc("Mahnung", doc.get("name"))
        return frappe.utils.get_datetime(mahnung.sales_invoices[0].posting_date).strftime('%d.%m.%Y')
    
    return '---'

@context_decorator
def get_jahresrechnung_jahr(ctx):
    doc = get_doc_from_ctx(ctx)

    if doc.get("doctype") == "Mahnung":
        mahnung = frappe.get_doc("Mahnung", doc.get("name"))
        if mahnung.sales_invoices[0].ist_mitgliedschaftsrechnung:
            if mahnung.sales_invoices[0].amount == mahnung.sales_invoices[0].outstanding_amount:
                return str(mahnung.sales_invoices[0].mitgliedschafts_jahr)
            else:
                return str(mahnung.sales_invoices[0].mitgliedschafts_jahr) + ' (Restbetrag)'
        else:
            if mahnung.sales_invoices[0].amount == mahnung.sales_invoices[0].outstanding_amount:
                return frappe.utils.get_datetime(mahnung.sales_invoices[0].posting_date).strftime('%d.%m.%Y')
            else:
                return frappe.utils.get_datetime(mahnung.sales_invoices[0].posting_date).strftime('%d.%m.%Y') + ' (Restbetrag)'
    
    return '---'