# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import add_days, getdate, now, today
from mvd.mvd.utils.qrr_reference import get_qrr_reference
import json
from PyPDF2 import PdfFileWriter
from mvd.mvd.doctype.arbeits_backlog.arbeits_backlog import create_abl
from mvd.mvd.doctype.fakultative_rechnung.fakultative_rechnung import create_hv_fr
from frappe.utils.pdf import get_file_data_from_writer
from mvd.mvd.doctype.druckvorlage.druckvorlage import get_druckvorlagen

class Mitgliedschaft(Document):
    def set_new_name(self):
        if not self.mitglied_id:
            mitglied_nummer_obj = mvm_neue_mitglieder_nummer(self)
            if mitglied_nummer_obj:
                self.mitglied_id = mitglied_nummer_obj["mitgliedId"]
                if not self.mitglied_nr or self.mitglied_nr == 'MV':
                    if mitglied_nummer_obj["mitgliedNummer"]:
                        self.mitglied_nr = mitglied_nummer_obj["mitgliedNummer"]
                    else:
                        self.mitglied_nr = 'MV'
            else:
                frappe.throw("Die gewünschte Mitgliedschaft konnte nicht erstellt werden.")
        return
    
    def validate(self):
        if not self.validierung_notwendig or str(self.validierung_notwendig) == '0':
            # entferne Telefonnummern mit vergessenen Leerschlägen
            self.remove_unnecessary_blanks()
            
            # handling von Kontakt(en), Adresse(n) und Kunde(n)
            self.handling_kontakt_adresse_kunde()
            
            # entferne "Postfach" aus Strasse falls vorhanden
            if int(self.postfach) == 1 and self.strasse == 'Postfach':
                self.strasse = ''
            
            # Briefanrede
            self.briefanrede = get_anredekonvention(self=self)
            
            # Rechnungs Briefanrede
            self.rg_briefanrede = get_anredekonvention(self=self, rg=True)
            
            # Adressblock
            self.adressblock = get_adressblock(self)
            
            # Rechnungs Adressblock
            self.rg_adressblock = get_rg_adressblock(self)
            
            # update Zahlung Mitgliedschaft
            self.check_zahlung_mitgliedschaft()
            
            # update Zahlung HV
            self.check_zahlung_hv()
            
            # preisregel
            self.check_preisregel()
            
            # ampelfarbe
            self.ampel_farbe = get_ampelfarbe(self)
            
            # Zuzugs-Korrespondenz für Massenlauf
            if self.zuzug_von and int(self.zuzug_massendruck) == 1:
                if not self.zuzugs_rechnung and not self.zuzug_korrespondenz:
                    if self.kunde_mitglied:
                        self.zuzug_massenlauf_korrespondenz()
                        
            
            # eintrittsdatum fix
            if self.eintritt and not self.eintrittsdatum:
                self.eintrittsdatum = self.eintritt
            
            # setze CB "Aktive Mitgliedschaft"
            if self.status_c not in ('Gestorben', 'Wegzug', 'Ausschluss', 'Inaktiv'):
                self.aktive_mitgliedschaft = 1
            else:
                self.aktive_mitgliedschaft = 0
            
            # schliesse offene abreits backlogs
            close_open_validations(self.name, 'Daten Validieren')
            if not int(self.interessent_innenbrief_mit_ez) == 1:
                close_open_validations(self.name, 'Interessent*Innenbrief mit EZ')
            if not int(self.anmeldung_mit_ez) == 1:
                close_open_validations(self.name, 'Anmeldung mit EZ')
            
            # beziehe mitglied_nr wenn umwandlung von Interessent*in
            if self.status_c != 'Interessent*in' and self.mitglied_nr == 'MV':
                self.mitglied_nr = mvm_mitglieder_nummer_update(self.name)
                self.letzte_bearbeitung_von = 'User'
            
            # hotfix für onlineHaftpflicht value (null vs 0)
            if not self.online_haftpflicht:
                self.online_haftpflicht = '0'
            
            # Mahnstopp in Rechnungen setzen
            if self.status_c in ('Gestorben', 'Ausschluss'):
                self.mahnstopp = '2099-12-31'
            
            if self.mahnstopp:
                mahnstopp(self.name, self.mahnstopp)
            
            # sende neuanlage/update an sp wenn letzter bearbeiter nich SP
            if self.letzte_bearbeitung_von == 'User':
                if self.creation == self.modified:
                    # sende neuanlage an SP
                    send_mvm_to_sp(self, False)
                else:
                    # sende update an SP
                    send_mvm_to_sp(self, True)
                    # special case sektionswechsel nach ZH
                    if self.wegzug_zu in ('MVZH', 'MVSO') and self.status_c == 'Wegzug':
                        send_mvm_sektionswechsel(self)
    
    def remove_unnecessary_blanks(self):
        # Hauptmitglied
        if self.tel_p_1:
            if not len(self.tel_p_1.replace(" ", "")) > 0:
                self.tel_p_1 = None
        if self.tel_m_1:
            if not len(self.tel_m_1.replace(" ", "")) > 0:
                self.tel_m_1 = None
        if self.tel_g_1:
            if not len(self.tel_g_1.replace(" ", "")) > 0:
                self.tel_g_1 = None
        
        # Solidarmitglied
        if self.tel_p_2:
            if not len(self.tel_p_2.replace(" ", "")) > 0:
                self.tel_p_2 = None
        if self.tel_m_2:
            if not len(self.tel_m_2.replace(" ", "")) > 0:
                self.tel_m_2 = None
        if self.tel_g_2:
            if not len(self.tel_g_2.replace(" ", "")) > 0:
                self.tel_g_2 = None
        
        # Rechnungskontakt
        if self.rg_tel_p:
            if not len(self.rg_tel_p.replace(" ", "")) > 0:
                self.rg_tel_p = None
        if self.rg_tel_m:
            if not len(self.rg_tel_m.replace(" ", "")) > 0:
                self.rg_tel_m = None
        if self.rg_tel_g:
            if not len(self.rg_tel_g.replace(" ", "")) > 0:
                self.rg_tel_g = None
    
    def zuzug_massenlauf_korrespondenz(self):
        # erstelle ggf. neue Rechnung
        mit_rechnung = False
        if self.bezahltes_mitgliedschaftsjahr < int(now().split("-")[0]):
            if self.naechstes_jahr_geschuldet == 1:
                mit_rechnung = create_mitgliedschaftsrechnung(self.name, jahr=int(now().split("-")[0]), submit=True, attach_as_pdf=True, druckvorlage=get_druckvorlagen(sektion=self.sektion_id, dokument='Zuzug mit EZ', mitgliedtyp=self.mitgliedtyp_c, reduzierte_mitgliedschaft=self.reduzierte_mitgliedschaft, language=self.language)['default_druckvorlage'])
        
        
        if mit_rechnung:
            self.zuzugs_rechnung = mit_rechnung
        else:
            druckvorlage = frappe.get_doc("Druckvorlage", get_druckvorlagen(sektion=self.sektion_id, dokument='Zuzug ohne EZ', mitgliedtyp=self.mitgliedtyp_c, reduzierte_mitgliedschaft=self.reduzierte_mitgliedschaft, language=self.language)['default_druckvorlage'])
            _new_korrespondenz = frappe.copy_doc(druckvorlage)
            _new_korrespondenz.doctype = 'Korrespondenz'
            _new_korrespondenz.sektion_id = self.sektion_id
            _new_korrespondenz.titel = 'Zuzug ohne EZ'
            
            new_korrespondenz = frappe._dict(_new_korrespondenz.as_dict())
            keys_to_remove = [
                'mitgliedtyp_c',
                'validierungsstring',
                'language',
                'reduzierte_mitgliedschaft',
                'dokument',
                'default',
                'deaktiviert',
                'seite_1_qrr',
                'seite_1_qrr_spende_hv',
                'seite_2_qrr',
                'seite_2_qrr_spende_hv',
                'seite_3_qrr',
                'seite_3_qrr_spende_hv',
                'blatt_2_info_mahnung',
                'tipps_mahnung'
            ]
            for key in keys_to_remove:
                try:
                    new_korrespondenz.pop(key)
                except:
                    pass
            
            new_korrespondenz['mv_mitgliedschaft'] = self.mitglied_id
            new_korrespondenz['massenlauf'] = 0
            
            new_korrespondenz = frappe.get_doc(new_korrespondenz)
            new_korrespondenz.insert(ignore_permissions=True)
            frappe.db.commit()
            
            self.zuzug_korrespondenz =  new_korrespondenz.name
    
    def handling_kontakt_adresse_kunde(self):
        # Mitglied
        self.kunde_mitglied = self.validate_kunde_mitglied()
        self.kontakt_mitglied = self.validate_kontakt_mitglied(primary=True)
        self.adresse_mitglied, self.objekt_adresse = self.validate_adresse_mitglied()
        join_mitglied_contact_and_address(self.kontakt_mitglied, self.adresse_mitglied)
        
        # Solidarmitglied
        if self.hat_solidarmitglied:
            self.kontakt_solidarmitglied = self.validate_kontakt_mitglied(primary=False)
            if not self.kontakt_solidarmitglied:
                self.hat_solidarmitglied = '0'
            else:
                if self.objekt_adresse:
                    join_mitglied_contact_and_address(self.kontakt_solidarmitglied, self.objekt_adresse)
                else:
                    join_mitglied_contact_and_address(self.kontakt_solidarmitglied, self.adresse_mitglied)
        else:
            if self.kontakt_solidarmitglied:
                self.kontakt_solidarmitglied = self.remove_solidarmitglied()
        
        # Rechnungsempfaenger
        if self.abweichende_rechnungsadresse:
            if self.unabhaengiger_debitor:
                self.rg_kunde = self.validate_rg_kunde()
                self.rg_kontakt = self.validate_rg_kontakt()
            else:
                self.rg_kunde = ''
                self.rg_kontakt = ''
            self.rg_adresse = self.validate_rg_adresse()
        else:
            self.rg_kunde = ''
            self.rg_kontakt = ''
            self.rg_adresse = ''
    
    def check_preisregel(self):
        if int(self.reduzierte_mitgliedschaft) == 1:
            if not self.existing_preisregel():
                self.erstelle_preisregel()
            else:
                self.update_preisregel()
        else:
            if self.existing_preisregel():
                self.deaktiviere_preisregel()
    
    def existing_preisregel(self):
        qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabPricing Rule`
                                WHERE `name` = 'Reduzierung {mitglied_id}'""".format(mitglied_id=str(self.mitglied_id)), as_dict=True)[0].qty
        if int(qty) > 0:
            return True
        else:
            return False
    
    def deaktiviere_preisregel(self):
        customer = self.rg_kunde if self.rg_kunde else self.kunde_mitglied
        _pr = frappe.db.sql("""SELECT `name` FROM `tabPricing Rule`
                                WHERE `name` = 'Reduzierung {mitglied_id}'""".format(mitglied_id=str(self.mitglied_id)), as_dict=True)
        if len(_pr) > 0:
            pr = frappe.get_doc("Pricing Rule", _pr[0].name)
            pr.disable = 1
            pr.save(ignore_permissions=True)
            return
        else:
            return
    
    def erstelle_preisregel(self):
        customer = self.rg_kunde if self.rg_kunde else self.kunde_mitglied
        sektion = frappe.get_doc("Sektion", self.sektion_id)
        new_pr = frappe.get_doc({
            'doctype': 'Pricing Rule',
            'title': 'Reduzierung ' + str(self.mitglied_id),
            'selling': 1,
            'applicable_for': 'Customer',
            'customer': customer,
            'valid_from': '',
            'valid_upto': self.reduzierung_bis,
            'rate_or_discount': 'Rate',
            'rate': self.reduzierter_betrag,
            'items': [
                {
                    'item_code': sektion.mitgliedschafts_artikel if self.mitgliedtyp_c == 'Privat' else sektion.mitgliedschafts_artikel_geschaeft
                }
            ]
        })
        
        new_pr.insert(ignore_permissions=True)
        frappe.db.commit()
        return
    
    def update_preisregel(self):
        customer = self.rg_kunde if self.rg_kunde else self.kunde_mitglied
        sektion = frappe.get_doc("Sektion", self.sektion_id)
        _pr = frappe.db.sql("""SELECT `name` FROM `tabPricing Rule`
                                WHERE `name` = 'Reduzierung {mitglied_id}'""".format(mitglied_id=str(self.mitglied_id)), as_dict=True)
        if len(_pr) > 0:
            pr = frappe.get_doc("Pricing Rule", _pr[0].name)
            pr.disable = 0
            pr.customer = customer
            pr.valid_upto = self.reduzierung_bis
            pr.rate = self.reduzierter_betrag
            pr.items[0].item_code = sektion.mitgliedschafts_artikel if self.mitgliedtyp_c == 'Privat' else sektion.mitgliedschafts_artikel_geschaeft
            pr.save(ignore_permissions=True)
            return
        else:
            return
        
    def check_zahlung_mitgliedschaft(self):
        noch_kein_eintritt = False
        if not self.datum_zahlung_mitgliedschaft:
            noch_kein_eintritt = True
        
        sinvs = frappe.db.sql("""SELECT
                                    `name`,
                                    `is_pos`,
                                    `posting_date`,
                                    `mitgliedschafts_jahr`
                                FROM `tabSales Invoice`
                                WHERE `docstatus` = 1
                                AND `ist_mitgliedschaftsrechnung` = 1
                                AND `mv_mitgliedschaft` = '{mvm}'
                                AND `status` = 'Paid'
                                ORDER BY `mitgliedschafts_jahr` DESC""".format(mvm=self.name), as_dict=True)
        if len(sinvs) > 0:
            sinv = sinvs[0]
            if sinv.is_pos == 1:
                sinv_year = getdate(sinv.posting_date).strftime("%Y")
                self.datum_zahlung_mitgliedschaft = sinv.posting_date
            else:
                pes = frappe.db.sql("""SELECT `parent` FROM `tabPayment Entry Reference`
                                        WHERE `reference_doctype` = 'Sales Invoice'
                                        AND `reference_name` = '{sinv}' ORDER BY `creation` DESC""".format(sinv=sinv.name), as_dict=True)
                if len(pes) > 0:
                    pe = frappe.get_doc("Payment Entry", pes[0].parent)
                    sinv_year = getdate(pe.reference_date).strftime("%Y")
                    self.datum_zahlung_mitgliedschaft = pe.reference_date
                else:
                    sinv_year = 0
            self.zahlung_mitgliedschaft = sinv_year
            
            if self.bezahltes_mitgliedschaftsjahr < sinv.mitgliedschafts_jahr:
                self.bezahltes_mitgliedschaftsjahr = sinv.mitgliedschafts_jahr
        
        current_year = int(now().split("-")[0])
        if int(self.zahlung_mitgliedschaft) > current_year:
            self.naechstes_jahr_geschuldet = '0'
        else:
            self.naechstes_jahr_geschuldet = 1
        
        
        # Zahldatum = Eintrittsdatum
        if self.status_c in ('Anmeldung', 'Online-Anmeldung', 'Interessent*in') and self.bezahltes_mitgliedschaftsjahr > 0:
            if noch_kein_eintritt:
                self.eintrittsdatum = self.datum_zahlung_mitgliedschaft
        
        if self.bezahltes_mitgliedschaftsjahr > 0 and self.status_c in ('Anmeldung', 'Online-Anmeldung', 'Interessent*in'):
            self.status_c = 'Regulär'
            # erstellung Begrüssungsschreiben
            self.begruessung_massendruck = 1
            self.begruessung_via_zahlung = 1
            druckvorlage = get_druckvorlagen(sektion=self.sektion_id, dokument='Begrüssung mit Ausweis', mitgliedtyp=self.mitgliedtyp_c, language=self.language)['default_druckvorlage']
            self.begruessung_massendruck_dokument = create_korrespondenz(mitgliedschaft=self.name, druckvorlage=druckvorlage, titel='Begrüssung (Autom.)')
            
        
        # prüfe offene Rechnungen bei sektionswechsel
        if self.status_c == 'Wegzug':
            sinvs = frappe.db.sql("""SELECT
                                        `name`
                                    FROM `tabSales Invoice`
                                    WHERE `docstatus` != 2
                                    AND `ist_mitgliedschaftsrechnung` = 1
                                    AND `mv_mitgliedschaft` = '{mvm}'
                                    AND `status` != 'Paid'""".format(mvm=self.name), as_dict=True)
            for sinv in sinvs:
                sinv = frappe.get_doc("Sales Invoice", sinv.name)
                if sinv.docstatus == 1:
                    # cancel linked FR
                    linked_fr = frappe.db.sql("""SELECT `name` FROM `tabFakultative Rechnung` WHERE `sales_invoice` = '{sinv}' AND `docstatus` = 1""".format(sinv=sinv.name), as_dict=True)
                    if len(linked_fr) > 0:
                        for _fr in linked_fr:
                            fr = frappe.get_doc("Fakultative Rechnung", _fr.name)
                            fr.cancel()
                    
                    # cancel linked mahnungen
                    if sinv.payment_reminder_level > 0:
                        linked_mahnungen = frappe.db.sql("""SELECT DISTINCT `parent` FROM `tabMahnung Invoices` WHERE `sales_invoice` = '{sinv}' AND `docstatus` = 1""".format(sinv=sinv.name), as_dict=True)
                        if len(linked_mahnungen) > 0:
                            for _mahnung in linked_mahnungen:
                                mahnung = frappe.get_doc("Mahnung", _mahnung.parent)
                                mahnung.cancel()
                    
                    # reload & cancel sinv
                    sinv = frappe.get_doc("Sales Invoice", sinv.name)
                    sinv.cancel()
                else:
                    if sinv.docstatus == 0:
                        sinv.delete()
        
        return
    
    def check_zahlung_hv(self):
        sinvs = frappe.db.sql("""SELECT
                                    `name`,
                                    `is_pos`,
                                    `posting_date`
                                FROM `tabSales Invoice`
                                WHERE `docstatus` = 1
                                AND `ist_hv_rechnung` = 1
                                AND `mv_mitgliedschaft` = '{mvm}'
                                AND `status` = 'Paid'
                                ORDER BY `posting_date` DESC""".format(mvm=self.name), as_dict=True)
        if len(sinvs) > 0:
            sinv = sinvs[0]
            if sinv.is_pos == 1:
                sinv_year = getdate(sinv.posting_date).strftime("%Y")
                self.datum_hv_zahlung = sinv.posting_date
            else:
                pes = frappe.db.sql("""SELECT `parent` FROM `tabPayment Entry Reference`
                                        WHERE `reference_doctype` = 'Sales Invoice'
                                        AND `reference_name` = '{sinv}' ORDER BY `creation` DESC""".format(sinv=sinv.name), as_dict=True)
                if len(pes) > 0:
                    pe = frappe.get_doc("Payment Entry", pes[0].parent)
                    sinv_year = getdate(pe.reference_date).strftime("%Y")
                    self.datum_hv_zahlung = pe.reference_date
            self.zahlung_hv = sinv_year
        return
        
    def validate_rg_kunde(self):
        if self.rg_kunde:
            update_rg_kunde(self)
            return self.rg_kunde
        else:
            customer = create_rg_kunde(self)
            return customer
    
    def validate_rg_kontakt(self):
        if self.rg_kontakt:
            update_rg_kontakt(self)
            return self.rg_kontakt
        else:
            contact = create_rg_kontakt(self)
            return contact
    
    def validate_rg_adresse(self):
        if self.rg_adresse:
            rg_adresse = update_rg_adresse(self)
            return rg_adresse
        else:
            address = create_rg_adresse(self)
            return address

    def validate_kunde_mitglied(self):
        if self.kunde_mitglied:
            update_kunde_mitglied(self)
            return self.kunde_mitglied
        else:
            customer = create_kunde_mitglied(self)
            return customer
    
    def validate_kontakt_mitglied(self, primary):
        if primary:
            if self.kontakt_mitglied:
                update_kontakt_mitglied(self, primary)
                return self.kontakt_mitglied
            else:
                contact = create_kontakt_mitglied(self, primary)
                return contact
        else:
            if self.kontakt_solidarmitglied:
                update_kontakt_mitglied(self, primary)
                return self.kontakt_solidarmitglied
            else:
                contact = create_kontakt_mitglied(self, primary)
                return contact
    
    def validate_adresse_mitglied(self):
        if self.adresse_mitglied:
            adresse_mitglied = update_adresse_mitglied(self)
            
            if self.postfach == 1 or self.abweichende_objektadresse == 1:
                if self.objekt_adresse:
                    objekt_adresse = update_objekt_adresse(self)
                    return adresse_mitglied, objekt_adresse
                else:
                    objekt_adresse = create_objekt_adresse(self)
                    return adresse_mitglied, objekt_adresse
            else:
                if self.objekt_adresse:
                    self.remove_objekt_adresse()
                return adresse_mitglied, ''
        else:
            address = create_adresse_mitglied(self)
            if self.postfach == 1 or self.abweichende_objektadresse == 1:
                if self.objekt_adresse:
                    objekt_adresse = update_objekt_adresse(self)
                    return address, objekt_adresse
                else:
                    objekt_adresse = create_objekt_adresse(self)
                    return address, objekt_adresse
            else:
                if self.objekt_adresse:
                    self.remove_objekt_adresse()
                return address, ''
    
    def remove_objekt_adresse(self):
        if self.kontakt_solidarmitglied:
            join_mitglied_contact_and_address(self.kontakt_solidarmitglied, '')
        address = frappe.get_doc("Address", self.objekt_adresse)
        address.disabled = 1
        address.links = []
        address.save(ignore_permissions=True)
        return
    
    def remove_solidarmitglied(self):
        contact = frappe.get_doc("Contact", self.kontakt_solidarmitglied)
        contact.links = []
        contact.save(ignore_permissions=True)
        return ''

def mahnstopp(mitgliedschaft, mahnstopp):
    SQL_SAFE_UPDATES_false = frappe.db.sql("""SET SQL_SAFE_UPDATES=0""", as_list=True)
    frappe.db.sql("""UPDATE `tabSales Invoice` SET `exclude_from_payment_reminder_until` = '{mahnstopp}' WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'""".format(mitgliedschaft=mitgliedschaft, mahnstopp=mahnstopp), as_list=True)
    SQL_SAFE_UPDATES_true = frappe.db.sql("""SET SQL_SAFE_UPDATES=1""", as_list=True)
    frappe.db.commit()

def get_adressblock(mitgliedschaft):
    adressblock = ''
    if mitgliedschaft.kundentyp == 'Unternehmen':
        if mitgliedschaft.firma:
            adressblock += mitgliedschaft.firma or ''
            adressblock += ' '
        if mitgliedschaft.zusatz_firma:
            adressblock += mitgliedschaft.zusatz_firma or ''
        if mitgliedschaft.firma or mitgliedschaft.zusatz_firma:
            adressblock += '\n'
    
    if mitgliedschaft.vorname_1:
        adressblock += mitgliedschaft.vorname_1 or ''
        adressblock += ' '
    adressblock += mitgliedschaft.nachname_1 or ''
    adressblock += '\n'
    
    if mitgliedschaft.hat_solidarmitglied:
        if mitgliedschaft.vorname_2:
            adressblock += mitgliedschaft.vorname_2 or ''
            adressblock += ' '
        if mitgliedschaft.nachname_2:
            adressblock += mitgliedschaft.nachname_2 or ''
        if  mitgliedschaft.vorname_2 or mitgliedschaft.nachname_2:
            adressblock += '\n'
    
    if mitgliedschaft.zusatz_adresse:
        adressblock += mitgliedschaft.zusatz_adresse or ''
        adressblock += '\n'
    
    # ~ adressblock += mitgliedschaft.strasse or ''
    if mitgliedschaft.strasse and mitgliedschaft.strasse != '':
        adressblock += mitgliedschaft.strasse
        if mitgliedschaft.nummer:
            adressblock += ' '
            adressblock += str(mitgliedschaft.nummer) or ''
            if mitgliedschaft.nummer_zu:
                adressblock += str(mitgliedschaft.nummer_zu) or ''
        adressblock += '\n'
    
    if int(mitgliedschaft.postfach) == 1:
        adressblock += 'Postfach '
        adressblock += str(mitgliedschaft.postfach_nummer) or ''
        adressblock += '\n'
    
    if mitgliedschaft.land != 'Schweiz':
        laender_code = frappe.get_value("Country", mitgliedschaft.land, "code").upper() + "-"
    else:
        laender_code = ''
    adressblock += laender_code + str(mitgliedschaft.plz) or ''
    adressblock += ' '
    adressblock += mitgliedschaft.ort or ''
    
    return adressblock

def get_rg_adressblock(mitgliedschaft):
    if int(mitgliedschaft.abweichende_rechnungsadresse) != 1:
        return get_adressblock(mitgliedschaft)
    
    adressblock = ''
    
    if int(mitgliedschaft.unabhaengiger_debitor) != 1:
        if mitgliedschaft.kundentyp == 'Unternehmen':
            if mitgliedschaft.firma:
                adressblock += mitgliedschaft.firma or ''
                adressblock += ' '
            if mitgliedschaft.zusatz_firma:
                adressblock += mitgliedschaft.zusatz_firma or ''
            if mitgliedschaft.firma or mitgliedschaft.zusatz_firma:
                adressblock += '\n'
        
        if mitgliedschaft.vorname_1:
            adressblock += mitgliedschaft.vorname_1 or ''
            adressblock += ' '
        adressblock += mitgliedschaft.nachname_1 or ''
        adressblock += '\n'
        
        if mitgliedschaft.hat_solidarmitglied:
            if mitgliedschaft.vorname_2:
                adressblock += mitgliedschaft.vorname_2 or ''
                adressblock += ' '
            if mitgliedschaft.nachname_2:
                adressblock += mitgliedschaft.nachname_2 or ''
            if  mitgliedschaft.vorname_2 or mitgliedschaft.nachname_2:
                adressblock += '\n'
    else:
        if mitgliedschaft.rg_kundentyp == 'Unternehmen':
            if mitgliedschaft.rg_firma:
                adressblock += mitgliedschaft.rg_firma or ''
                adressblock += ' '
            if mitgliedschaft.rg_zusatz_firma:
                adressblock += mitgliedschaft.rg_zusatz_firma or ''
            if mitgliedschaft.rg_firma or mitgliedschaft.rg_zusatz_firma:
                adressblock += '\n'
        
        if mitgliedschaft.rg_vorname:
            adressblock += mitgliedschaft.rg_vorname or ''
            adressblock += ' '
        adressblock += mitgliedschaft.rg_nachname or ''
        adressblock += '\n'
    
    if mitgliedschaft.rg_zusatz_adresse:
        adressblock += mitgliedschaft.rg_zusatz_adresse or ''
        adressblock += '\n'
    
    adressblock += mitgliedschaft.rg_strasse or ''
    if mitgliedschaft.rg_nummer:
        adressblock += ' '
        adressblock += str(mitgliedschaft.rg_nummer) or ''
        if mitgliedschaft.rg_nummer_zu:
            adressblock += str(mitgliedschaft.rg_nummer_zu) or ''
    adressblock += '\n'
    
    if int(mitgliedschaft.rg_postfach) == 1:
        adressblock += 'Postfach '
        adressblock += str(mitgliedschaft.rg_postfach_nummer) or ''
        adressblock += '\n'
    
    if mitgliedschaft.rg_land != 'Schweiz':
        laender_code = frappe.get_value("Country", mitgliedschaft.rg_land, "code").upper() + "-"
    else:
        laender_code = ''
    adressblock += laender_code + str(mitgliedschaft.rg_plz) or ''
    adressblock += ' '
    adressblock += mitgliedschaft.rg_ort or ''
    
    return adressblock
    
def update_rg_adresse(mitgliedschaft):
    address = frappe.get_doc("Address", mitgliedschaft.rg_adresse)
    if mitgliedschaft.rg_postfach == 1:
        strasse = address_line1 = 'Postfach'
        postfach = 1
    else:
        strasse = address_line1 = (" ").join((str(mitgliedschaft.rg_strasse or ''), str(mitgliedschaft.rg_nummer or ''), str(mitgliedschaft.rg_nummer_zu or '')))
        postfach = 0
    
    is_primary_address = 0
    is_shipping_address = 0
    address_title = mitgliedschaft.mitglied_id
    address_line2 = mitgliedschaft.rg_zusatz_adresse
    sektion = mitgliedschaft.sektion_id
    plz = mitgliedschaft.rg_plz
    postfach_nummer = mitgliedschaft.rg_postfach_nummer
    city = mitgliedschaft.rg_ort
    country = mitgliedschaft.rg_land or 'Schweiz'
    
    address.address_title = address_title
    address.address_line1 = address_line1
    address.address_line2 = address_line2
    address.strasse = strasse
    address.sektion = sektion
    address.pincode = plz
    address.plz = plz
    address.postfach = postfach
    address.postfach_nummer = postfach_nummer
    address.city = city
    address.country = country
    address.is_primary_address = is_primary_address
    address.is_shipping_address = is_shipping_address
    address.adress_id = str(mitgliedschaft.mitglied_id) + "-Rechnung"
    address.disabled = 0
    
    if mitgliedschaft.rg_kunde:
        link_name = mitgliedschaft.rg_kunde
    else:
        link_name = mitgliedschaft.kunde_mitglied
    
    address.links = []
    link = address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = link_name
    address.save(ignore_permissions=True)
    
    return address.name

def create_rg_adresse(mitgliedschaft):
    existierende_adresse = existierende_adresse_anhand_id(str(mitgliedschaft.mitglied_id) + "-Rechnung")
    if existierende_adresse:
        mitgliedschaft.rg_adresse = existierende_adresse
        return update_rg_adresse(mitgliedschaft)
    
    if mitgliedschaft.rg_postfach == 1:
        strasse = address_line1 = 'Postfach'
        postfach = 1
    else:
        strasse = address_line1 = (" ").join((str(mitgliedschaft.rg_strasse or ''), str(mitgliedschaft.rg_nummer or ''), str(mitgliedschaft.rg_nummer_zu or '')))
        postfach = 0
    
    is_primary_address = 0
    is_shipping_address = 0
    address_title = mitgliedschaft.mitglied_id
    address_line2 = mitgliedschaft.rg_zusatz_adresse
    sektion = mitgliedschaft.sektion_id
    plz = mitgliedschaft.rg_plz
    postfach_nummer = mitgliedschaft.rg_postfach_nummer
    city = mitgliedschaft.rg_ort
    country = mitgliedschaft.rg_land or 'Schweiz'
    
    new_address = frappe.get_doc({
        'doctype': 'Address',
        'address_title': address_title,
        'address_line1': address_line1,
        'address_line2': address_line2,
        'strasse': strasse,
        'sektion': sektion,
        'pincode': plz,
        'plz': plz,
        'postfach': postfach,
        'postfach_nummer': postfach_nummer,
        'city': city,
        'country': country,
        'is_primary_address': is_primary_address,
        'is_shipping_address': is_shipping_address,
        'adress_id': str(mitgliedschaft.mitglied_id) + "-Rechnung"
    })
    
    if mitgliedschaft.rg_kunde:
        link_name = mitgliedschaft.rg_kunde
    else:
        link_name = mitgliedschaft.kunde_mitglied
    
    link = new_address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = link_name
    
    new_address.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return new_address.name

def update_rg_kontakt(mitgliedschaft):
    contact = frappe.get_doc("Contact", mitgliedschaft.rg_kontakt)
    sektion = mitgliedschaft.sektion_id
    if mitgliedschaft.rg_kunde:
        is_primary_contact = 1
        link_name = mitgliedschaft.rg_kunde
    else:
        is_primary_contact = 0
        link_name = mitgliedschaft.kunde_mitglied
    
    if mitgliedschaft.rg_kundentyp == 'Unternehmen':
        salutation = ''
        company_name = mitgliedschaft.rg_firma
        if not mitgliedschaft.rg_nachname and not mitgliedschaft.rg_vorname:
            first_name = company_name
            last_name = company_name
        else:
            company_name = ''
            salutation = mitgliedschaft.rg_anrede
            first_name = mitgliedschaft.rg_vorname or mitgliedschaft.rg_nachname
            if first_name != mitgliedschaft.rg_nachname:
                last_name = mitgliedschaft.rg_nachname
            else:
                last_name = ''
    else:
        company_name = ''
        salutation = mitgliedschaft.rg_anrede
        first_name = mitgliedschaft.rg_vorname or mitgliedschaft.rg_nachname
        if first_name != mitgliedschaft.rg_nachname:
            last_name = mitgliedschaft.rg_nachname
        else:
            last_name = ''
    contact.first_name = first_name
    contact.last_name = last_name
    contact.salutation = salutation
    contact.sektion = sektion
    contact.company_name = company_name
    contact.is_primary_contact = is_primary_contact
    
    contact.links = []
    link = contact.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = link_name
    
    # email
    contact.email_ids = []
    email_id = mitgliedschaft.rg_e_mail
    if email_id:
        email_row = contact.append("email_ids", {})
        email_row.email_id = email_id
        email_row.is_primary = 1
        
    contact.phone_nos = []
    # private phone
    is_primary_phone = mitgliedschaft.rg_tel_p
    if is_primary_phone:
        is_primary_phone_row = contact.append("phone_nos", {})
        is_primary_phone_row.phone = is_primary_phone
        is_primary_phone_row.is_primary_phone = 1
        
    # mobile phone
    is_primary_mobile_no = mitgliedschaft.rg_tel_m
    if is_primary_mobile_no:
        is_primary_mobile_no_row = contact.append("phone_nos", {})
        is_primary_mobile_no_row.phone = is_primary_mobile_no
        is_primary_mobile_no_row.is_primary_mobile_no = 1
        
    # other (company) phone
    phone = mitgliedschaft.rg_tel_g
    if phone:
        phone_row = contact.append("phone_nos", {})
        phone_row.phone = phone
    
    contact.save(ignore_permissions=True)
    return

def create_rg_kontakt(mitgliedschaft):
    sektion = mitgliedschaft.sektion_id
    if mitgliedschaft.rg_kunde:
        is_primary_contact = 1
        link_name = mitgliedschaft.rg_kunde
    else:
        is_primary_contact = 0
        link_name = mitgliedschaft.kunde_mitglied
    
    if mitgliedschaft.rg_kundentyp == 'Unternehmen':
        salutation = ''
        company_name = mitgliedschaft.rg_firma
        if not mitgliedschaft.rg_nachname and not mitgliedschaft.rg_vorname:
            first_name = company_name
            last_name = mitgliedschaft.rg_nachname or ''
        else:
            company_name = ''
            salutation = mitgliedschaft.rg_anrede
            first_name = mitgliedschaft.rg_vorname or mitgliedschaft.rg_nachname
            if first_name != mitgliedschaft.rg_nachname:
                last_name = mitgliedschaft.rg_nachname
            else:
                last_name = ''
    else:
        company_name = ''
        salutation = mitgliedschaft.rg_anrede
        first_name = mitgliedschaft.rg_vorname or mitgliedschaft.rg_nachname
        if first_name != mitgliedschaft.rg_nachname:
            last_name = mitgliedschaft.rg_nachname
        else:
            last_name = ''
    
    new_contact = frappe.get_doc({
        'doctype': 'Contact',
        'first_name': first_name,
        'last_name': last_name,
        'salutation': salutation,
        'sektion': sektion,
        'company_name': company_name,
        'is_primary_contact': is_primary_contact
    })
    
    link = new_contact.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = link_name
    
    # email
    email_id = mitgliedschaft.rg_e_mail
    if email_id:
        email_row = new_contact.append("email_ids", {})
        email_row.email_id = email_id
        email_row.is_primary = 1
        
    # private phone
    is_primary_phone = mitgliedschaft.rg_tel_p
    if is_primary_phone:
        is_primary_phone_row = new_contact.append("phone_nos", {})
        is_primary_phone_row.phone = is_primary_phone
        is_primary_phone_row.is_primary_phone = 1
        
    # mobile phone
    is_primary_mobile_no = mitgliedschaft.rg_tel_m
    if is_primary_mobile_no:
        is_primary_mobile_no_row = new_contact.append("phone_nos", {})
        is_primary_mobile_no_row.phone = is_primary_mobile_no
        is_primary_mobile_no_row.is_primary_mobile_no = 1
        
    # other (company) phone
    phone = mitgliedschaft.rg_tel_g
    if phone:
        phone_row = new_contact.append("phone_nos", {})
        phone_row.phone = phone
    
    try:
        new_contact.insert(ignore_permissions=True)
        frappe.db.commit()
    except frappe.DuplicateEntryError:
        frappe.local.message_log = []
        mitgliedschaft.rg_kontakt = new_contact.name
        update_rg_kontakt(mitgliedschaft)
        return new_contact.name
    
    return new_contact.name

def update_rg_kunde(mitgliedschaft):
    customer = frappe.get_doc("Customer", mitgliedschaft.rg_kunde)
    if mitgliedschaft.rg_kundentyp == 'Unternehmen':
        customer.customer_name = mitgliedschaft.rg_firma
        customer.customer_addition = mitgliedschaft.rg_zusatz_firma
        customer.customer_type = 'Company'
    else:
        customer.customer_name = (" ").join((mitgliedschaft.rg_vorname or '', mitgliedschaft.rg_nachname or ''))
        customer.customer_addition = ''
        customer.customer_type = 'Individual'
    customer.sektion = mitgliedschaft.sektion_id
    customer.save(ignore_permissions=True)
    return

def create_rg_kunde(mitgliedschaft):
    if mitgliedschaft.rg_kundentyp == 'Unternehmen':
        customer_name = mitgliedschaft.rg_firma
        customer_addition = mitgliedschaft.rg_zusatz_firma
        customer_type = 'Company'
    else:
        customer_name = (" ").join((mitgliedschaft.rg_vorname or '', mitgliedschaft.rg_nachname or ''))
        customer_addition = ''
        customer_type = 'Individual'
    
    new_customer = frappe.get_doc({
        'doctype': 'Customer',
        'customer_name': customer_name,
        'customer_addition': customer_addition,
        'customer_type': customer_type,
        'sektion': mitgliedschaft.sektion_id,
        'customer_group': 'All Customer Groups',
        'territory': 'All Territories'
    })
    new_customer.insert(ignore_permissions=True)
    frappe.db.commit()
    return new_customer.name

def create_objekt_adresse(mitgliedschaft):
    existierende_adresse = existierende_adresse_anhand_id(str(mitgliedschaft.mitglied_id) + "-Objekt")
    if existierende_adresse:
        mitgliedschaft.objekt_adresse = existierende_adresse
        return update_objekt_adresse(mitgliedschaft)
    
    strasse = address_line1 = (" ").join((str(mitgliedschaft.objekt_strasse or ''), str(mitgliedschaft.objekt_hausnummer or ''), str(mitgliedschaft.objekt_nummer_zu or '')))
    postfach = 0
    is_primary_address = 0
    is_shipping_address = 0
    address_title = ("-").join((str(mitgliedschaft.mitglied_id), 'Objekt'))
    address_line2 = mitgliedschaft.objekt_zusatz_adresse
    sektion = mitgliedschaft.sektion_id
    plz = mitgliedschaft.objekt_plz
    postfach_nummer = ''
    city = mitgliedschaft.objekt_ort
    
    if not strasse:
        strasse = address_line1 = "Achtung Fehler!"
    if not city:
        city = "Achtung Fehler!"
    
    new_address = frappe.get_doc({
        'doctype': 'Address',
        'address_title': address_title,
        'address_line1': address_line1,
        'address_line2': address_line2,
        'strasse': strasse,
        'sektion': sektion,
        'pincode': plz,
        'plz': plz,
        'postfach': postfach,
        'postfach_nummer': postfach_nummer,
        'city': city,
        'is_primary_address': is_primary_address,
        'is_shipping_address': is_shipping_address,
        'adress_id': str(mitgliedschaft.mitglied_id) + "-Objekt"
    })
    
    link = new_address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied
    
    new_address.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return new_address.name

def update_objekt_adresse(mitgliedschaft):
    address = frappe.get_doc("Address", mitgliedschaft.objekt_adresse)
    strasse = address_line1 = (" ").join((str(mitgliedschaft.objekt_strasse or ''), str(mitgliedschaft.objekt_hausnummer or ''), str(mitgliedschaft.objekt_nummer_zu or '')))
    postfach = 0
    is_primary_address = 0
    is_shipping_address = 0
    address_title = ("-").join((str(mitgliedschaft.mitglied_id), 'Objekt'))
    address_line2 = mitgliedschaft.objekt_zusatz_adresse
    sektion = mitgliedschaft.sektion_id
    plz = mitgliedschaft.objekt_plz
    postfach_nummer = ''
    city = mitgliedschaft.objekt_ort
    
    if not strasse:
        strasse = address_line1 = "Achtung Fehler!"
    if not city:
        city = "Achtung Fehler!"
    
    address.address_title = address_title
    address.address_line1 = address_line1
    address.address_line2 = address_line2
    address.strasse = strasse
    address.sektion = sektion
    address.pincode = plz
    address.plz = plz
    address.postfach = postfach
    address.postfach_nummer = postfach_nummer
    address.city = city
    address.is_primary_address = is_primary_address
    address.is_shipping_address = is_shipping_address
    address.adress_id = str(mitgliedschaft.mitglied_id) + "-Objekt"
    address.disabled = 0
    
    address.links = []
    link = address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied
    address.save(ignore_permissions=True)
    
    return address.name

def join_mitglied_contact_and_address(contact, address):
    contact = frappe.get_doc("Contact", contact)
    contact.address = address
    contact.save(ignore_permissions=True)
    
def update_adresse_mitglied(mitgliedschaft):
    address = frappe.get_doc("Address", mitgliedschaft.adresse_mitglied)
    if mitgliedschaft.postfach == 1:
        strasse = address_line1 = 'Postfach'
        postfach = 1
    else:
        strasse = address_line1 = (" ").join((str(mitgliedschaft.strasse or ''), str(mitgliedschaft.nummer or ''), str(mitgliedschaft.nummer_zu or '')))
        postfach = 0
    
    is_primary_address = 1
    is_shipping_address = 1
    address_title = mitgliedschaft.mitglied_id
    address_line2 = mitgliedschaft.zusatz_adresse
    sektion = mitgliedschaft.sektion_id
    plz = mitgliedschaft.plz
    postfach_nummer = mitgliedschaft.postfach_nummer
    city = mitgliedschaft.ort
    country = mitgliedschaft.land or 'Schweiz'
    
    address.address_title = address_title
    address.address_line1 = address_line1
    address.address_line2 = address_line2
    address.strasse = strasse
    address.sektion = sektion
    address.pincode = plz
    address.plz = plz
    address.postfach = postfach
    address.postfach_nummer = postfach_nummer
    address.city = city
    address.country = country
    address.is_primary_address = is_primary_address
    address.is_shipping_address = is_shipping_address
    address.adress_id = str(mitgliedschaft.mitglied_id) + "-Mitglied"
    
    address.links = []
    link = address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied
    address.save(ignore_permissions=True)
    
    return address.name

def create_adresse_mitglied(mitgliedschaft):
    existierende_adresse = existierende_adresse_anhand_id(str(mitgliedschaft.mitglied_id) + "-Mitglied")
    if existierende_adresse:
        mitgliedschaft.adresse_mitglied = existierende_adresse
        return update_adresse_mitglied(mitgliedschaft)
    
    if mitgliedschaft.postfach == 1:
        strasse = address_line1 = 'Postfach'
        postfach = 1
    else:
        strasse = address_line1 = (" ").join((str(mitgliedschaft.strasse or ''), str(mitgliedschaft.nummer or ''), str(mitgliedschaft.nummer_zu or '')))
        postfach = 0
    
    is_primary_address = 1
    is_shipping_address = 1
    address_title = mitgliedschaft.mitglied_id
    address_line2 = mitgliedschaft.zusatz_adresse
    sektion = mitgliedschaft.sektion_id
    plz = mitgliedschaft.plz
    postfach_nummer = mitgliedschaft.postfach_nummer
    city = mitgliedschaft.ort
    country = mitgliedschaft.land or 'Schweiz'
    
    new_address = frappe.get_doc({
        'doctype': 'Address',
        'address_title': address_title,
        'address_line1': address_line1,
        'address_line2': address_line2,
        'strasse': strasse,
        'sektion': sektion,
        'pincode': plz,
        'plz': plz,
        'postfach': postfach,
        'postfach_nummer': postfach_nummer,
        'city': city,
        'country': country,
        'is_primary_address': is_primary_address,
        'is_shipping_address': is_shipping_address,
        'adress_id': str(mitgliedschaft.mitglied_id) + "-Mitglied"
    })
    
    link = new_address.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied
    
    new_address.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return new_address.name

def remove_solidarmitglied(mitgliedschaft):
    return

def update_kontakt_mitglied(mitgliedschaft, primary=True):
    if primary:
        contact = frappe.get_doc("Contact", mitgliedschaft.kontakt_mitglied)
        sektion = mitgliedschaft.sektion_id
        is_primary_contact = 1
        if mitgliedschaft.kundentyp == 'Unternehmen':
            salutation = ''
            company_name = mitgliedschaft.firma
            if not mitgliedschaft.nachname_1 and not mitgliedschaft.vorname_1:
                first_name = company_name
                last_name = ''
            else:
                company_name = ''
                salutation = mitgliedschaft.anrede_c
                first_name = mitgliedschaft.vorname_1 or mitgliedschaft.nachname_1
                if first_name != mitgliedschaft.nachname_1:
                    last_name = mitgliedschaft.nachname_1
                else:
                    last_name = ''
        else:
            company_name = ''
            salutation = mitgliedschaft.anrede_c
            first_name = mitgliedschaft.vorname_1 or mitgliedschaft.nachname_1
            if first_name != mitgliedschaft.nachname_1:
                last_name = mitgliedschaft.nachname_1
            else:
                last_name = ''
    else:
        contact = frappe.get_doc("Contact", mitgliedschaft.kontakt_solidarmitglied)
        sektion = mitgliedschaft.sektion_id
        is_primary_contact = 0
        company_name = ''
        salutation = mitgliedschaft.anrede_2
        first_name = mitgliedschaft.vorname_2 or mitgliedschaft.nachname_2
        if first_name != mitgliedschaft.nachname_2:
            last_name = mitgliedschaft.nachname_2
        else:
            last_name = ''
    
    # company fallback
    if not first_name:
        if mitgliedschaft.firma and not mitgliedschaft.nachname_1 and not mitgliedschaft.vorname_1:
            first_name = mitgliedschaft.firma
    
    contact.first_name = first_name
    contact.last_name = last_name
    contact.salutation = salutation
    contact.sektion = sektion
    contact.company_name = company_name
    contact.is_primary_contact = is_primary_contact
    
    contact.links = []
    link = contact.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied
    
    if primary:
        # email
        contact.email_ids = []
        email_id = mitgliedschaft.e_mail_1
        if email_id:
            email_row = contact.append("email_ids", {})
            email_row.email_id = email_id
            email_row.is_primary = 1
            
        contact.phone_nos = []
        contact.phone = ''
        contact.mobile_no = ''
        # private phone
        is_primary_phone = mitgliedschaft.tel_p_1
        if is_primary_phone:
            is_primary_phone_row = contact.append("phone_nos", {})
            is_primary_phone_row.phone = is_primary_phone
            is_primary_phone_row.is_primary_phone = 1
            
        # mobile phone
        is_primary_mobile_no = mitgliedschaft.tel_m_1
        if is_primary_mobile_no:
            is_primary_mobile_no_row = contact.append("phone_nos", {})
            is_primary_mobile_no_row.phone = is_primary_mobile_no
            is_primary_mobile_no_row.is_primary_mobile_no = 1
            
        # other (company) phone
        phone = mitgliedschaft.tel_g_1
        if phone:
            phone_row = contact.append("phone_nos", {})
            phone_row.phone = phone
    else:
        # email
        contact.email_ids = []
        email_id = mitgliedschaft.e_mail_2
        if email_id:
            email_row = contact.append("email_ids", {})
            email_row.email_id = email_id
            email_row.is_primary = 1
            
        contact.phone_nos = []
        contact.phone = ''
        contact.mobile_no = ''
        # private phone
        is_primary_phone = mitgliedschaft.tel_p_2
        if is_primary_phone:
            is_primary_phone_row = contact.append("phone_nos", {})
            is_primary_phone_row.phone = is_primary_phone
            is_primary_phone_row.is_primary_phone = 1
            
        # mobile phone
        is_primary_mobile_no = mitgliedschaft.tel_m_2
        if is_primary_mobile_no:
            is_primary_mobile_no_row = contact.append("phone_nos", {})
            is_primary_mobile_no_row.phone = is_primary_mobile_no
            is_primary_mobile_no_row.is_primary_mobile_no = 1
            
        # other (company) phone
        phone = mitgliedschaft.tel_g_2
        if phone:
            phone_row = contact.append("phone_nos", {})
            phone_row.phone = phone
    
    contact.save(ignore_permissions=True)
    return

def create_kontakt_mitglied(mitgliedschaft, primary=True):
    if primary:
        sektion = mitgliedschaft.sektion_id
        is_primary_contact = 1
        if mitgliedschaft.kundentyp == 'Unternehmen':
            salutation = ''
            company_name = mitgliedschaft.firma
            if not mitgliedschaft.nachname_1 and not mitgliedschaft.vorname_1:
                first_name = company_name
                last_name = ''
            else:
                company_name = ''
                salutation = mitgliedschaft.anrede_c
                first_name = mitgliedschaft.vorname_1 or mitgliedschaft.nachname_1
                if first_name != mitgliedschaft.nachname_1:
                    last_name = mitgliedschaft.nachname_1
                else:
                    last_name = ''
        else:
            company_name = ''
            salutation = mitgliedschaft.anrede_c
            first_name = mitgliedschaft.vorname_1 or mitgliedschaft.nachname_1
            if first_name != mitgliedschaft.nachname_1:
                last_name = mitgliedschaft.nachname_1
            else:
                last_name = ''
    else:
        if not  mitgliedschaft.nachname_2 and not mitgliedschaft.vorname_2:
            # Weder Vor- noch Nachname, Anlage Solidarmitglied abgebrochen
            return ''
        
        sektion = mitgliedschaft.sektion_id
        is_primary_contact = 0
        company_name = ''
        salutation = mitgliedschaft.anrede_2
        first_name = mitgliedschaft.vorname_2 or mitgliedschaft.nachname_2
        if first_name != mitgliedschaft.nachname_2:
            last_name = mitgliedschaft.nachname_2
        else:
            last_name = ''
    
    # company fallback
    if not first_name:
        if mitgliedschaft.firma and not mitgliedschaft.nachname_1 and not mitgliedschaft.vorname_1:
            first_name = mitgliedschaft.firma
            frappe.log_error("{0}\n---\n{1}".format('fallback: first_name was " "', mitgliedschaft.as_json()), 'create_kontakt_mitglied')
    
    new_contact = frappe.get_doc({
        'doctype': 'Contact',
        'first_name': first_name,
        'last_name': last_name,
        'salutation': salutation,
        'sektion': sektion,
        'company_name': company_name,
        'is_primary_contact': is_primary_contact
    })
    
    link = new_contact.append("links", {})
    link.link_doctype = 'Customer'
    link.link_name = mitgliedschaft.kunde_mitglied
    
    if primary:
        # email
        email_id = mitgliedschaft.e_mail_1
        if email_id:
            email_row = new_contact.append("email_ids", {})
            email_row.email_id = email_id
            email_row.is_primary = 1
            
        # private phone
        is_primary_phone = mitgliedschaft.tel_p_1
        if is_primary_phone:
            is_primary_phone_row = new_contact.append("phone_nos", {})
            is_primary_phone_row.phone = is_primary_phone
            is_primary_phone_row.is_primary_phone = 1
            
        # mobile phone
        is_primary_mobile_no = mitgliedschaft.tel_m_1
        if is_primary_mobile_no:
            is_primary_mobile_no_row = new_contact.append("phone_nos", {})
            is_primary_mobile_no_row.phone = is_primary_mobile_no
            is_primary_mobile_no_row.is_primary_mobile_no = 1
            
        # other (company) phone
        phone = mitgliedschaft.tel_g_1
        if phone:
            phone_row = new_contact.append("phone_nos", {})
            phone_row.phone = phone
    else:
        # email
        email_id = mitgliedschaft.e_mail_2
        if email_id:
            email_row = new_contact.append("email_ids", {})
            email_row.email_id = email_id
            email_row.is_primary = 1
            
        # private phone
        is_primary_phone = mitgliedschaft.tel_p_2
        if is_primary_phone:
            is_primary_phone_row = new_contact.append("phone_nos", {})
            is_primary_phone_row.phone = is_primary_phone
            is_primary_phone_row.is_primary_phone = 1
            
        # mobile phone
        is_primary_mobile_no = mitgliedschaft.tel_m_2
        if is_primary_mobile_no:
            is_primary_mobile_no_row = new_contact.append("phone_nos", {})
            is_primary_mobile_no_row.phone = is_primary_mobile_no
            is_primary_mobile_no_row.is_primary_mobile_no = 1
            
        # other (company) phone
        phone = mitgliedschaft.tel_g_2
        if phone:
            phone_row = new_contact.append("phone_nos", {})
            phone_row.phone = phone
    
    try:
        new_contact.insert(ignore_permissions=True)
        frappe.db.commit()
    except frappe.DuplicateEntryError:
        frappe.local.message_log = []
        mitgliedschaft.kontakt_solidarmitglied = new_contact.name
        update_kontakt_mitglied(mitgliedschaft, primary)
        return new_contact.name
    
    return new_contact.name

def update_kunde_mitglied(mitgliedschaft):
    customer = frappe.get_doc("Customer", mitgliedschaft.kunde_mitglied)
    if mitgliedschaft.kundentyp == 'Unternehmen':
        customer.customer_name = mitgliedschaft.firma
        customer.customer_addition = mitgliedschaft.zusatz_firma
        customer.customer_type = 'Company'
    else:
        if mitgliedschaft.vorname_1:
            customer.customer_name = (" ").join((mitgliedschaft.vorname_1, mitgliedschaft.nachname_1))
        else:
            customer.customer_name = mitgliedschaft.nachname_1
        customer.customer_addition = ''
        customer.customer_type = 'Individual'
    customer.sektion = mitgliedschaft.sektion_id
    
    # fallback wrong import data
    if customer.customer_name == ' ' and mitgliedschaft.firma:
        customer.customer_name = mitgliedschaft.firma
        customer.customer_addition = mitgliedschaft.zusatz_firma
        customer.customer_type = 'Company'
        frappe.log_error("{0}\n---\n{1}".format('fallback: customer_name was " "', mitgliedschaft.as_json()), 'update_kunde_mitglied')
    
    customer.save(ignore_permissions=True)
    return
    
def create_kunde_mitglied(mitgliedschaft):
    if mitgliedschaft.kundentyp == 'Unternehmen':
        customer_name = mitgliedschaft.firma
        customer_addition = mitgliedschaft.zusatz_firma
        customer_type = 'Company'
    else:
        if mitgliedschaft.vorname_1:
            customer_name = (" ").join((mitgliedschaft.vorname_1, mitgliedschaft.nachname_1))
        else:
            customer_name = mitgliedschaft.nachname_1
        customer_addition = ''
        customer_type = 'Individual'
        
    # fallback wrong import data
    if customer_name == ' ' and mitgliedschaft.firma:
        customer_name = mitgliedschaft.firma
        customer_addition = mitgliedschaft.zusatz_firma
        customer_type = 'Company'
        frappe.log_error("{0}\n---\n{1}".format('fallback: customer_name was " "', mitgliedschaft.as_json()), 'create_kunde_mitglied')
    
    new_customer = frappe.get_doc({
        'doctype': 'Customer',
        'customer_name': customer_name,
        'customer_addition': customer_addition,
        'customer_type': customer_type,
        'sektion': mitgliedschaft.sektion_id,
        'customer_group': 'All Customer Groups',
        'territory': 'All Territories'
    })
    
    new_customer.insert(ignore_permissions=True)
    frappe.db.commit()
    return new_customer.name

def existierende_adresse_anhand_id(adress_id):
    address = False
    adress_lookup = frappe.db.sql("""SELECT `name` FROM `tabAddress` WHERE `adress_id` = '{adress_id}' LIMIT 1""".format(adress_id=adress_id), as_dict=True)
    if len(adress_lookup) > 0:
        address = adress_lookup[0].name
    return address

@frappe.whitelist()
def get_timeline_data(doctype, name):
    '''returns timeline data for the past one year'''
    from frappe.desk.form.load import get_communication_data
    from frappe.utils import add_years, now, add_days, getdate, get_timestamp

    
    out = {}
    fields = 'DATE(`creation`) AS `date`, COUNT(`name`) AS `qty`'
    after = add_years(None, -1).strftime('%Y-%m-%d')
    group_by='GROUP BY DATE(`creation`)'

    # fetch and append data from Version Log
    timeline_items = frappe.db.sql("""SELECT {fields}
        FROM `tabVersion`
        WHERE `ref_doctype` = "{doctype}" AND `docname` = "{name}"
        AND `creation` > '{after}'
        {group_by} ORDER BY `creation` DESC
        """.format(doctype=doctype, name=name, fields=fields,
            group_by=group_by, after=after), as_dict=True)

    for timeline_item in timeline_items:
        timestamp = get_timestamp(timeline_item.date)
        out.update({ timestamp: timeline_item.qty })
    return out

@frappe.whitelist()
def get_uebersicht_html(name):
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", name)
    
    if not mitgliedschaft.validierung_notwendig:
        # vaidiertes mitglied
        col_qty = 1
        
        kunde_mitglied = False
        if mitgliedschaft.kunde_mitglied:
            kunde_mitglied = frappe.get_doc("Customer", mitgliedschaft.kunde_mitglied).as_dict()
        
        kontakt_mitglied = False
        if mitgliedschaft.kontakt_mitglied:
            kontakt_mitglied = frappe.get_doc("Contact", mitgliedschaft.kontakt_mitglied).as_dict()
        
        adresse_mitglied = False
        if mitgliedschaft.adresse_mitglied:
            adresse_mitglied = frappe.get_doc("Address", mitgliedschaft.adresse_mitglied).as_dict()
        
        objekt_adresse = False
        if mitgliedschaft.objekt_adresse:
            objekt_adresse = frappe.get_doc("Address", mitgliedschaft.objekt_adresse).as_dict()
            col_qty += 1
        
        kontakt_solidarmitglied = False
        if mitgliedschaft.kontakt_solidarmitglied:
            kontakt_solidarmitglied = frappe.get_doc("Contact", mitgliedschaft.kontakt_solidarmitglied).as_dict()
            col_qty += 1
        
        rg_kunde = False
        if mitgliedschaft.rg_kunde:
            rg_kunde = frappe.get_doc("Customer", mitgliedschaft.rg_kunde).as_dict()
        
        rg_kontakt = False
        if mitgliedschaft.rg_kontakt:
            rg_kontakt = frappe.get_doc("Contact", mitgliedschaft.rg_kontakt).as_dict()
        
        rg_adresse = False
        if mitgliedschaft.rg_adresse:
            rg_adresse = frappe.get_doc("Address", mitgliedschaft.rg_adresse).as_dict()
        
        rg_sep = False
        if mitgliedschaft.abweichende_rechnungsadresse:
            rg_sep = True
            col_qty += 1
        
        rechnungs_kunde = mitgliedschaft.kunde_mitglied
        ueberfaellige_rechnungen = 0
        offene_rechnungen = 0
        
        sektion = frappe.get_doc("Sektion", mitgliedschaft.sektion_id)
        karenzfrist_in_d = sektion.karenzfrist
        ablauf_karenzfrist = add_days(getdate(mitgliedschaft.eintrittsdatum), karenzfrist_in_d)
        if getdate() < ablauf_karenzfrist:
            karenzfrist = False
        else:
            karenzfrist = True
            
        if mitgliedschaft.zuzug:
            zuzug = mitgliedschaft.zuzug
            zuzug_von = mitgliedschaft.zuzug_von
        else:
            zuzug = False
            zuzug_von = False
            
        if mitgliedschaft.wegzug:
            wegzug = mitgliedschaft.wegzug
            wegzug_zu = mitgliedschaft.wegzug_zu
        else:
            wegzug = False
            wegzug_zu = False
        
        if mitgliedschaft.kuendigung:
            kuendigung = mitgliedschaft.kuendigung
        else:
            kuendigung = False
        
        if mitgliedschaft.mitgliedtyp_c == 'Privat':
            if mitgliedschaft.zahlung_hv:
                # im moment umgeschrieben von Datum auf Jahreszahl, muss nach dem Update der API wieder angepasst werden!
                # hv_status = 'HV bezahlt am {0}'.format(frappe.utils.get_datetime(mitgliedschaft.zahlung_hv).strftime('%d.%m.%Y'))
                hv_status = 'HV bezahlt im {0}'.format(mitgliedschaft.zahlung_hv)
                if mitgliedschaft.datum_hv_zahlung:
                    hv_status = 'HV bezahlt am {0}'.format(frappe.utils.get_datetime(mitgliedschaft.datum_hv_zahlung).strftime('%d.%m.%Y'))
            else:
                hv_status = 'HV unbezahlt'
        else:
            hv_status = False
        
        if mitgliedschaft.rg_kunde:
            rechnungs_kunde = mitgliedschaft.rg_kunde
        
        ueberfaellige_rechnungen = frappe.db.sql("""SELECT IFNULL(SUM(`outstanding_amount`), 0) AS `open_amount`
                                                    FROM `tabSales Invoice` 
                                                    WHERE `customer` = '{rechnungs_kunde}'
                                                    AND `due_date` < CURDATE()
                                                    AND `docstatus` = 1""".format(rechnungs_kunde=rechnungs_kunde), as_dict=True)[0].open_amount
        
        offene_rechnungen = frappe.db.sql("""SELECT IFNULL(SUM(`outstanding_amount`), 0) AS `open_amount`
                                            FROM `tabSales Invoice` 
                                            WHERE `customer` = '{rechnungs_kunde}'
                                            AND `due_date` >= CURDATE()
                                            AND `docstatus` = 1""".format(rechnungs_kunde=rechnungs_kunde), as_dict=True)[0].open_amount
        
        data = {
            'kunde_mitglied': kunde_mitglied,
            'kontakt_mitglied': kontakt_mitglied,
            'adresse_mitglied': adresse_mitglied,
            'objekt_adresse': objekt_adresse,
            'kontakt_solidarmitglied': kontakt_solidarmitglied,
            'rg_kunde': rg_kunde,
            'rg_kontakt': rg_kontakt,
            'rg_adresse': rg_adresse,
            'rg_sep': rg_sep,
            'col_qty': int(12 / col_qty),
            'allgemein': {
                'status': mitgliedschaft.status_c,
                'eintritt': mitgliedschaft.eintrittsdatum,
                'austritt': mitgliedschaft.austritt,
                'ampelfarbe': mitgliedschaft.ampel_farbe or 'ampelrot',
                'ueberfaellige_rechnungen': ueberfaellige_rechnungen,
                'offene_rechnungen': offene_rechnungen,
                'ablauf_karenzfrist': ablauf_karenzfrist,
                'zuzug': zuzug,
                'wegzug': wegzug,
                'zuzug_von': zuzug_von,
                'wegzug_zu': wegzug_zu,
                'mitgliedtyp_c': mitgliedschaft.mitgliedtyp_c,
                'hv_status': hv_status,
                'wichtig': mitgliedschaft.wichtig,
                'kuendigung': kuendigung,
                'validierung': int(mitgliedschaft.validierung_notwendig),
                'tel_g_1': mitgliedschaft.tel_g_1 or '',
                'tel_g_2': mitgliedschaft.tel_g_2 or '',
                'rg_tel_g': mitgliedschaft.rg_tel_g or '',
                'language': mitgliedschaft.language or 'de',
                'sektion': mitgliedschaft.sektion_id
            }
        }
        
        return frappe.render_template('templates/includes/mitgliedschaft_overview.html', data)
    else:
        # unvaidiertes mitglied
        col_qty = 1
        allgemein = False
        mitglied = False
        solidarmitglied = False
        korrespondenzadresse = False
        objektadresse = False
        rechnungsempfaenger = False
        rechnungsadresse = False
        
        allgemein = {
            'status': mitgliedschaft.status_c,
            'mitgliedtyp': mitgliedschaft.mitgliedtyp_c,
            'eintritt': mitgliedschaft.eintrittsdatum,
            'kuendigung': mitgliedschaft.kuendigung or False,
            'language': mitgliedschaft.language or 'de',
            'sektion': mitgliedschaft.sektion_id
        }
        
        # Hauptmitglied
        if mitgliedschaft.kundentyp == 'Einzelperson':
            mitglied = {
                'firma': False,
                'zusatz_firma': False,
                'anrede': mitgliedschaft.anrede_c if mitgliedschaft.anrede_c else False,
                'vorname': mitgliedschaft.vorname_1 if mitgliedschaft.vorname_1 else False,
                'nachname': mitgliedschaft.nachname_1,
                'tel_p': mitgliedschaft.tel_p_1 if mitgliedschaft.tel_p_1 else False,
                'tel_m': mitgliedschaft.tel_m_1 if mitgliedschaft.tel_m_1 else False,
                'tel_g': mitgliedschaft.tel_g_1 if mitgliedschaft.tel_g_1 else False,
                'mail': mitgliedschaft.e_mail_1 if mitgliedschaft.e_mail_1 else False
            }
        else:
            mitglied = {
                'firma': mitgliedschaft.firma,
                'zusatz_firma': mitgliedschaft.zusatz_firma if mitgliedschaft.zusatz_firma else False,
                'anrede': mitgliedschaft.anrede_c if mitgliedschaft.anrede_c else False,
                'vorname': mitgliedschaft.vorname_1 if mitgliedschaft.vorname_1 else False,
                'nachname': mitgliedschaft.nachname_1,
                'tel_p': mitgliedschaft.tel_p_1 if mitgliedschaft.tel_p_1 else False,
                'tel_m': mitgliedschaft.tel_m_1 if mitgliedschaft.tel_m_1 else False,
                'tel_g': mitgliedschaft.tel_g_1 if mitgliedschaft.tel_g_1 else False,
                'mail': mitgliedschaft.e_mail_1 if mitgliedschaft.e_mail_1 else False
            }
        
        # Solidarmitglied
        if int(mitgliedschaft.hat_solidarmitglied) == 1:
            solidarmitglied = {
                'anrede': mitgliedschaft.anrede_2 if mitgliedschaft.anrede_2 else False,
                'nachname': mitgliedschaft.nachname_2,
                'vorname': mitgliedschaft.vorname_2 if mitgliedschaft.vorname_2 else False,
                'tel_p': mitgliedschaft.tel_p_2 if mitgliedschaft.tel_p_2 else False,
                'tel_m': mitgliedschaft.tel_m_2 if mitgliedschaft.tel_m_2 else False,
                'tel_g': mitgliedschaft.tel_g_2 if mitgliedschaft.tel_g_2 else False,
                'mail': mitgliedschaft.e_mail_2 if mitgliedschaft.e_mail_2 else False
            }
            col_qty += 1
        
        # Korrespondenzadresse
        korrespondenzadresse = {
            'zusatz': mitgliedschaft.zusatz_adresse if mitgliedschaft.zusatz_adresse else False,
            'strasse': mitgliedschaft.strasse if mitgliedschaft.strasse else False,
            'nummer': mitgliedschaft.nummer if mitgliedschaft.nummer else False,
            'nummer_zu': mitgliedschaft.nummer_zu if mitgliedschaft.nummer_zu else False,
            'postfach': 1 if int(mitgliedschaft.postfach) == 1 else 0,
            'postfach_nummer': mitgliedschaft.postfach_nummer if mitgliedschaft.postfach_nummer else False,
            'plz': mitgliedschaft.plz,
            'ort': mitgliedschaft.ort
        }
        
        # Objektadresse
        if int(mitgliedschaft.abweichende_objektadresse) == 1:
            objektadresse = {
                'zusatz': mitgliedschaft.objekt_zusatz_adresse if mitgliedschaft.objekt_zusatz_adresse else False,
                'strasse': mitgliedschaft.objekt_strasse if mitgliedschaft.objekt_strasse else False,
                'nummer': mitgliedschaft.objekt_hausnummer if mitgliedschaft.objekt_hausnummer else False,
                'nummer_zu': mitgliedschaft.objekt_nummer_zu if mitgliedschaft.objekt_nummer_zu else False,
                'plz': mitgliedschaft.objekt_plz,
                'ort': mitgliedschaft.objekt_ort
            }
        else:
            objektadresse = korrespondenzadresse
        col_qty += 1
        
        # Rechnungsadresse
        if int(mitgliedschaft.abweichende_rechnungsadresse) == 1:
            rechnungsadresse = {
                'zusatz': mitgliedschaft.rg_zusatz_adresse if mitgliedschaft.rg_zusatz_adresse else False,
                'strasse': mitgliedschaft.rg_strasse if mitgliedschaft.rg_strasse else False,
                'nummer': mitgliedschaft.rg_nummer if mitgliedschaft.rg_nummer else False,
                'nummer_zu': mitgliedschaft.rg_nummer_zu if mitgliedschaft.rg_nummer_zu else False,
                'postfach': 1 if int(mitgliedschaft.rg_postfach) == 1 else 0,
                'postfach_nummer': mitgliedschaft.rg_postfach_nummer if mitgliedschaft.rg_postfach_nummer else False,
                'plz': mitgliedschaft.rg_plz,
                'ort': mitgliedschaft.rg_ort
            }
            col_qty += 1
        
        # Rechnungsempfänger
        if int(mitgliedschaft.unabhaengiger_debitor) == 1:
            if mitgliedschaft.rg_kundentyp == 'Einzelperson':
                rechnungsempfaenger = {
                    'firma': False,
                    'zusatz_firma': False,
                    'anrede': mitgliedschaft.rg_anrede if mitgliedschaft.rg_anrede else False,
                    'vorname': mitgliedschaft.rg_vorname if mitgliedschaft.rg_vorname else False,
                    'nachname': mitgliedschaft.rg_nachname,
                    'tel_p': mitgliedschaft.rg_tel_p if mitgliedschaft.rg_tel_p else False,
                    'tel_m': mitgliedschaft.rg_tel_m if mitgliedschaft.rg_tel_m else False,
                    'tel_g': mitgliedschaft.rg_tel_g if mitgliedschaft.rg_tel_g else False,
                    'mail': mitgliedschaft.rg_e_mail if mitgliedschaft.rg_e_mail else False
                }
            else:
                rechnungsempfaenger = {
                    'firma': mitgliedschaft.rg_firma if mitgliedschaft.rg_firma else False,
                    'zusatz_firma': mitgliedschaft.rg_zusatz_firma if mitgliedschaft.rg_zusatz_firma else False,
                    'anrede': mitgliedschaft.rg_anrede if mitgliedschaft.rg_anrede else False,
                    'vorname': mitgliedschaft.rg_vorname if mitgliedschaft.rg_vorname else False,
                    'nachname': mitgliedschaft.rg_nachname,
                    'tel_p': mitgliedschaft.rg_tel_p if mitgliedschaft.rg_tel_p else False,
                    'tel_m': mitgliedschaft.rg_tel_m if mitgliedschaft.rg_tel_m else False,
                    'tel_g': mitgliedschaft.rg_tel_g if mitgliedschaft.rg_tel_g else False,
                    'mail': mitgliedschaft.rg_e_mail if mitgliedschaft.rg_e_mail else False
                }
        
        data = {
            'col_qty': int(12 / col_qty),
            'allgemein': allgemein,
            'mitglied': mitglied,
            'solidarmitglied': solidarmitglied,
            'korrespondenzadresse': korrespondenzadresse,
            'objektadresse': objektadresse,
            'rechnungsempfaenger': rechnungsempfaenger,
            'rechnungsadresse': rechnungsadresse
        }
        
        return frappe.render_template('templates/includes/mitgliedschaft_overview_unvalidiert.html', data)
    
def get_anredekonvention(mitgliedschaft=None, self=None, rg=False):
    if self:
        mitgliedschaft = self
    else:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    if mitgliedschaft.hat_solidarmitglied and not rg:
        # mit Solidarmitglied
        if mitgliedschaft.anrede_c not in ('Herr', 'Frau') and mitgliedschaft.anrede_2 not in ('Herr', 'Frau'):
            # enthält neutrale Anrede
            if mitgliedschaft.nachname_1 == mitgliedschaft.nachname_2 and mitgliedschaft.vorname_1 == mitgliedschaft.vorname_2:
                # gleiche Namen Fallback
                return 'Guten Tag'
            else:
                return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
        else:
            if mitgliedschaft.anrede_c == mitgliedschaft.anrede_2:
                # selbes Geschlecht
                if mitgliedschaft.nachname_1 == mitgliedschaft.nachname_2:
                    # gleiche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return 'Sehr geehrter Herr {vorname_1} {nachname_1}, sehr geehrter Herr {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return 'Sehr geehrte Frau {vorname_1} {nachname_1}, sehr geehrte Frau {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                else:
                    # unterschiedliche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return 'Sehr geehrter Herr {nachname_1}, sehr geehrter Herr {nachname_2}'.format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return 'Sehr geehrte Frau {nachname_1}, sehr geehrte Frau {nachname_2}'.format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
            else:
                # unterschiedliches Geschlecht
                if mitgliedschaft.nachname_1 == mitgliedschaft.nachname_2:
                    # gleiche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return 'Sehr geehrte Herr und Frau {nachname_1}'.format(nachname_1=mitgliedschaft.nachname_1)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return 'Sehr geehrte Frau und Herr {nachname_1}'.format(nachname_1=mitgliedschaft.nachname_1)
                    else:
                        # Fallback
                        return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                else:
                    # unterschiedliche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return 'Sehr geehrter Herr {nachname_1}, sehr geehrte Frau {nachname_2}'.format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return 'Sehr geehrte Frau {nachname_1}, sehr geehrter Herr {nachname_2}'.format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return 'Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}'.format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
        
    else:
        if not rg:
            # ohne Solidarmitglied
            if mitgliedschaft.anrede_c == 'Herr':
                return 'Sehr geehrter Herr {nachname}'.format(nachname=mitgliedschaft.nachname_1)
            elif mitgliedschaft.anrede_c == 'Frau':
                return 'Sehr geehrte Frau {nachname}'.format(nachname=mitgliedschaft.nachname_1)
            else:
                return 'Guten Tag {vorname} {nachname}'.format(vorname=mitgliedschaft.vorname_1 or '', nachname=mitgliedschaft.nachname_1)
        else:
            if int(mitgliedschaft.unabhaengiger_debitor) == 1:
                # Rechnungs Anrede
                if mitgliedschaft.rg_anrede == 'Herr':
                    return 'Sehr geehrter Herr {nachname}'.format(nachname=mitgliedschaft.rg_nachname)
                elif mitgliedschaft.rg_anrede == 'Frau':
                    return 'Sehr geehrte Frau {nachname}'.format(nachname=mitgliedschaft.rg_nachname)
                else:
                    return 'Guten Tag {vorname} {nachname}'.format(vorname=mitgliedschaft.rg_vorname or '', nachname=mitgliedschaft.rg_nachname)
            else:
                return get_anredekonvention(self=mitgliedschaft)

@frappe.whitelist()
def sektionswechsel(mitgliedschaft, neue_sektion, zuzug_per):
    if str(get_sektion_code(neue_sektion)) not in ('ZH', 'SO'):
        try:
            # erstelle Mitgliedschaft in Zuzugs-Sektion
            mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
            new_mitgliedschaft = frappe.copy_doc(mitgliedschaft)
            new_mitgliedschaft.mitglied_id = ''
            new_mitgliedschaft.zuzug_von = new_mitgliedschaft.sektion_id
            new_mitgliedschaft.sektion_id = neue_sektion
            new_mitgliedschaft.status_c = 'Zuzug'
            new_mitgliedschaft.zuzug = zuzug_per
            new_mitgliedschaft.wegzug = ''
            new_mitgliedschaft.kunde_mitglied = ''
            new_mitgliedschaft.kontakt_mitglied = ''
            new_mitgliedschaft.adresse_mitglied = ''
            new_mitgliedschaft.adress_id_mitglied = ''
            new_mitgliedschaft.kontakt_solidarmitglied = ''
            new_mitgliedschaft.objekt_adresse = ''
            new_mitgliedschaft.adress_id_objekt = ''
            new_mitgliedschaft.rg_kunde = ''
            new_mitgliedschaft.rg_kontakt = ''
            new_mitgliedschaft.rg_adresse = ''
            new_mitgliedschaft.online_haftpflicht = 0
            new_mitgliedschaft.online_gutschrift = None
            new_mitgliedschaft.online_betrag = None
            new_mitgliedschaft.datum_online_verbucht = None
            new_mitgliedschaft.datum_online_gutschrift = None
            new_mitgliedschaft.online_payment_method = None
            new_mitgliedschaft.online_payment_id = None
            new_mitgliedschaft.adress_id_rg = ''
            new_mitgliedschaft.validierung_notwendig = 0
            new_mitgliedschaft.letzte_bearbeitung_von = 'SP'
            new_mitgliedschaft.insert(ignore_permissions=True)
            
            frappe.db.commit()
            
            # erstelle ggf. neue Rechnung
            mit_rechnung = False
            if new_mitgliedschaft.zahlung_mitgliedschaft < int(now().split("-")[0]):
                if new_mitgliedschaft.naechstes_jahr_geschuldet == 1:
                    mit_rechnung = create_mitgliedschaftsrechnung(new_mitgliedschaft.name, jahr=int(now().split("-")[0]), submit=True, attach_as_pdf=True, druckvorlage=get_druckvorlagen(sektion=neue_sektion, dokument='Zuzug mit EZ', mitgliedtyp=new_mitgliedschaft.mitgliedtyp_c, reduzierte_mitgliedschaft=new_mitgliedschaft.reduzierte_mitgliedschaft, language=new_mitgliedschaft.language)['default_druckvorlage'])
            
            # markiere neue Mitgliedschaft als zu validieren
            new_mitgliedschaft = frappe.get_doc("Mitgliedschaft", new_mitgliedschaft.name)
            new_mitgliedschaft.validierung_notwendig = 1
            new_mitgliedschaft.letzte_bearbeitung_von = 'User'
            if mit_rechnung:
                new_mitgliedschaft.zuzugs_rechnung = mit_rechnung
            else:
                druckvorlage = frappe.get_doc("Druckvorlage", get_druckvorlagen(sektion=neue_sektion, dokument='Zuzug ohne EZ', mitgliedtyp=new_mitgliedschaft.mitgliedtyp_c, reduzierte_mitgliedschaft=new_mitgliedschaft.reduzierte_mitgliedschaft, language=new_mitgliedschaft.language)['default_druckvorlage'])
                _new_korrespondenz = frappe.copy_doc(druckvorlage)
                _new_korrespondenz.doctype = 'Korrespondenz'
                _new_korrespondenz.sektion_id = new_mitgliedschaft.sektion_id
                _new_korrespondenz.titel = 'Zuzug ohne EZ'
                
                new_korrespondenz = frappe._dict(_new_korrespondenz.as_dict())
                keys_to_remove = [
                    'mitgliedtyp_c',
                    'validierungsstring',
                    'language',
                    'reduzierte_mitgliedschaft',
                    'dokument',
                    'default',
                    'deaktiviert',
                    'seite_1_qrr',
                    'seite_1_qrr_spende_hv',
                    'seite_2_qrr',
                    'seite_2_qrr_spende_hv',
                    'seite_3_qrr',
                    'seite_3_qrr_spende_hv',
                    'blatt_2_info_mahnung',
                    'tipps_mahnung'
                ]
                for key in keys_to_remove:
                    try:
                        new_korrespondenz.pop(key)
                    except:
                        pass
                
                new_korrespondenz['mv_mitgliedschaft'] = new_mitgliedschaft.name
                new_korrespondenz['massenlauf'] = 0
                
                new_korrespondenz = frappe.get_doc(new_korrespondenz)
                new_korrespondenz.insert(ignore_permissions=True)
                frappe.db.commit()
                
                new_mitgliedschaft.zuzug_korrespondenz = new_korrespondenz.name
            
            new_mitgliedschaft.save(ignore_permissions=True)
            
            return 1
            
        except Exception as err:
            frappe.log_error("{0}\n\n{1}\n\n{2}".format(err, frappe.utils.get_traceback(), new_mitgliedschaft.as_dict()), 'Sektionswechsel')
            return 0
    else:
        # Sektionswechsel nach ZH, und SO --> kein neues Mtiglied in ERPNext, Meldung Sektionswechsel erfolgt vie validate Trigger von Mitgliedschaft
        # Sobald ZH oder SO neues Mitglied verarbeitet erhält ERPNext via SP eine Neuanlage von/für ZH oder SO und ist mittels Freizügigkeitsabfrage wieder verfügbar
        return 1

@frappe.whitelist()
def create_mitgliedschaftsrechnung(mitgliedschaft, jahr=None, bezahlt=False, submit=False, attach_as_pdf=False, ignore_stichtage=False, inkl_hv=True, hv_bar_bezahlt=False, druckvorlage=False, massendruck=False):
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    sektion = frappe.get_doc("Sektion", mitgliedschaft.sektion_id)
    company = frappe.get_doc("Company", sektion.company)
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
    
    # finde passenden Artikel
    if mitgliedschaft.mitgliedtyp_c == 'Privat':
        item = [{"item_code": sektion.mitgliedschafts_artikel,"qty": 1, "cost_center": company.cost_center}]
        if not ignore_stichtage:
            reduziert_ab = getdate(getdate(today()).strftime("%Y") + "-" + getdate(sektion.reduzierter_mitgliederbeitrag).strftime("%m") + "-" + getdate(sektion.reduzierter_mitgliederbeitrag).strftime("%d"))
            gratis_ab = getdate(getdate(today()).strftime("%Y") + "-" + getdate(sektion.gratis_bis_ende_jahr).strftime("%m") + "-" + getdate(sektion.gratis_bis_ende_jahr).strftime("%d"))
            if getdate(today()) >= reduziert_ab:
                item = [{"item_code": sektion.mitgliedschafts_artikel_reduziert,"qty": 1, "cost_center": company.cost_center}]
                if getdate(today()) >= gratis_ab:
                    item = [
                        {"item_code": sektion.mitgliedschafts_artikel_gratis,"qty": 1, "cost_center": company.cost_center},
                        {"item_code": sektion.mitgliedschafts_artikel,"qty": 1, "cost_center": company.cost_center}
                    ]
                    jahr = int(getdate(today()).strftime("%Y")) + 1
        
        # prüfe Beitrittsgebühr
        if int(mitgliedschaft.zahlung_mitgliedschaft) == 0 and sektion.mitgliedschafts_artikel_beitritt:
            item.append({"item_code": sektion.mitgliedschafts_artikel_beitritt,"qty": 1, "cost_center": company.cost_center})
    
    if mitgliedschaft.mitgliedtyp_c == 'Geschäft':
        item = [{"item_code": sektion.mitgliedschafts_artikel_geschaeft,"qty": 1}]
        # prüfe Beitrittsgebühr
        if int(mitgliedschaft.zahlung_mitgliedschaft) == 0 and sektion.mitgliedschafts_artikel_beitritt_geschaeft:
            item.append({"item_code": sektion.mitgliedschafts_artikel_beitritt_geschaeft,"qty": 1, "cost_center": company.cost_center})
    
    # ~ if mitgliedschaft.mitgliedtyp_c == 'Kollektiv':
        # ~ item = [{"item_code": sektion.mitgliedschafts_artikel_kollektiv,"qty": 1}]
    
    if mitgliedschaft.status_c == 'Interessent*in':
        exclude_from_payment_reminder_until = '2099-12-31'
    else:
        exclude_from_payment_reminder_until = ''
    
    sinv = frappe.get_doc({
        "doctype": "Sales Invoice",
        "ist_mitgliedschaftsrechnung": 1,
        "mv_mitgliedschaft": mitgliedschaft.name,
        "company": sektion.company,
        "cost_center": company.cost_center,
        "customer": customer,
        "customer_address": address,
        "contact_person": contact,
        'mitgliedschafts_jahr': jahr or int(getdate(today()).strftime("%Y")),
        'due_date': add_days(today(), 30),
        'debit_to': company.default_receivable_account,
        'sektions_code': str(sektion.sektion_id) or '00',
        'sektion_id': mitgliedschaft.sektion_id,
        "items": item,
        "druckvorlage": druckvorlage if druckvorlage else '',
        "exclude_from_payment_reminder_until": exclude_from_payment_reminder_until
    })
    sinv.insert(ignore_permissions=True)
    sinv.esr_reference = get_qrr_reference(sales_invoice=sinv.name)
    sinv.save(ignore_permissions=True)
    
    if bezahlt:
        pos_profile = frappe.get_doc("POS Profile", sektion.pos_barzahlung)
        sinv.is_pos = 1
        sinv.pos_profile = pos_profile.name
        row = sinv.append('payments', {})
        row.mode_of_payment = pos_profile.payments[0].mode_of_payment
        row.account = pos_profile.payments[0].account
        row.type = pos_profile.payments[0].type
        row.amount = sinv.grand_total
        sinv.save(ignore_permissions=True)
    
    if massendruck:
        frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `rg_massendruck` = '{sinv}', `rg_massendruck_vormerkung` = 1 WHERE `name` = '{mitgliedschaft}'""".format(sinv=sinv.name, mitgliedschaft=mitgliedschaft.name), as_list=True)
    else:
        frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `rg_massendruck` = '', `rg_massendruck_vormerkung` = 0 WHERE `name` = '{mitgliedschaft}'""".format(mitgliedschaft=mitgliedschaft.name), as_list=True)
    
    if submit:
        # submit workaround weil submit ignore_permissions=True nicht kennt
        sinv.docstatus = 1
        sinv.save(ignore_permissions=True)
    
    if inkl_hv and mitgliedschaft.mitgliedtyp_c != 'Geschäft':
        fr_rechnung = create_hv_fr(mitgliedschaft=mitgliedschaft.name, sales_invoice=sinv.name, bezahlt=hv_bar_bezahlt)
    
    if attach_as_pdf:
        # add doc signature to allow print
        frappe.form_dict.key = sinv.get_signature()
        
        # erstellung Rechnungs PDF
        output = PdfFileWriter()
        output = frappe.get_print("Sales Invoice", sinv.name, 'Automatisierte Mitgliedschaftsrechnung', as_pdf = True, output = output, ignore_zugferd=True)
        
        file_name = "{sinv}_{datetime}".format(sinv=sinv.name, datetime=now().replace(" ", "_"))
        file_name = file_name.split(".")[0]
        file_name = file_name.replace(":", "-")
        file_name = file_name + ".pdf"
        
        filedata = get_file_data_from_writer(output)
        
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "folder": "Home/Attachments",
            "is_private": 1,
            "content": filedata,
            "attached_to_doctype": 'Mitgliedschaft',
            "attached_to_name": mitgliedschaft.name
        })
        
        _file.save(ignore_permissions=True)
    
    return sinv.name

@frappe.whitelist()
def make_kuendigungs_prozess(mitgliedschaft, datum_kuendigung, massenlauf, druckvorlage):
    # erfassung Kündigung
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    mitgliedschaft.kuendigung = datum_kuendigung
    mitgliedschaft.status_c = 'Kündigung'
    mitgliedschaft.validierung_notwendig = 0
    mitgliedschaft.kuendigung_druckvorlage = druckvorlage
    if massenlauf == '1':
        mitgliedschaft.kuendigung_verarbeiten = 1
    mitgliedschaft.save(ignore_permissions=True)
    
    # erstellung Kündigungs PDF
    output = PdfFileWriter()
    output = frappe.get_print("Mitgliedschaft", mitgliedschaft.name, 'Kündigungsbestätigung', as_pdf = True, output = output)
    
    pdf = frappe.utils.pdf.get_file_data_from_writer(output)
    file_name = "Kündigungsbestätigung_{mitgliedschaft}_{datetime}.pdf".format(mitgliedschaft=mitgliedschaft.name, datetime=now().replace(" ", "_"))
    
    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "folder": "Home/Attachments",
        "is_private": 1,
        "content": pdf,
        "attached_to_doctype": 'Mitgliedschaft',
        "attached_to_name": mitgliedschaft.name
    })
    
    _file.save(ignore_permissions=True)
    
    return 'done'

def close_open_validations(mitgliedschaft, typ):
    open_abl = frappe.db.sql("""SELECT `name` FROM `tabArbeits Backlog` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}' AND `status` = 'Open' AND `typ` = '{typ}'""".format(mitgliedschaft=mitgliedschaft, typ=typ), as_dict=True)
    
    for abl in open_abl:
        abl = frappe.get_doc("Arbeits Backlog", abl.name)
        abl.status = 'Completed'
        abl.save(ignore_permissions=True)

# API (eingehend von Service-Platform)
# -----------------------------------------------

# Neuanlage / Update Mitgliedschaft
def mvm_mitglieder(kwargs):
    if 'mitgliedId' in kwargs:
        if kwargs["mitgliedId"] > 0:
            return check_update_vs_neuanlage(kwargs)
        else:
            return raise_xxx(400, 'Bad Request', 'mitgliedId == 0')
    else:
        return raise_xxx(400, 'Bad Request', 'mitgliedId missing')

# Status Returns
def raise_xxx(code, title, message, daten=None):
    frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(code, title, message, frappe.utils.get_traceback(), daten or ''), 'SP API Error!')
    frappe.local.response.http_status_code = code
    frappe.local.response.message = message
    return ['{code} {title}'.format(code=code, title=title), {
        "error": {
            "code": code,
            "message": "{message}".format(message=message)
        }
    }]
    
def raise_200(answer='Success'):
    frappe.local.response.http_status_code = 200
    frappe.local.response.message = answer
    return ['200 Success', answer]

# API Funktionshelfer
# -----------------------------------------------
def check_update_vs_neuanlage(kwargs):
    if not frappe.db.exists("Mitgliedschaft", kwargs["mitgliedId"]):
        return mvm_neuanlage(kwargs)
    else:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", kwargs["mitgliedId"])
        return mvm_update(mitgliedschaft, kwargs)
        

def mvm_update(mitgliedschaft, kwargs):
    missing_keys = check_main_keys(kwargs)
    if not missing_keys:
        try:
            sektion_id = get_sektion_id(kwargs['sektionCode'])
            if not sektion_id:
                return raise_xxx(404, 'Not Found', 'Sektion ({sektion_id}) not found'.format(sektion_id=kwargs['sektionCode']), daten=kwargs)
                
            status_c = get_status_c(kwargs['status'])
            if not status_c:
                return raise_xxx(404, 'Not Found', 'MitgliedStatus ({status_c}) not found'.format(status_c=kwargs['status']), daten=kwargs)
                
            mitgliedtyp_c = get_mitgliedtyp_c(kwargs['typ'])
            if not mitgliedtyp_c:
                return raise_xxx(404, 'Not Found', 'typ ({mitgliedtyp_c}) not found'.format(mitgliedtyp_c=kwargs['Typ']), daten=kwargs)
            
            if kwargs['eintrittsdatum'] and status_c != 'Interessent*in':
                eintritt = kwargs['eintrittsdatum'].split("T")[0]
            else:
                eintritt = None
            
            if kwargs['neueSektionCode']:
                wegzug_zu = get_sektion_id(kwargs['neueSektionCode'])
            else:
                wegzug_zu = ''
            
            if kwargs['alteSektionCode']:
                zuzug_von = get_sektion_id(kwargs['alteSektionCode'])
            else:
                zuzug_von = ''
            
            if kwargs['zuzugsdatum']:
                zuzug = kwargs['zuzugsdatum'].split("T")[0]
            else:
                zuzug = ''
            
            if kwargs['wegzugsdatum']:
                wegzug = kwargs['wegzugsdatum'].split("T")[0]
            else:
                wegzug = ''
            
            if kwargs['austrittsdatum']:
                austritt = kwargs['austrittsdatum'].split("T")[0]
            else:
                austritt = ''
            
            if kwargs['kuendigungPer']:
                kuendigung = kwargs['kuendigungPer'].split("T")[0]
            else:
                kuendigung = ''
            
            if kwargs['zeitungAlsPdf']:
                m_und_w_pdf = 1
            else:
                m_und_w_pdf = 0
            
            if kwargs['isKollektiv']:
                ist_kollektiv = 1
            else:
                ist_kollektiv = '0'
            
            if kwargs['isGeschenkmitgliedschaft']:
                ist_geschenkmitgliedschaft = 1
            else:
                ist_geschenkmitgliedschaft = '0'
            
            if kwargs['isEinmaligeSchenkung']:
                ist_einmalige_schenkung = 1
            else:
                ist_einmalige_schenkung = '0'
            
            if kwargs['schenkerHasGeschenkunterlagen']:
                geschenkunterlagen_an_schenker = 1
            else:
                geschenkunterlagen_an_schenker = '0'
            
            if kwargs['datumBezahltHaftpflicht']:
                datum_hv_zahlung = kwargs['datumBezahltHaftpflicht'].split("T")[0]
            else:
                datum_hv_zahlung = None
            
            if kwargs['onlineHaftpflicht']:
                online_haftpflicht = kwargs['onlineHaftpflicht']
            else:
                online_haftpflicht = None
            
            if kwargs['onlineGutschrift']:
                online_gutschrift = kwargs['onlineGutschrift']
            else:
                online_gutschrift = None
            
            if kwargs['onlineBetrag']:
                online_betrag = kwargs['onlineBetrag']
            else:
                online_betrag = None
            
            if kwargs['datumOnlineVerbucht']:
                datum_online_verbucht = kwargs['datumOnlineVerbucht']
            else:
                datum_online_verbucht = None
            
            if kwargs['datumOnlineGutschrift']:
                datum_online_gutschrift = kwargs['datumOnlineGutschrift']
            else:
                datum_online_gutschrift = None
            
            if kwargs['onlinePaymentMethod']:
                online_payment_method = kwargs['onlinePaymentMethod']
            else:
                online_payment_method = None
            
            if kwargs['onlinePaymentId']:
                online_payment_id = kwargs['onlinePaymentId']
            else:
                online_payment_id = None
            
            region = ''
            if kwargs['regionCode']:
                regionen = frappe.db.sql("""SELECT `name` FROM `tabRegion` WHERE `region_c` = '{region}'""".format(region=kwargs['regionCode']), as_dict=True)
                if len(regionen) > 0:
                    region = regionen[0].name
            
            mitgliedschaft.mitglied_nr = kwargs['mitgliedNummer']
            mitgliedschaft.sektion_id = sektion_id
            mitgliedschaft.region = region
            mitgliedschaft.region_manuell = 1 if kwargs['regionManuell'] else '0'
            mitgliedschaft.status_c = status_c
            mitgliedschaft.mitglied_id = kwargs['mitgliedId']
            mitgliedschaft.mitgliedtyp_c = mitgliedtyp_c
            mitgliedschaft.inkl_hv = get_inkl_hv(kwargs["jahrBezahltHaftpflicht"])
            mitgliedschaft.m_und_w = kwargs['anzahlZeitungen']
            mitgliedschaft.m_und_w_pdf = m_und_w_pdf
            mitgliedschaft.wichtig = kwargs['bemerkungen'] if kwargs['bemerkungen'] else ''
            mitgliedschaft.eintrittsdatum = eintritt
            mitgliedschaft.zuzug = zuzug
            mitgliedschaft.zuzug_von = zuzug_von
            mitgliedschaft.wegzug = wegzug
            mitgliedschaft.wegzug_zu = wegzug_zu
            mitgliedschaft.austritt = austritt
            mitgliedschaft.kuendigung = kuendigung
            mitgliedschaft.zahlung_hv = int(kwargs['jahrBezahltHaftpflicht']) if kwargs['jahrBezahltHaftpflicht'] else 0
            mitgliedschaft.bezahltes_mitgliedschaftsjahr = int(kwargs['jahrBezahltMitgliedschaft']) if kwargs['jahrBezahltMitgliedschaft'] else 0
            mitgliedschaft.naechstes_jahr_geschuldet = 1 if kwargs['naechstesJahrGeschuldet'] else '0'
            mitgliedschaft.validierung_notwendig = 0
            mitgliedschaft.language = get_sprache_abk(language=kwargs['sprache']) if kwargs['sprache'] else 'de'
            mitgliedschaft.ist_kollektiv = ist_kollektiv
            mitgliedschaft.ist_geschenkmitgliedschaft = ist_geschenkmitgliedschaft
            mitgliedschaft.ist_einmalige_schenkung = ist_einmalige_schenkung
            mitgliedschaft.geschenkunterlagen_an_schenker = geschenkunterlagen_an_schenker
            mitgliedschaft.datum_hv_zahlung = datum_hv_zahlung
            mitgliedschaft.letzte_bearbeitung_von = 'SP'
            mitgliedschaft.online_haftpflicht = online_haftpflicht
            mitgliedschaft.online_gutschrift = online_gutschrift
            mitgliedschaft.online_betrag = online_betrag
            mitgliedschaft.datum_online_verbucht = datum_online_verbucht
            mitgliedschaft.datum_online_gutschrift = datum_online_gutschrift
            mitgliedschaft.online_payment_method = online_payment_method
            mitgliedschaft.online_payment_id = online_payment_id
            
            mitgliedschaft = adressen_und_kontakt_handling(mitgliedschaft, kwargs)
            
            if not mitgliedschaft:
                return raise_xxx(500, 'Internal Server Error', 'Beim Adressen Update ist etwas schief gelaufen', daten=kwargs)
            
            if status_c in ('Online-Anmeldung', 'Online-Beitritt', 'Online-Kündigung'):
                mitgliedschaft.validierung_notwendig = 1
                if status_c == 'Online-Beitritt':
                    if online_haftpflicht:
                        if int(online_haftpflicht) == 1:
                            mitgliedschaft.datum_hv_zahlung = eintritt
                    mitgliedschaft.datum_zahlung_mitgliedschaft = eintritt
            else:
                if kwargs['needsValidation']:
                    mitgliedschaft.validierung_notwendig = 1
                    if status_c != 'Zuzug':
                        mitgliedschaft.status_vor_onl_mutation = status_c
                        mitgliedschaft.status_c = 'Online-Mutation'
                    
            
            # Zuzugsdatum-Fix bei Sektionswechsel von MVZH
            if mitgliedschaft.zuzug_von == 'MVZH' and mitgliedschaft.status_c == 'Zuzug':
                if not mitgliedschaft.zuzug:
                    mitgliedschaft.zuzug = today()
            
            mitgliedschaft.flags.ignore_links=True
            mitgliedschaft.save()
            frappe.db.commit()
            
            create_sp_log(mitgliedschaft.name, False, kwargs)
            
            return raise_200()
            
        except Exception as err:
            return raise_xxx(500, 'Internal Server Error', err, daten=kwargs)
    else:
        return missing_keys

def mvm_neuanlage(kwargs):
    missing_keys = check_main_keys(kwargs)
    if not missing_keys:
        try:
            sektion_id = get_sektion_id(kwargs['sektionCode'])
            if not sektion_id:
                return raise_xxx(404, 'Not Found', 'Sektion ({sektion_id}) not found'.format(sektion_id=kwargs['sektionCode']), daten=kwargs)
            
            status_c = get_status_c(kwargs['status'])
            if not status_c:
                return raise_xxx(404, 'Not Found', 'MitgliedStatus ({status_c}) not found'.format(status_c=kwargs['status']), daten=kwargs)
            
            if kwargs['neueSektionCode']:
                wegzug_zu = get_sektion_id(kwargs['neueSektionCode'])
            else:
                wegzug_zu = ''
            
            if kwargs['alteSektionCode']:
                zuzug_von = get_sektion_id(kwargs['alteSektionCode'])
            else:
                zuzug_von = ''
            
            mitgliedtyp_c = get_mitgliedtyp_c(kwargs['typ'])
            if not mitgliedtyp_c:
                return raise_xxx(404, 'Not Found', 'typ ({mitgliedtyp_c}) not found'.format(mitgliedtyp_c=kwargs['Typ']), daten=kwargs)
            
            if kwargs['eintrittsdatum'] and status_c != 'Interessent*in':
                eintritt = kwargs['eintrittsdatum'].split("T")[0]
            else:
                eintritt = None
            
            if kwargs['zuzugsdatum']:
                zuzug = kwargs['zuzugsdatum'].split("T")[0]
            else:
                zuzug = ''
            
            if kwargs['wegzugsdatum']:
                wegzug = kwargs['wegzugsdatum'].split("T")[0]
            else:
                wegzug = ''
            
            if kwargs['austrittsdatum']:
                austritt = kwargs['austrittsdatum'].split("T")[0]
            else:
                austritt = ''
            
            if kwargs['kuendigungPer']:
                kuendigung = kwargs['kuendigungPer'].split("T")[0]
            else:
                kuendigung = ''
            
            if kwargs['zeitungAlsPdf']:
                m_und_w_pdf = 1
            else:
                m_und_w_pdf = 0
            
            if kwargs['isKollektiv']:
                ist_kollektiv = 1
            else:
                ist_kollektiv = '0'
            
            if kwargs['isGeschenkmitgliedschaft']:
                ist_geschenkmitgliedschaft = 1
            else:
                ist_geschenkmitgliedschaft = '0'
            
            if kwargs['isEinmaligeSchenkung']:
                ist_einmalige_schenkung = 1
            else:
                ist_einmalige_schenkung = '0'
            
            if kwargs['schenkerHasGeschenkunterlagen']:
                geschenkunterlagen_an_schenker = 1
            else:
                geschenkunterlagen_an_schenker = '0'
            
            if kwargs['datumBezahltHaftpflicht']:
                datum_hv_zahlung = kwargs['datumBezahltHaftpflicht'].split("T")[0]
            else:
                datum_hv_zahlung = None
            
            if kwargs['onlineHaftpflicht']:
                online_haftpflicht = kwargs['onlineHaftpflicht']
            else:
                online_haftpflicht = None
            
            if kwargs['onlineGutschrift']:
                online_gutschrift = kwargs['onlineGutschrift']
            else:
                online_gutschrift = None
            
            if kwargs['onlineBetrag']:
                online_betrag = kwargs['onlineBetrag']
            else:
                online_betrag = None
            
            if kwargs['datumOnlineVerbucht']:
                datum_online_verbucht = kwargs['datumOnlineVerbucht']
                if zuzug_von not in ('MVZH', 'MVSO'):
                    datum_zahlung_mitgliedschaft = datum_online_verbucht.split("T")[0]
                else:
                    datum_zahlung_mitgliedschaft = None
            else:
                datum_online_verbucht = None
                datum_zahlung_mitgliedschaft = None
            
            if kwargs['datumOnlineGutschrift']:
                datum_online_gutschrift = kwargs['datumOnlineGutschrift']
            else:
                datum_online_gutschrift = None
            
            if kwargs['onlinePaymentMethod']:
                online_payment_method = kwargs['onlinePaymentMethod']
            else:
                online_payment_method = None
            
            if kwargs['onlinePaymentId']:
                online_payment_id = kwargs['onlinePaymentId']
            else:
                online_payment_id = None
            
            region = ''
            if kwargs['regionCode']:
                regionen = frappe.db.sql("""SELECT `name` FROM `tabRegion` WHERE `region_c` = '{region}'""".format(region=kwargs['regionCode']), as_dict=True)
                if len(regionen) > 0:
                    region = regionen[0].name
            
            new_mitgliedschaft = frappe.get_doc({
                'doctype': 'Mitgliedschaft',
                'mitglied_nr': str(kwargs['mitgliedNummer']),
                'sektion_id': sektion_id,
                'region': region,
                'region_manuell': 1 if kwargs['regionManuell'] else '0',
                'status_c': status_c,
                'mitglied_id': str(kwargs['mitgliedId']),
                'mitgliedtyp_c': mitgliedtyp_c,
                'inkl_hv': get_inkl_hv(kwargs["jahrBezahltHaftpflicht"]),
                'm_und_w': kwargs['anzahlZeitungen'],
                'm_und_w_pdf': m_und_w_pdf,
                'wichtig': str(kwargs['bemerkungen']) if kwargs['bemerkungen'] else '',
                'eintrittsdatum': eintritt,
                'zuzug': zuzug,
                'zuzug_von': zuzug_von,
                'wegzug': wegzug,
                'wegzug_zu': wegzug_zu,
                'austritt': austritt,
                'kuendigung': kuendigung,
                'zahlung_hv': int(kwargs['jahrBezahltHaftpflicht']) if kwargs['jahrBezahltHaftpflicht'] else 0,
                'bezahltes_mitgliedschaftsjahr': int(kwargs['jahrBezahltMitgliedschaft']) if kwargs['jahrBezahltMitgliedschaft'] else 0,
                'naechstes_jahr_geschuldet': 1 if kwargs['naechstesJahrGeschuldet'] else '0',
                'validierung_notwendig': 0,
                'language': get_sprache_abk(language=kwargs['sprache']),
                'ist_kollektiv': ist_kollektiv,
                'ist_geschenkmitgliedschaft': ist_geschenkmitgliedschaft,
                'ist_einmalige_schenkung': ist_einmalige_schenkung,
                'geschenkunterlagen_an_schenker': geschenkunterlagen_an_schenker,
                'datum_hv_zahlung': datum_hv_zahlung,
                'letzte_bearbeitung_von': 'SP',
                'online_haftpflicht': online_haftpflicht,
                'online_gutschrift': online_gutschrift,
                'online_betrag': online_betrag,
                'datum_online_verbucht': datum_online_verbucht,
                'datum_online_gutschrift': datum_online_gutschrift,
                'online_payment_method': online_payment_method,
                'online_payment_id': online_payment_id,
                'datum_zahlung_mitgliedschaft': datum_zahlung_mitgliedschaft
            })
            
            new_mitgliedschaft = adressen_und_kontakt_handling(new_mitgliedschaft, kwargs)
            
            if not new_mitgliedschaft:
                return raise_xxx(500, 'Internal Server Error', 'Bei der Adressen Anlage ist etwas schief gelaufen', daten=kwargs)
            
            if status_c in ('Online-Anmeldung', 'Online-Beitritt', 'Online-Kündigung'):
                new_mitgliedschaft.validierung_notwendig = 1
                if status_c == 'Online-Beitritt':
                    if online_haftpflicht:
                        if int(online_haftpflicht) == 1:
                            new_mitgliedschaft.datum_hv_zahlung = eintritt
                    new_mitgliedschaft.datum_zahlung_mitgliedschaft = eintritt
            else:
                if kwargs['needsValidation']:
                    new_mitgliedschaft.validierung_notwendig = 1
                    if status_c != 'Zuzug':
                        new_mitgliedschaft.status_vor_onl_mutation = status_c
                        new_mitgliedschaft.status_c = 'Online-Mutation'
            
            # Zuzugsdatum-Fix bei Sektionswechsel von MVZH
            if new_mitgliedschaft.zuzug_von == 'MVZH' and new_mitgliedschaft.status_c == 'Zuzug':
                if not new_mitgliedschaft.zuzug:
                    new_mitgliedschaft.zuzug = today()
            
            new_mitgliedschaft.insert()
            frappe.db.commit()
            
            create_sp_log(new_mitgliedschaft.name, True, kwargs)
            
            return raise_200()
            
        except Exception as err:
            return raise_xxx(500, 'Internal Server Error', err, daten=kwargs)
            
    else:
        return missing_keys

def check_main_keys(kwargs):
    mandatory_keys = [
        'mitgliedNummer',
        'mitgliedId',
        'sektionCode',
        'typ',
        'status',
        'regionCode',
        'istTemporaeresMitglied',
        'fuerBewirtschaftungGesperrt',
        'erfassungsdatum',
        'eintrittsdatum',
        'austrittsdatum',
        'zuzugsdatum',
        'wegzugsdatum',
        'kuendigungPer',
        'jahrBezahltMitgliedschaft',
        'jahrBezahltHaftpflicht',
        'naechstesJahrGeschuldet',
        'bemerkungen',
        'anzahlZeitungen',
        'zeitungAlsPdf',
        'adressen',
        'sprache',
        'needsValidation',
        'isKollektiv',
        'isGeschenkmitgliedschaft',
        'isEinmaligeSchenkung',
        'schenkerHasGeschenkunterlagen',
        'datumBezahltHaftpflicht',
        'onlineHaftpflicht',
        'onlineGutschrift',
        'onlineBetrag',
        'datumOnlineVerbucht',
        'datumOnlineGutschrift',
        'onlinePaymentMethod',
        'onlinePaymentId'
    ]
    for key in mandatory_keys:
        if key not in kwargs:
            return raise_xxx(400, 'Bad Request', '{key} missing'.format(key=key), daten=kwargs)
    if 'Geschenkmitgliedschaft' in kwargs:
        return raise_xxx(400, 'Bad Request', 'Geschenkmitgliedschaft unbekannt', daten=kwargs)
    else:
        return False

def get_sektion_id(sektion_c):
    sektionen = frappe.db.sql("""SELECT `name` FROM `tabSektion` WHERE `sektion_c` = '{sektion_c}'""".format(sektion_c=sektion_c), as_dict=True)
    if len(sektionen) > 0:
        return sektionen[0].name
    else:
        return False

def get_sprache_abk(language='Deutsch'):
    language = frappe.db.sql("""SELECT `name` FROM `tabLanguage` WHERE `language_name` = '{language}'""".format(language=language), as_list=True)
    if len(language) > 0:
        return language[0][0]
    else:
        return 'de'

def get_sektion_code(sektion):
    sektionen = frappe.db.sql("""SELECT `sektion_c` FROM `tabSektion` WHERE `name` = '{sektion}'""".format(sektion=sektion), as_dict=True)
    if len(sektionen) > 0:
        return sektionen[0].sektion_c
    else:
        return False

def get_status_c(status_c):
    mapper = {
        'Anmeldung': 'Anmeldung',
        'OnlineAnmeldung': 'Online-Anmeldung',
        'OnlineBeitritt': 'Online-Beitritt',
        'OnlineKuendigung': 'Online-Kündigung',
        'Zuzug': 'Zuzug',
        'Regulaer': 'Regulär',
        'Gestorben': 'Gestorben',
        'Kuendigung': 'Kündigung',
        'Wegzug': 'Wegzug',
        'Ausschluss': 'Ausschluss',
        'Inaktiv': 'Inaktiv',
        'InteressentIn': 'Interessent*in'
    }
    if status_c in mapper:
        return mapper[status_c]
    else:
        return False

def get_mitgliedtyp_c(mitgliedtyp_c):
    mapper = {
        'privat': 'Privat',
        'kollektiv': 'Kollektiv',
        'geschaeft': 'Geschäft',
        'Privat': 'Privat',
        'Kollektiv': 'Kollektiv',
        'Geschaeft': 'Geschäft'
    }
    if mitgliedtyp_c.lower() in mapper:
        return mapper[mitgliedtyp_c.lower()]
    else:
        return False

def get_inkl_hv(inkl_hv):
    curr_year = int(getdate().strftime("%Y"))
    if inkl_hv:
        if int(inkl_hv) >= curr_year:
            return 1
        else:
            return 0
    else:
        return 0

def check_email(email=None):
    # ~ import re
    # ~ regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    # ~ if email:
        # ~ if(re.fullmatch(regex, email)):
            # ~ return True
        # ~ else:
            # ~ frappe.log_error("Folgende E-Mail musste entfernt werden: {0}".format(email), 'Fehlerhafte E-Mail')
            # ~ return False
    # ~ else:
        # ~ return False
    return True
    
def adressen_und_kontakt_handling(new_mitgliedschaft, kwargs):
    try:
        mitglied = False
        objekt = False
        rechnung = False
        filiale = False
        mitbewohner = False
        zeitung = False
        
        for adresse in kwargs["adressen"]["adressenListe"]:
            adressen_dict = adresse
            
            if isinstance(adressen_dict, str):
                adressen_dict = json.loads(adressen_dict)
            
            if adressen_dict['typ'] == 'Filiale':
                filiale = adressen_dict
            elif adressen_dict['typ'] == 'Mitbewohner':
                mitbewohner = adressen_dict
            elif adressen_dict['typ'] == 'Zeitung':
                zeitung = adressen_dict
            elif adressen_dict['typ'] == 'Mitglied':
                mitglied = adressen_dict
            elif adressen_dict['typ'] == 'Objekt':
                objekt = adressen_dict
            elif adressen_dict['typ'] == 'Rechnung':
                rechnung = adressen_dict
            else:
                # unbekannter adresstyp
                frappe.log_error("{0}".format(adressen_dict), 'unbekannter adresstyp')
                return False
        
        if not mitglied:
            frappe.log_error("{0}".format(kwargs), 'adress/kontakt anlage: Keine mitglied Adresse')
            # muss zwingend vorhanden sein
            return False
        
        if mitglied:
            # erfassung mitglied-daten
            for kontaktdaten in mitglied["kontakte"]:
                if kontaktdaten["istHauptkontakt"]:
                    # hauptmiglied
                    if not mitglied["strasse"] or str(mitglied["strasse"]) == '':
                        if not mitglied["postfach"]:
                            # eines von beidem muss zwingend vorhanden sein
                            frappe.log_error("{0}".format(kwargs), 'adress/kontakt anlage: Weder Postfach noch Strasse')
                            return False
                        else:
                            mitglied["strasse"] = 'Postfach'
                    if kontaktdaten["firma"]:
                        new_mitgliedschaft.kundentyp = 'Unternehmen'
                        new_mitgliedschaft.firma = str(kontaktdaten["firma"])
                        new_mitgliedschaft.zusatz_firma = str(kontaktdaten["firmaZusatz"]) if kontaktdaten["firmaZusatz"] else ''
                    else:
                        new_mitgliedschaft.kundentyp = 'Einzelperson'
                    if kontaktdaten["anrede"] != 'Unbekannt':
                        new_mitgliedschaft.anrede_c = str(kontaktdaten["anrede"]) if kontaktdaten["anrede"] else ''
                    new_mitgliedschaft.nachname_1 = str(kontaktdaten["nachname"]) if kontaktdaten["nachname"] else ''
                    new_mitgliedschaft.vorname_1 = str(kontaktdaten["vorname"]) if kontaktdaten["vorname"] else ''
                    new_mitgliedschaft.tel_p_1 = str(kontaktdaten["telefon"]) if kontaktdaten["telefon"] else ''
                    if kontaktdaten["mobile"]:
                        if str(kontaktdaten["mobile"]) != str(kontaktdaten["telefon"]):
                            new_mitgliedschaft.tel_m_1 = str(kontaktdaten["mobile"])
                        else:
                            new_mitgliedschaft.tel_m_1 = ''
                    else:
                        new_mitgliedschaft.tel_m_1 = ''
                    new_mitgliedschaft.tel_g_1 = str(kontaktdaten["telefonGeschaeft"]) if kontaktdaten["telefonGeschaeft"] else ''
                    new_mitgliedschaft.e_mail_1 = str(kontaktdaten["email"]) if check_email(kontaktdaten["email"]) else ''
                    new_mitgliedschaft.zusatz_adresse = str(mitglied["adresszusatz"]) if mitglied["adresszusatz"] else ''
                    new_mitgliedschaft.strasse = str(mitglied["strasse"]) if mitglied["strasse"] else ''
                    new_mitgliedschaft.nummer = str(mitglied["hausnummer"]) if mitglied["hausnummer"] else ''
                    new_mitgliedschaft.nummer_zu = str(mitglied["hausnummerZusatz"]) if mitglied["hausnummerZusatz"] else ''
                    new_mitgliedschaft.postfach = 1 if mitglied["postfach"] else '0'
                    new_mitgliedschaft.postfach_nummer = str(mitglied["postfachNummer"]) if mitglied["postfachNummer"] else ''
                    new_mitgliedschaft.plz = str(mitglied["postleitzahl"]) if mitglied["postleitzahl"] else ''
                    new_mitgliedschaft.ort = str(mitglied["ort"]) if mitglied["ort"] else ''
                    if mitglied["fuerKorrespondenzGesperrt"]:
                        new_mitgliedschaft.adressen_gesperrt = 1
                else:
                    # solidarmitglied
                    new_mitgliedschaft.hat_solidarmitglied = 1
                    if kontaktdaten["anrede"] != 'Unbekannt':
                        new_mitgliedschaft.anrede_2 = str(kontaktdaten["anrede"]) if kontaktdaten["anrede"] else ''
                    new_mitgliedschaft.nachname_2 = str(kontaktdaten["nachname"]) if kontaktdaten["nachname"] else ''
                    new_mitgliedschaft.vorname_2 = str(kontaktdaten["vorname"]) if kontaktdaten["vorname"] else ''
                    new_mitgliedschaft.tel_p_2 = str(kontaktdaten["telefon"]) if kontaktdaten["telefon"] else ''
                    if kontaktdaten["mobile"]:
                        if str(kontaktdaten["mobile"]) != str(kontaktdaten["telefon"]):
                            new_mitgliedschaft.tel_m_2 = str(kontaktdaten["mobile"])
                        else:
                            new_mitgliedschaft.tel_m_2 = ''
                    else:
                        new_mitgliedschaft.tel_m_2 = ''
                    new_mitgliedschaft.tel_g_2 = str(kontaktdaten["telefonGeschaeft"]) if kontaktdaten["telefonGeschaeft"] else ''
                    new_mitgliedschaft.e_mail_2 = str(kontaktdaten["email"]) if check_email(kontaktdaten["email"]) else ''
        
        if objekt:
            if objekt["strasse"]:
                new_mitgliedschaft.abweichende_objektadresse = 1
                new_mitgliedschaft.objekt_zusatz_adresse = str(objekt["adresszusatz"]) if objekt["adresszusatz"] else ''
                new_mitgliedschaft.objekt_strasse = str(objekt["strasse"]) if objekt["strasse"] else ''
                new_mitgliedschaft.objekt_hausnummer = str(objekt["hausnummer"]) if objekt["hausnummer"] else ''
                new_mitgliedschaft.objekt_nummer_zu = str(objekt["hausnummerZusatz"]) if objekt["hausnummerZusatz"] else ''
                new_mitgliedschaft.objekt_plz = str(objekt["postleitzahl"]) if objekt["postleitzahl"] else ''
                new_mitgliedschaft.objekt_ort = str(objekt["ort"]) if objekt["ort"] else ''
                if objekt["fuerKorrespondenzGesperrt"]:
                    new_mitgliedschaft.adressen_gesperrt = 1
            else:
                frappe.log_error("Adressdaten:\n{0}\n\nMitgliedsdaten:\n{1}".format(objekt, kwargs), 'Adresse Typ Objekt: Wurde entfernt; fehlende Strasse')
                # reset objektadresse
                new_mitgliedschaft.abweichende_objektadresse = 0
                new_mitgliedschaft.objekt_zusatz_adresse = None
                new_mitgliedschaft.objekt_strasse = None
                new_mitgliedschaft.objekt_hausnummer = None
                new_mitgliedschaft.objekt_plz = None
                new_mitgliedschaft.objekt_ort = None
        else:
            # reset objektadresse
            new_mitgliedschaft.abweichende_objektadresse = 0
            new_mitgliedschaft.objekt_zusatz_adresse = None
            new_mitgliedschaft.objekt_strasse = None
            new_mitgliedschaft.objekt_hausnummer = None
            new_mitgliedschaft.objekt_plz = None
            new_mitgliedschaft.objekt_ort = None
        
        
        if rechnung:
            new_mitgliedschaft.abweichende_rechnungsadresse = 1
            new_mitgliedschaft.rg_zusatz_adresse = str(rechnung["adresszusatz"]) if rechnung["adresszusatz"] else ''
            new_mitgliedschaft.rg_strasse = str(rechnung["strasse"]) if rechnung["strasse"] else 'Postfach' if rechnung["postfach"] else ''
            new_mitgliedschaft.rg_nummer = str(rechnung["hausnummer"]) if rechnung["hausnummer"] else ''
            new_mitgliedschaft.rg_nummer_zu = str(rechnung["hausnummerZusatz"]) if rechnung["hausnummerZusatz"] else ''
            new_mitgliedschaft.rg_postfach = 1 if rechnung["postfach"] else '0'
            new_mitgliedschaft.rg_postfach_nummer = str(rechnung["postfachNummer"]) if rechnung["postfachNummer"] else ''
            new_mitgliedschaft.rg_plz = str(rechnung["postleitzahl"]) if rechnung["postleitzahl"] else ''
            new_mitgliedschaft.rg_ort = str(rechnung["ort"]) if rechnung["ort"] else ''
            if rechnung["fuerKorrespondenzGesperrt"]:
                new_mitgliedschaft.adressen_gesperrt = 1
            for kontaktdaten in rechnung["kontakte"]:
                if kontaktdaten["istHauptkontakt"]:
                    if (str(kontaktdaten["nachname"]) + str(kontaktdaten["vorname"])) != (new_mitgliedschaft.nachname_1 + new_mitgliedschaft.vorname_1):
                        # unabhängiger debitor
                        new_mitgliedschaft.unabhaengiger_debitor = 1
                        if kontaktdaten["firma"]:
                            new_mitgliedschaft.rg_kundentyp = 'Unternehmen'
                            new_mitgliedschaft.rg_firma = str(kontaktdaten["firma"])
                            new_mitgliedschaft.rg_zusatz_firma = str(kontaktdaten["firmaZusatz"]) if kontaktdaten["firmaZusatz"] else ''
                        else:
                            new_mitgliedschaft.rg_kundentyp = 'Einzelperson'
                        if kontaktdaten["anrede"] != 'Unbekannt':
                            new_mitgliedschaft.rg_anrede = str(kontaktdaten["anrede"]) if kontaktdaten["anrede"] else ''
                        new_mitgliedschaft.rg_nachname = str(kontaktdaten["nachname"]) if kontaktdaten["nachname"] else ''
                        new_mitgliedschaft.rg_vorname = str(kontaktdaten["vorname"]) if kontaktdaten["vorname"] else ''
                        new_mitgliedschaft.rg_tel_p = str(kontaktdaten["telefon"]) if kontaktdaten["telefon"] else ''
                        if kontaktdaten["mobile"]:
                            if str(kontaktdaten["mobile"]) != str(kontaktdaten["telefon"]):
                                new_mitgliedschaft.rg_tel_m = str(kontaktdaten["mobile"])
                            else:
                                new_mitgliedschaft.rg_tel_m = ''
                        else:
                            new_mitgliedschaft.rg_tel_m = ''
                        new_mitgliedschaft.rg_tel_g = str(kontaktdaten["telefonGeschaeft"]) if kontaktdaten["telefonGeschaeft"] else ''
                        new_mitgliedschaft.rg_e_mail = str(kontaktdaten["email"]) if check_email(kontaktdaten["email"]) else ''
                    
        
        if zeitung:
            # manuelle erfassung zeitung
            frappe.log_error("Adressdaten:\n{0}\n\nMitgliedsdaten:\n{1}".format(zeitung, kwargs), 'Adresse Typ Zeitung: Manuelle Verarbeitung')
        
        if mitbewohner:
            # manuelle erfassung solidarmitglied
            frappe.log_error("Adressdaten:\n{0}\n\nMitgliedsdaten:\n{1}".format(mitbewohner, kwargs), 'Adresse Typ Mitbewohner: Manuelle Verarbeitung')
        
        if filiale:
            # manuelle erfassung filiale
            frappe.log_error("Adressdaten:\n{0}\n\nMitgliedsdaten:\n{1}".format(filiale, kwargs), 'Adresse Typ Filiale: Manuelle Verarbeitung')
        
        
        return new_mitgliedschaft
        
    except Exception as err:
        return raise_xxx(500, 'Internal Server Error', err, daten=kwargs)

# API (ausgehend zu Service-Platform)
# -----------------------------------------------

# Bezug neuer mitgliedId 
def mvm_neue_mitglieder_nummer(mitgliedschaft):
    from mvd.mvd.service_plattform.api import neue_mitglieder_nummer
    sektion_code = get_sektion_code(mitgliedschaft.sektion_id)
    needsMitgliedNummer = True
    if mitgliedschaft.status_c in ('Interessent*in', 'Zuzug'):
        needsMitgliedNummer = False
    return neue_mitglieder_nummer(sektion_code, needsMitgliedNummer=needsMitgliedNummer)

# Bezug neuer mitgliedId 
def mvm_mitglieder_nummer_update(mitgliedId):
    from mvd.mvd.service_plattform.api import mitglieder_nummer_update
    return mitglieder_nummer_update(mitgliedId)['mitgliedNummer']

def send_mvm_to_sp(mitgliedschaft, update):
    if str(get_sektion_code(mitgliedschaft.sektion_id)) != 'ZH':
        if not int(frappe.db.get_single_value('Service Plattform API', 'queue')) == 1:
            from mvd.mvd.service_plattform.api import update_mvm
            prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
            update_status = update_mvm(prepared_mvm, update)
            return update_status
        else:
            create_sp_queue(mitgliedschaft, update)

def create_sp_queue(mitgliedschaft, update):
    existing_queue = frappe.db.sql("""SELECT COUNT(`name`) as `qty` FROM `tabService Platform Queue` WHERE `status` = 'Open' AND `mv_mitgliedschaft` = '{mitgliedschaft}'""".format(mitgliedschaft=mitgliedschaft.mitglied_id), as_dict=True)[0].qty
    if existing_queue > 0 and update:
        return
    else:
        queue = frappe.get_doc({
            "doctype": "Service Platform Queue",
            "status": "Open",
            "mv_mitgliedschaft": mitgliedschaft.mitglied_id,
            "sektion_id": mitgliedschaft.sektion_id,
            "update": 1 if update else 0
        })
        queue.insert(ignore_permissions=True)
        
        return

def send_mvm_sektionswechsel(mitgliedschaft):
    from mvd.mvd.service_plattform.api import sektionswechsel
    prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
    neue_sektion = ''
    if mitgliedschaft.wegzug_zu == 'MVZH':
        neue_sektion = 'ZH'
    elif mitgliedschaft.wegzug_zu == 'MVSO':
        neue_sektion = 'SO'
    elif mitgliedschaft.wegzug_zu == 'MVBE':
        neue_sektion = 'BE'
    sektionswechsel(prepared_mvm, neue_sektion)

def prepare_mvm_for_sp(mitgliedschaft):
    adressen = get_adressen_for_sp(mitgliedschaft)
    
    typ_mapper = {
        'Kollektiv': 'Kollektiv',
        'Privat': 'Privat',
        'Geschäft': 'Geschaeft'
    }
    
    status_mapper = {
        'Anmeldung': 'Anmeldung',
        'Online-Anmeldung': 'OnlineAnmeldung',
        'Online-Beitritt': 'OnlineBeitritt',
        'Online-Kündigung': 'OnlineKuendigung',
        'Zuzug': 'Zuzug',
        'Regulär': 'Regulaer',
        'Gestorben': 'Gestorben',
        'Kündigung': 'Kuendigung',
        'Wegzug': 'Wegzug',
        'Ausschluss': 'Ausschluss',
        'Inaktiv': 'Inaktiv',
        'Interessent*in': 'InteressentIn'
    }
    
    prepared_mvm = {
        "mitgliedNummer": str(mitgliedschaft.mitglied_nr),
        "mitgliedId": int(mitgliedschaft.mitglied_id),
        "sektionCode": str(get_sektion_code(mitgliedschaft.sektion_id)),
        "regionCode": frappe.get_value("Region", mitgliedschaft.region, "region_c") if mitgliedschaft.region else None,
        "regionManuell": True if mitgliedschaft.region_manuell else False,
        "typ": str(typ_mapper[mitgliedschaft.mitgliedtyp_c]),
        "status": str(status_mapper[mitgliedschaft.status_c]),
        "sprache": get_sprache(language=mitgliedschaft.language) if mitgliedschaft.language else 'Deutsch',
        "istTemporaeresMitglied": False, # ???
        "fuerBewirtschaftungGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
        "erfassungsdatum": str(mitgliedschaft.creation).replace(" ", "T"),
        "eintrittsdatum": str(mitgliedschaft.eintrittsdatum).replace(" ", "T") + "T00:00:00" if mitgliedschaft.eintrittsdatum else None,
        "austrittsdatum": str(mitgliedschaft.austritt).replace(" ", "T") + "T00:00:00" if mitgliedschaft.austritt else None,
        "alteSektionCode": str(get_sektion_code(mitgliedschaft.zuzug_von)) if mitgliedschaft.zuzug_von else None,
        "zuzugsdatum": str(mitgliedschaft.zuzug).replace(" ", "T") + "T00:00:00" if mitgliedschaft.zuzug else None,
        "neueSektionCode": str(get_sektion_code(mitgliedschaft.wegzug_zu)) if mitgliedschaft.wegzug_zu else None,
        "wegzugsdatum": str(mitgliedschaft.wegzug).replace(" ", "T") + "T00:00:00" if mitgliedschaft.wegzug else None,
        "kuendigungPer": str(mitgliedschaft.kuendigung).replace(" ", "T") + "T00:00:00" if mitgliedschaft.kuendigung else None,
        "jahrBezahltMitgliedschaft": mitgliedschaft.bezahltes_mitgliedschaftsjahr or 0,
        "betragBezahltMitgliedschaft": None, # ???
        "jahrBezahltHaftpflicht": mitgliedschaft.zahlung_hv, # TBD
        "betragBezahltHaftpflicht": None, # ???
        "naechstesJahrGeschuldet": True if mitgliedschaft.naechstes_jahr_geschuldet == 1 else False,
        "bemerkungen": str(mitgliedschaft.wichtig) if mitgliedschaft.wichtig else None,
        "anzahlZeitungen": int(mitgliedschaft.m_und_w),
        "zeitungAlsPdf": True if mitgliedschaft.m_und_w_pdf else False,
        "isKollektiv": True if int(mitgliedschaft.ist_kollektiv) == 1 else False,
        "isGeschenkmitgliedschaft": True if int(mitgliedschaft.ist_geschenkmitgliedschaft) == 1 else False,
        "isEinmaligeSchenkung": True if int(mitgliedschaft.ist_einmalige_schenkung) == 1 else False,
        "schenkerHasGeschenkunterlagen": True if int(mitgliedschaft.geschenkunterlagen_an_schenker) == 1 else False,
        "datumBezahltHaftpflicht": str(mitgliedschaft.datum_hv_zahlung).replace(" ", "T") + "T00:00:00" if mitgliedschaft.datum_hv_zahlung else None,
        "adressen": adressen,
        "onlineHaftpflicht": mitgliedschaft.online_haftpflicht if mitgliedschaft.online_haftpflicht and mitgliedschaft.online_haftpflicht != '' else None,
        "onlineGutschrift": mitgliedschaft.online_gutschrift if mitgliedschaft.online_gutschrift and mitgliedschaft.online_gutschrift != '' else None,
        "onlineBetrag": mitgliedschaft.online_betrag if mitgliedschaft.online_betrag and mitgliedschaft.online_betrag != '' else None,
        "datumOnlineVerbucht": mitgliedschaft.datum_online_verbucht if mitgliedschaft.datum_online_verbucht and mitgliedschaft.datum_online_verbucht != '' else None,
        "datumOnlineGutschrift": mitgliedschaft.datum_online_gutschrift if mitgliedschaft.datum_online_gutschrift and mitgliedschaft.datum_online_gutschrift != '' else None,
        "onlinePaymentMethod": mitgliedschaft.online_payment_method if mitgliedschaft.online_payment_method and mitgliedschaft.online_payment_method != '' else None,
        "onlinePaymentId": mitgliedschaft.online_payment_id if mitgliedschaft.online_payment_id and mitgliedschaft.online_payment_id != '' else None
    }
    
    return prepared_mvm

def get_adressen_for_sp(mitgliedschaft):
    adressen = []
    mitglied = {
        "typ": "Mitglied",
        "strasse": str(mitgliedschaft.strasse) if mitgliedschaft.strasse else None,
        "hausnummer": str(mitgliedschaft.nummer) if mitgliedschaft.nummer else None,
        "hausnummerZusatz": str(mitgliedschaft.nummer_zu) if mitgliedschaft.nummer_zu else None,
        "postleitzahl": str(mitgliedschaft.plz) if mitgliedschaft.plz else None,
        "ort": str(mitgliedschaft.ort) if mitgliedschaft.ort else None,
        "adresszusatz": str(mitgliedschaft.zusatz_adresse) if mitgliedschaft.zusatz_adresse else None,
        "postfach": True if mitgliedschaft.postfach else False,
        "postfachNummer": str(mitgliedschaft.postfach_nummer) if mitgliedschaft.postfach_nummer and mitgliedschaft.postfach else None,
        "fuerKorrespondenzGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
        "kontakte": [
            {
                "anrede": str(mitgliedschaft.anrede_c) if mitgliedschaft.anrede_c else "Unbekannt",
                "istHauptkontakt": True,
                "vorname": str(mitgliedschaft.vorname_1) if mitgliedschaft.vorname_1 else None,
                "nachname": str(mitgliedschaft.nachname_1) if mitgliedschaft.nachname_1 else None,
                "email": str(mitgliedschaft.e_mail_1) if mitgliedschaft.e_mail_1 and mitgliedschaft.e_mail_1 != "None" else None,
                "telefon": str(mitgliedschaft.tel_p_1) if mitgliedschaft.tel_p_1 else None,
                "mobile": str(mitgliedschaft.tel_m_1) if mitgliedschaft.tel_m_1 else None,
                "telefonGeschaeft": str(mitgliedschaft.tel_g_1) if mitgliedschaft.tel_g_1 else None,
                "firma": str(mitgliedschaft.firma) if mitgliedschaft.kundentyp == 'Unternehmen' else None,
                "firmaZusatz": str(mitgliedschaft.zusatz_firma) if mitgliedschaft.kundentyp == 'Unternehmen' else None
            }
        ]
    }
    
    if int(mitgliedschaft.hat_solidarmitglied) == 1:
        solidarmitglied = {
            "anrede": str(mitgliedschaft.anrede_2) if mitgliedschaft.anrede_2 else "Unbekannt",
            "istHauptkontakt": False,
            "vorname": str(mitgliedschaft.vorname_2) if mitgliedschaft.vorname_2 else None,
            "nachname": str(mitgliedschaft.nachname_2) if mitgliedschaft.nachname_2 else None,
            "email": str(mitgliedschaft.e_mail_2) if mitgliedschaft.e_mail_2 and mitgliedschaft.e_mail_2 != "None" else None,
            "telefon": str(mitgliedschaft.tel_p_2) if mitgliedschaft.tel_p_2 else None,
            "mobile": str(mitgliedschaft.tel_m_2) if mitgliedschaft.tel_m_2 else None,
            "telefonGeschaeft": str(mitgliedschaft.tel_g_2) if mitgliedschaft.tel_g_2 else None,
            "firma": '',
            "firmaZusatz": ''
        }
        mitglied['kontakte'].append(solidarmitglied)
    
    adressen.append(mitglied)
    
    if int(mitgliedschaft.abweichende_objektadresse) == 1:
        objekt = {
            "typ": "Objekt",
            "strasse": str(mitgliedschaft.objekt_strasse) if mitgliedschaft.objekt_strasse else None,
            "hausnummer": str(mitgliedschaft.objekt_hausnummer) if mitgliedschaft.objekt_hausnummer else None,
            "hausnummerZusatz": str(mitgliedschaft.objekt_nummer_zu) if mitgliedschaft.objekt_nummer_zu else None,
            "postleitzahl": str(mitgliedschaft.objekt_plz) if mitgliedschaft.objekt_plz else None,
            "ort": str(mitgliedschaft.objekt_ort) if mitgliedschaft.objekt_ort else None,
            "adresszusatz": str(mitgliedschaft.objekt_zusatz_adresse) if mitgliedschaft.objekt_zusatz_adresse else None,
            "postfach": False,
            "postfachNummer": "",
            "fuerKorrespondenzGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
            "kontakte": []
        }
        adressen.append(objekt)
    
    if int(mitgliedschaft.abweichende_rechnungsadresse) == 1:
        rechnung = {
            "typ": "Rechnung",
            "strasse": str(mitgliedschaft.rg_strasse) if mitgliedschaft.rg_strasse else None,
            "hausnummer": str(mitgliedschaft.rg_nummer) if mitgliedschaft.rg_nummer else None,
            "hausnummerZusatz": str(mitgliedschaft.rg_nummer_zu) if mitgliedschaft.rg_nummer_zu else None,
            "postleitzahl": str(mitgliedschaft.rg_plz) if mitgliedschaft.rg_plz else None,
            "ort": str(mitgliedschaft.rg_ort) if mitgliedschaft.rg_ort else None,
            "adresszusatz": str(mitgliedschaft.rg_zusatz_adresse) if mitgliedschaft.rg_zusatz_adresse else None,
            "postfach": True if mitgliedschaft.rg_postfach else False,
            "postfachNummer": str(mitgliedschaft.rg_postfach_nummer) if mitgliedschaft.rg_postfach_nummer else None,
            "fuerKorrespondenzGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
            "kontakte": []
        }
        
        if int(mitgliedschaft.unabhaengiger_debitor) == 1:
            rechnungskontakt = {
                "anrede": str(mitgliedschaft.rg_anrede) if mitgliedschaft.rg_anrede else "Unbekannt",
                "istHauptkontakt": True,
                "vorname": str(mitgliedschaft.rg_vorname) if mitgliedschaft.rg_vorname else None,
                "nachname": str(mitgliedschaft.rg_nachname) if mitgliedschaft.rg_nachname else None,
                "email": str(mitgliedschaft.rg_e_mail) if mitgliedschaft.rg_e_mail and mitgliedschaft.rg_e_mail != "None" else None,
                "telefon": str(mitgliedschaft.rg_tel_p) if mitgliedschaft.rg_tel_p else None,
                "mobile": str(mitgliedschaft.rg_tel_m) if mitgliedschaft.rg_tel_m else None,
                "telefonGeschaeft": str(mitgliedschaft.rg_tel_g) if mitgliedschaft.rg_tel_g else None,
                "firma": str(mitgliedschaft.rg_firma) if mitgliedschaft.rg_firma else None,
                "firmaZusatz": str(mitgliedschaft.rg_zusatz_firma) if mitgliedschaft.rg_zusatz_firma else None,
            }
            rechnung['kontakte'].append(rechnungskontakt)
        else:
            rechnungskontakt = {
                "anrede": str(mitgliedschaft.anrede_c) if mitgliedschaft.anrede_c else "Unbekannt",
                "istHauptkontakt": True,
                "vorname": str(mitgliedschaft.vorname_1) if mitgliedschaft.vorname_1 else None,
                "nachname": str(mitgliedschaft.nachname_1) if mitgliedschaft.nachname_1 else None,
                "email": str(mitgliedschaft.e_mail_1) if mitgliedschaft.e_mail_1 and mitgliedschaft.e_mail_1 != "None" else None,
                "telefon": str(mitgliedschaft.tel_p_1) if mitgliedschaft.tel_p_1 else None,
                "mobile": str(mitgliedschaft.tel_m_1) if mitgliedschaft.tel_m_1 else None,
                "telefonGeschaeft": str(mitgliedschaft.tel_g_1) if mitgliedschaft.tel_g_1 else None,
                "firma": str(mitgliedschaft.firma) if mitgliedschaft.kundentyp == 'Unternehmen' else None,
                "firmaZusatz": str(mitgliedschaft.zusatz_firma) if mitgliedschaft.kundentyp == 'Unternehmen' else None
            }
            rechnung['kontakte'].append(rechnungskontakt)
        
        adressen.append(rechnung)
    
    return adressen

def get_sprache(language='de'):
    language = frappe.db.sql("""SELECT `language_name` FROM `tabLanguage` WHERE `name` = '{language}'""".format(language=language), as_list=True)
    if len(language) > 0:
        return language[0][0]
    else:
        return 'Deutsch'

# /API
# -----------------------------------------------

# Hooks functions
# -----------------------------------------------
def sinv_check_zahlung_mitgliedschaft(sinv, event):
    # mitgliedschaft speichern um SP Update zu triggern und höchste Mahnstufe zu setzen
    if sinv.mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", sinv.mv_mitgliedschaft)
        try:
            sql_query = ("""SELECT MAX(`payment_reminder_level`) AS `max` FROM `tabSales Invoice` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}' AND `status` = 'Overdue'""".format(mitgliedschaft=mitgliedschaft.name))
            max_level = frappe.db.sql(sql_query, as_dict=True)[0]['max']
            if not max_level:
                max_level = 0
        except:
            max_level = 0
        sinv_max_level = int(sinv.payment_reminder_level or 0)
        if max_level < sinv_max_level:
            max_level = sinv_max_level
        mitgliedschaft.max_reminder_level = max_level
        mitgliedschaft.save(ignore_permissions=True)

def pe_check_zahlung_mitgliedschaft(pe, event):
    for ref in pe.references:
        if ref.reference_doctype == 'Sales Invoice':
            sinv = frappe.get_doc("Sales Invoice", ref.reference_name)
            if sinv.mv_mitgliedschaft:
                mitgliedschaft = frappe.get_doc("Mitgliedschaft", sinv.mv_mitgliedschaft)
                mitgliedschaft.save(ignore_permissions=True)

# -----------------------------------------------
# other helpers
# -----------------------------------------------
@frappe.whitelist()
def get_sektions_code(company):
    if company:
        sektion = frappe.db.sql("""SELECT `sektion_id` FROM `tabSektion` WHERE `company` = '{company}' LIMIT 1""".format(company=company), as_dict=True)
        if len(sektion) > 0:
            return str(sektion[0].sektion_id)
        else:
            return '00'
    else:
        return '00'

@frappe.whitelist()
def get_sektionen_zur_auswahl():
    sektionen = frappe.db.sql("""SELECT `name` FROM `tabSektion` ORDER BY `name` ASC""", as_dict=True)
    sektionen_zur_auswahl = ''
    for sektion in sektionen:
        sektionen_zur_auswahl += "\n" + sektion.name
    return sektionen_zur_auswahl

def get_ampelfarbe(mitgliedschaft):
    ''' mögliche Ampelfarben:
        - Grün: ampelgruen --> Mitglied kann alle Dienstleistungen beziehen (keine Karenzfristen, keine überfälligen oder offen Rechnungen)
        - Gelb: ampelgelb --> Karenzfristen oder offene Rechnungen
        - Rot: ampelrot --> überfällige offene Rechnungen
    '''
    
    if mitgliedschaft.status_c in ('Gestorben', 'Wegzug', 'Ausschluss', 'Inaktiv', 'Interessent*in'):
        ampelfarbe = 'ampelrot'
    else:
        rechnungs_kunde = mitgliedschaft.kunde_mitglied
        if mitgliedschaft.rg_kunde:
            rechnungs_kunde = mitgliedschaft.rg_kunde
        
        ueberfaellige_rechnungen = 0
        offene_rechnungen = 0
        
        sektion = frappe.get_doc("Sektion", mitgliedschaft.sektion_id)
        karenzfrist_in_d = sektion.karenzfrist
        ablauf_karenzfrist = add_days(getdate(mitgliedschaft.eintrittsdatum), karenzfrist_in_d)
        
        if getdate() < ablauf_karenzfrist:
            karenzfrist = False
        else:
            karenzfrist = True
        
        ueberfaellige_rechnungen = frappe.db.sql("""SELECT IFNULL(SUM(`outstanding_amount`), 0) AS `open_amount`
                                                    FROM `tabSales Invoice` 
                                                    WHERE `customer` = '{rechnungs_kunde}'
                                                    AND `due_date` < CURDATE()
                                                    AND `docstatus` = 1""".format(rechnungs_kunde=rechnungs_kunde), as_dict=True)[0].open_amount
        
        if ueberfaellige_rechnungen > 0:
            ampelfarbe = 'ampelrot'
        else:
            offene_rechnungen = frappe.db.sql("""SELECT IFNULL(SUM(`outstanding_amount`), 0) AS `open_amount`
                                                FROM `tabSales Invoice` 
                                                WHERE `customer` = '{rechnungs_kunde}'
                                                AND `due_date` >= CURDATE()
                                                AND `docstatus` = 1""".format(rechnungs_kunde=rechnungs_kunde), as_dict=True)[0].open_amount
            
            if offene_rechnungen > 0:
                ampelfarbe = 'ampelgelb'
            else:
                if not karenzfrist:
                    ampelfarbe = 'ampelgelb'
                else:
                    ampelfarbe = 'ampelgruen'
    
    return ampelfarbe

@frappe.whitelist()
def create_korrespondenz(mitgliedschaft, titel, druckvorlage=False, massenlauf=False):
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    if druckvorlage == 'keine':
        new_korrespondenz = frappe.get_doc({
            "doctype": "Korrespondenz",
            "mv_mitgliedschaft": mitgliedschaft.name,
            "sektion_id": mitgliedschaft.sektion_id,
            "titel": titel
        })
        new_korrespondenz.insert(ignore_permissions=True)
        frappe.db.commit()
        return new_korrespondenz.name
    else:
        druckvorlage = frappe.get_doc("Druckvorlage", druckvorlage)
        _new_korrespondenz = frappe.copy_doc(druckvorlage)
        _new_korrespondenz.doctype = 'Korrespondenz'
        _new_korrespondenz.sektion_id = mitgliedschaft.sektion_id
        _new_korrespondenz.titel = titel
        
        new_korrespondenz = frappe._dict(_new_korrespondenz.as_dict())
        
        keys_to_remove = [
            'mitgliedtyp_c',
            'validierungsstring',
            'language',
            'reduzierte_mitgliedschaft',
            'dokument',
            'default',
            'deaktiviert',
            'seite_1_qrr',
            'seite_1_qrr_spende_hv',
            'seite_2_qrr',
            'seite_2_qrr_spende_hv',
            'seite_3_qrr',
            'seite_3_qrr_spende_hv',
            'blatt_2_info_mahnung',
            'tipps_mahnung',
            'geschenkmitgliedschaft_dok_empfaenger',
            'tipps_geschenkmitgliedschaft'
        ]
        for key in keys_to_remove:
            try:
                new_korrespondenz.pop(key)
            except:
                pass
        
        new_korrespondenz['mv_mitgliedschaft'] = mitgliedschaft.name
        new_korrespondenz['massenlauf'] = 1 if massenlauf else 0
        
        new_korrespondenz = frappe.get_doc(new_korrespondenz)
        new_korrespondenz.insert(ignore_permissions=True)
        frappe.db.commit()
        return new_korrespondenz.name

@frappe.whitelist()
def create_geschenk_korrespondenz(mitgliedschaft, druckvorlage_inhaber=False, druckvorlage_zahler=False, massenlauf=False):
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    
    druckvorlage = frappe.get_doc("Druckvorlage", druckvorlage_inhaber)
    _new_korrespondenz = frappe.copy_doc(druckvorlage)
    _new_korrespondenz.doctype = 'Korrespondenz'
    _new_korrespondenz.sektion_id = mitgliedschaft.sektion_id
    _new_korrespondenz.titel = 'Geschenkmitgliedschaft Beschenkte*r'
    
    new_korrespondenz = frappe._dict(_new_korrespondenz.as_dict())
    
    keys_to_remove = [
        'mitgliedtyp_c',
        'validierungsstring',
        'language',
        'reduzierte_mitgliedschaft',
        'dokument',
        'default',
        'deaktiviert',
        'seite_1_qrr',
        'seite_1_qrr_spende_hv',
        'seite_2_qrr',
        'seite_2_qrr_spende_hv',
        'seite_3_qrr',
        'seite_3_qrr_spende_hv',
        'blatt_2_info_mahnung',
        'tipps_mahnung',
        'geschenkmitgliedschaft_dok_empfaenger',
        'tipps_geschenkmitgliedschaft'
    ]
    for key in keys_to_remove:
        try:
            new_korrespondenz.pop(key)
        except:
            pass
    
    new_korrespondenz['mv_mitgliedschaft'] = mitgliedschaft.name
    new_korrespondenz['massenlauf'] = 1 if massenlauf else 0
    
    new_korrespondenz = frappe.get_doc(new_korrespondenz)
    new_korrespondenz.insert(ignore_permissions=True)
    frappe.db.commit()
    
    inhaber = new_korrespondenz.name
    zahler = None
    
    if druckvorlage_zahler:
        druckvorlage = frappe.get_doc("Druckvorlage", druckvorlage_zahler)
        _new_korrespondenz = frappe.copy_doc(druckvorlage)
        _new_korrespondenz.doctype = 'Korrespondenz'
        _new_korrespondenz.sektion_id = mitgliedschaft.sektion_id
        _new_korrespondenz.titel = 'Geschenkmitgliedschaft Schenkende*r'
        
        new_korrespondenz = frappe._dict(_new_korrespondenz.as_dict())
        
        keys_to_remove = [
            'mitgliedtyp_c',
            'validierungsstring',
            'language',
            'reduzierte_mitgliedschaft',
            'dokument',
            'default',
            'deaktiviert',
            'seite_1_qrr',
            'seite_1_qrr_spende_hv',
            'seite_2_qrr',
            'seite_2_qrr_spende_hv',
            'seite_3_qrr',
            'seite_3_qrr_spende_hv',
            'blatt_2_info_mahnung',
            'tipps_mahnung',
            'geschenkmitgliedschaft_dok_empfaenger',
            'tipps_geschenkmitgliedschaft'
        ]
        for key in keys_to_remove:
            try:
                new_korrespondenz.pop(key)
            except:
                pass
        
        new_korrespondenz['mv_mitgliedschaft'] = mitgliedschaft.name
        new_korrespondenz['massenlauf'] = 1 if massenlauf else 0
        
        new_korrespondenz = frappe.get_doc(new_korrespondenz)
        new_korrespondenz.geschenk = 1
        new_korrespondenz.insert(ignore_permissions=True)
        frappe.db.commit()
        
        zahler = new_korrespondenz.name
    
    output = PdfFileWriter()
    if druckvorlage_zahler:
        output = frappe.get_print("Korrespondenz", zahler, 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
    output = frappe.get_print("Korrespondenz", inhaber, 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
    
    file_name = "Geschenk_Korrespondenz_{datetime}".format(datetime=now().replace(" ", "_"))
    file_name = file_name.split(".")[0]
    file_name = file_name.replace(":", "-")
    file_name = file_name + ".pdf"
    
    filedata = get_file_data_from_writer(output)
    
    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "folder": "Home/Attachments",
        "is_private": 1,
        "content": filedata,
        "attached_to_doctype": 'Mitgliedschaft',
        "attached_to_name": mitgliedschaft.name
    })
    
    _file.save(ignore_permissions=True)
        
    return {'inhaber': inhaber, 'zahler': zahler}

@frappe.whitelist()
def create_korrespondenz_massenlauf(mitgliedschaften, druckvorlage, titel):
    if isinstance(mitgliedschaften, str):
        mitgliedschaften = json.loads(mitgliedschaften)
    
    for mitgliedschaft in mitgliedschaften:
        create_korrespondenz(mitgliedschaft["name"], titel, druckvorlage, massenlauf=True)
    return

@frappe.whitelist()
def erstelle_todo(owner, mitglied, description=False, datum=False, notify=0):
    todo = frappe.get_doc({
        "doctype":"ToDo",
        "owner": owner,
        "reference_type": "Mitgliedschaft",
        "reference_name": mitglied,
        "description": description or '',
        "priority": "Medium",
        "status": "Open",
        "date": datum or '',
        "assigned_by": frappe.session.user,
        "mv_mitgliedschaft": mitglied
    }).insert(ignore_permissions=True)
    return

@frappe.whitelist()
def wieder_beitritt(mitgliedschaft):
    alte_mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    mitgliedschafts_copy = frappe.copy_doc(alte_mitgliedschaft.as_dict())
    
    mitgliedschafts_copy.mitglied_nr = None
    mitgliedschafts_copy.mitglied_id = None
    mitgliedschafts_copy.status_c = 'Anmeldung'
    mitgliedschafts_copy.eintrittsdatum = today()
    mitgliedschafts_copy.zuzug = None
    mitgliedschafts_copy.zuzug_von = None
    mitgliedschafts_copy.wegzug = None
    mitgliedschafts_copy.wegzug_zu = None
    mitgliedschafts_copy.austritt = None
    mitgliedschafts_copy.kuendigung = None
    mitgliedschafts_copy.bezahltes_mitgliedschaftsjahr = 0
    mitgliedschafts_copy.zahlung_hv = 0
    mitgliedschafts_copy.zahlung_mitgliedschaft = 0
    mitgliedschafts_copy.naechstes_jahr_geschuldet = 1
    mitgliedschafts_copy.datum_hv_zahlung = None
    mitgliedschafts_copy.letzte_bearbeitung_von = 'SP'
    mitgliedschafts_copy.online_haftpflicht = None
    mitgliedschafts_copy.online_gutschrift = None
    mitgliedschafts_copy.online_betrag = None
    mitgliedschafts_copy.datum_online_verbucht = None
    mitgliedschafts_copy.datum_online_gutschrift = None
    mitgliedschafts_copy.online_payment_method = None
    mitgliedschafts_copy.online_payment_id = None
    mitgliedschafts_copy.anmeldung_mit_ez = 1
    mitgliedschafts_copy.validierung_notwendig = 1
    mitgliedschafts_copy.kuendigung_verarbeiten = 0
    mitgliedschafts_copy.interessent_innenbrief_mit_ez = 0
    mitgliedschafts_copy.zuzug_massendruck = 0
    mitgliedschafts_copy.zuzugs_rechnung = None
    mitgliedschafts_copy.zuzug_korrespondenz = None
    mitgliedschafts_copy.kuendigung_druckvorlage = None
    mitgliedschafts_copy.rg_massendruck_vormerkung = 0
    mitgliedschafts_copy.begruessung_massendruck = 0
    mitgliedschafts_copy.begruessung_via_zahlung = 0
    mitgliedschafts_copy.begruessung_massendruck_dokument = None
    
    mitgliedschafts_copy.insert()
    frappe.db.commit()
    
    mitgliedschafts_copy.validierung_notwendig = 0
    mitgliedschafts_copy.save()
    
    alte_mitgliedschaft.add_comment('Comment', text='Mitgliedschaft (als Anmeldung) mittels {0} ({1}) reaktiviert.'.format(mitgliedschafts_copy.mitglied_nr, mitgliedschafts_copy.name))
    mitgliedschafts_copy.add_comment('Comment', text='Reaktivierte Mitgliedschaft aus {0} ({1})'.format(alte_mitgliedschaft.mitglied_nr, alte_mitgliedschaft.name))
    
    return mitgliedschafts_copy.name

@frappe.whitelist()
def check_erstelle_rechnung(mitgliedschaft, typ, sektion):
    jahr = int(getdate(today()).strftime("%Y"))
    if typ == 'Privat':
        gratis_bis_ende_jahr = frappe.get_value("Sektion", sektion, "gratis_bis_ende_jahr")
        gratis_ab = getdate(getdate(today()).strftime("%Y") + "-" + getdate(gratis_bis_ende_jahr).strftime("%m") + "-" + getdate(gratis_bis_ende_jahr).strftime("%d"))
        if getdate(today()) >= gratis_ab:
            jahr += 1
                    
    vorhandene_rechnungen = frappe.db.sql("""SELECT
                                                COUNT(`name`) AS `qty`
                                            FROM `tabSales Invoice`
                                            WHERE `docstatus` = 1
                                            AND `ist_mitgliedschaftsrechnung` = 1
                                            AND `mv_mitgliedschaft` = '{mitgliedschaft}'
                                            AND `mitgliedschafts_jahr` = '{jahr}'""".format(mitgliedschaft=mitgliedschaft, jahr=jahr), as_dict=True)[0].qty
    if vorhandene_rechnungen < 1:
        return 1
    else:
        return 0

def create_sp_log(mitgliedschaft, neuanlage, kwargs):
    if neuanlage:
        neuanlage = 1
        update = 0
    else:
        neuanlage = 0
        update = 1
    
    sp_log = frappe.get_doc({
        "doctype":"Service Plattform Log",
        "mv_mitgliedschaft": mitgliedschaft,
        "json": str(kwargs),
        "neuanlage": neuanlage,
        "update": update
    }).insert(ignore_permissions=True)
    
    return
