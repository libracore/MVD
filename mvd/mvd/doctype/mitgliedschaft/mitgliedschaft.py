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
from mvd.mvd.doctype.druckvorlage.druckvorlage import get_druckvorlagen, replace_mv_keywords
from frappe import _
import datetime
from frappe.utils import cint

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
            if cint(self.postfach) == 1 and self.strasse == 'Postfach':
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
            
            # Prüfe Jahr Bezahlt (Mitgliedschaft & HV) bezgl. Folgejahr Regelung
            if self.status_c != 'Inaktiv':
                self.check_folgejahr_regelung()
            
            # preisregel
            self.check_preisregel()
            
            # ampelfarbe
            self.ampel_farbe = get_ampelfarbe(self)

            # prüfen und setzen des Wertes naechstes_jahr_geschuldet
            self.naechstes_jahr_geschuldet = cint(get_naechstes_jahr_geschuldet(self.name, live_data=self))
            
            # Hotfix Zuzugs-Korrespondenz
            if self.zuzug_von:
                # mit Massenlauf-Vormerkung
                if self.zuzug_massendruck:
                    if cint(self.zuzug_massendruck) == 1:
                        if not self.zuzugs_rechnung and not self.zuzug_korrespondenz:
                            if self.kunde_mitglied:
                                self.zuzug_massenlauf_korrespondenz()
                                self.zuzug_durch_sp = 0
                # ohne Massenlauf-Vormerkung
                elif self.zuzug_durch_sp:
                    if cint(self.zuzug_durch_sp) == 1:
                        if self.kunde_mitglied:
                            self.zuzug_massenlauf_korrespondenz()
                            self.zuzug_durch_sp = 0
            
            # setze CB "Aktive Mitgliedschaft"
            if self.status_c not in ('Gestorben', 'Wegzug', 'Ausschluss', 'Inaktiv'):
                self.aktive_mitgliedschaft = 1
            else:
                self.aktive_mitgliedschaft = 0
            
            # schliesse offene abreits backlogs
            close_open_validations(self.name, 'Daten Validieren')
            if not cint(self.interessent_innenbrief_mit_ez) == 1:
                    close_open_validations(self.name, 'Interessent*Innenbrief mit EZ')
            if not cint(self.anmeldung_mit_ez) == 1:
                    close_open_validations(self.name, 'Anmeldung mit EZ')
            
            # beziehe mitglied_nr wenn umwandlung von Interessent*in
            if self.status_c not in ('Interessent*in', 'Inaktiv') and self.mitglied_nr == 'MV':
                self.mitglied_nr = mvm_mitglieder_nummer_update(self.name)
                self.letzte_bearbeitung_von = 'User'
            
            # hotfix für onlineHaftpflicht value (null vs 0)
            if not self.online_haftpflicht:
                self.online_haftpflicht = '0'
            
            # Regions-Zuordnung anhand PLZ
            if not cint(self.region_manuell) == 1:
                self.region = self.get_region()
        
            # Mahnstopp in Rechnungen setzen
            if self.status_c in ('Gestorben', 'Ausschluss'):
                self.mahnstopp = '2099-12-31'
            
            if self.mahnstopp:
                mahnstopp(self.name, self.mahnstopp)
            
            # Anzahl M+W Update anhand Retouren in Folge
            if self.retoure_in_folge and self.m_und_w > 0:
                self.m_und_w = 0
            
            # halte ggf. Faktura Kunde synchron
            self.check_faktura_kunde()
            
            # sende neuanlage/update an sp wenn letzter bearbeiter nich SP
            if self.letzte_bearbeitung_von == 'User':
                if self.creation == self.modified:
                    # sende neuanlage an SP
                    send_mvm_to_sp(self, False)
                else:
                    # sende update an SP
                    send_mvm_to_sp(self, True)
                    # special case sektionswechsel nach ZH
                    if self.wegzug_zu == 'MVZH' and self.status_c == 'Wegzug':
                        send_mvm_sektionswechsel(self)
    
    def email_validierung(self, check=False):
        import re
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_felder = ['e_mail_1', 'e_mail_2', 'rg_e_mail']
        failed_mails = []
        for email_feld in email_felder:
            email = self.get(email_feld)
            if email:
                if(re.fullmatch(regex, email)):
                    # all good
                    pass
                else:
                    if not check:
                        self.add_comment('Comment', text='Die E-Mail-Adresse {0} musste entfernt werden, da sie als ungültig erkannt wurde.'.format(email))
                        self.set(email_feld, None)
                    else:
                        failed_mails.append(email)
        if len(failed_mails) > 0:
            return ", ".join(failed_mails)
        else:
            return 1
    
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
    
    def get_region(self):
        plz = ''.join(filter(str.isdigit, self.plz)) # remove characters except digits (e.g.: 'D-12345' -> '12345')
        region = frappe.db.sql("""SELECT
                                    `parent`
                                FROM `tabRegion PLZ`
                                WHERE `plz_von` <= {plz}
                                AND `plz_bis` >= {plz}
                                AND `parent` IN (
                                    SELECT
                                        `name`
                                    FROM `tabRegion`
                                    WHERE `sektion_id` = '{sektion}'
                                ) LIMIT 1""".format(plz=plz, sektion=self.sektion_id), as_dict=True)
        if len(region) > 0:
            return region[0].parent
        else:
            return None

    def zuzug_massenlauf_korrespondenz(self):
        # erstelle ggf. neue Rechnung
        mit_rechnung = False
        if self.bezahltes_mitgliedschaftsjahr < cint(now().split("-")[0]):
            if self.naechstes_jahr_geschuldet == 1:
                mit_rechnung = create_mitgliedschaftsrechnung(self.name, mitgliedschaft_obj=self, jahr=cint(now().split("-")[0]), submit=True, attach_as_pdf=True, druckvorlage=get_druckvorlagen(sektion=self.sektion_id, dokument='Zuzug mit EZ', mitgliedtyp=self.mitgliedtyp_c, reduzierte_mitgliedschaft=self.reduzierte_mitgliedschaft, language=self.language)['default_druckvorlage'])
        
        
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
        if cint(self.reduzierte_mitgliedschaft) == 1:
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
        if cint(qty) > 0:
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
            sinv_year = cint(sinv.mitgliedschafts_jahr)
            if sinv.is_pos == 1:
                # Fallback wenn sinv.mitgliedschafts_jahr == 0
                if sinv_year < 1:
                    sinv_year = getdate(sinv.posting_date).strftime("%Y")
                self.datum_zahlung_mitgliedschaft = sinv.posting_date
            else:
                pes = frappe.db.sql("""SELECT `parent` FROM `tabPayment Entry Reference`
                                        WHERE `reference_doctype` = 'Sales Invoice'
                                        AND `reference_name` = '{sinv}' ORDER BY `creation` DESC""".format(sinv=sinv.name), as_dict=True)
                if len(pes) > 0:
                    pe = frappe.get_doc("Payment Entry", pes[0].parent)
                    # Fallback wenn sinv.mitgliedschafts_jahr == 0
                    if sinv_year < 1:
                        sinv_year = getdate(pe.reference_date).strftime("%Y")
                    self.datum_zahlung_mitgliedschaft = pe.reference_date
            
            if self.bezahltes_mitgliedschaftsjahr < sinv_year:
                self.bezahltes_mitgliedschaftsjahr = sinv_year
        
        # Zahldatum = Eintrittsdatum
        if self.status_c in ('Anmeldung', 'Online-Anmeldung', 'Interessent*in') and self.bezahltes_mitgliedschaftsjahr > 0:
            if noch_kein_eintritt:
                self.eintrittsdatum = self.datum_zahlung_mitgliedschaft
        
        if self.bezahltes_mitgliedschaftsjahr > 0 and self.status_c in ('Anmeldung', 'Online-Anmeldung', 'Interessent*in'):
            # erstelle status change log und Status-Änderung
            change_log_row = self.append('status_change', {})
            change_log_row.datum = now()
            change_log_row.status_alt = self.status_c
            change_log_row.status_neu = 'Regulär'
            change_log_row.grund = 'Zahlungseingang'
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
                            if fr.status == 'Paid':
                                fr.add_comment('Comment', text="Verknüpfung zu Rechnung {0} aufgrund Sektionswechsel aufgehoben".format(fr.sales_invoice))
                                frappe.db.sql("""UPDATE `tabFakultative Rechnung` SET `sales_invoice` = '' WHERE `name` = '{0}'""".format(fr.name), as_list=True)
                            else:
                                fr.cancel()
                    
                    # cancel linked mahnungen
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
                                    `posting_date`,
                                    `mitgliedschafts_jahr`
                                FROM `tabSales Invoice`
                                WHERE `docstatus` = 1
                                AND `ist_hv_rechnung` = 1
                                AND `mv_mitgliedschaft` = '{mvm}'
                                AND `status` = 'Paid'
                                ORDER BY `posting_date` DESC""".format(mvm=self.name), as_dict=True)
        if len(sinvs) > 0:
            sinv = sinvs[0]
            if sinv.is_pos == 1:
                sinv_year = sinv.mitgliedschafts_jahr if sinv.mitgliedschafts_jahr and sinv.mitgliedschafts_jahr > 0 else getdate(sinv.posting_date).strftime("%Y")
                self.datum_hv_zahlung = sinv.posting_date
            else:
                pes = frappe.db.sql("""SELECT `parent` FROM `tabPayment Entry Reference`
                                        WHERE `reference_doctype` = 'Sales Invoice'
                                        AND `reference_name` = '{sinv}' ORDER BY `creation` DESC""".format(sinv=sinv.name), as_dict=True)
                if len(pes) > 0:
                    pe = frappe.get_doc("Payment Entry", pes[0].parent)
                    sinv_year = sinv.mitgliedschafts_jahr if sinv.mitgliedschafts_jahr and sinv.mitgliedschafts_jahr > 0 else getdate(pe.reference_date).strftime("%Y")
                    self.datum_hv_zahlung = pe.reference_date
            self.zahlung_hv = sinv_year
        
        return
    
    def check_folgejahr_regelung(self):
        # prüfe ob Folgejahr Regelung der Sektion aktiviert ist:
        if cint(frappe.get_value("Sektion", self.sektion_id, "folgejahr_regelung")) == 1:
            if self.datum_zahlung_mitgliedschaft:
            # prüfe Mitgliedschaftsjahr
                datum_zahlung_mitgliedschaft = getdate(self.datum_zahlung_mitgliedschaft)
                jahr_datum_zahlung_mitgliedschaft = cint(datum_zahlung_mitgliedschaft.strftime("%Y"))
                bezahltes_mitgliedschaftsjahr = cint(self.bezahltes_mitgliedschaftsjahr)
                
                if bezahltes_mitgliedschaftsjahr == jahr_datum_zahlung_mitgliedschaft:
                    current_year = str(now().split("-")[0])
                    eintrittsjahr = cint(getdate(self.eintrittsdatum).strftime("%Y"))
                    if cint(current_year) == eintrittsjahr:
                        if datum_zahlung_mitgliedschaft >= getdate(current_year + '-09-15') and datum_zahlung_mitgliedschaft <= getdate(current_year + '-12-31'):
                            self.bezahltes_mitgliedschaftsjahr += 1
            
            if self.datum_hv_zahlung:
                # prüfe HV-Jahr
                datum_hv_zahlung = getdate(self.datum_hv_zahlung)
                jahr_datum_hv_zahlung = cint(datum_hv_zahlung.strftime("%Y"))
                zahlung_hv = cint(self.zahlung_hv)
                
                current_year = str(now().split("-")[0])
                eintrittsjahr = cint(getdate(self.eintrittsdatum).strftime("%Y"))
                if cint(current_year) == eintrittsjahr:
                    if zahlung_hv == jahr_datum_hv_zahlung:
                        current_year = str(now().split("-")[0])
                        if datum_hv_zahlung >= getdate(current_year + '-09-15') and datum_hv_zahlung <= getdate(current_year + '-12-31'):
                            self.zahlung_hv += 1
        
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
    
    def check_faktura_kunde(self):
        from mvd.mvd.doctype.kunden.kunden import update_faktura_kunde
        faktura = frappe.db.sql("""SELECT `name` FROM `tabKunden` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}' AND `daten_aus_mitgliedschaft` = 1""".format(mitgliedschaft=self.name), as_dict=True)
        if len(faktura) > 0:
            update_faktura_kunde(mitgliedschaft=self, kunde=faktura[0].name)

def mahnstopp(mitgliedschaft, mahnstopp):
    SQL_SAFE_UPDATES_false = frappe.db.sql("""SET SQL_SAFE_UPDATES=0""", as_list=True)
    frappe.db.sql("""UPDATE `tabSales Invoice` SET `exclude_from_payment_reminder_until` = '{mahnstopp}' WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'""".format(mitgliedschaft=mitgliedschaft, mahnstopp=mahnstopp), as_list=True)
    SQL_SAFE_UPDATES_true = frappe.db.sql("""SET SQL_SAFE_UPDATES=1""", as_list=True)
    frappe.db.commit()

def get_adressblock(mitgliedschaft):
    adressblock = ''
    
    if mitgliedschaft.doctype == 'Mitgliedschaft':
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
        
        if mitgliedschaft.strasse and mitgliedschaft.strasse != '':
            adressblock += mitgliedschaft.strasse
            if mitgliedschaft.nummer:
                adressblock += ' '
                adressblock += str(mitgliedschaft.nummer) or ''
                if mitgliedschaft.nummer_zu:
                    adressblock += str(mitgliedschaft.nummer_zu) or ''
            adressblock += '\n'
        
        if cint(mitgliedschaft.postfach) == 1:
            adressblock += 'Postfach '
            adressblock += str(mitgliedschaft.postfach_nummer) or ''
            adressblock += '\n'
        
        if mitgliedschaft.land and mitgliedschaft.land != 'Schweiz':
            laender_code = frappe.get_value("Country", mitgliedschaft.land, "code").upper() + "-"
        else:
            laender_code = ''
        adressblock += laender_code + str(mitgliedschaft.plz) or ''
        adressblock += ' '
        adressblock += mitgliedschaft.ort or ''
        
        return adressblock
    else:
        if mitgliedschaft.kundentyp == 'Unternehmen':
            if mitgliedschaft.firma:
                adressblock += mitgliedschaft.firma or ''
                adressblock += ' '
            if mitgliedschaft.zusatz_firma:
                adressblock += mitgliedschaft.zusatz_firma or ''
            if mitgliedschaft.firma or mitgliedschaft.zusatz_firma:
                adressblock += '\n'
        
        if mitgliedschaft.vorname:
            adressblock += mitgliedschaft.vorname or ''
            adressblock += ' '
        adressblock += mitgliedschaft.nachname or ''
        adressblock += '\n'
        
        if mitgliedschaft.zusatz_adresse:
            adressblock += mitgliedschaft.zusatz_adresse or ''
            adressblock += '\n'
        
        if mitgliedschaft.strasse and mitgliedschaft.strasse != '':
            adressblock += mitgliedschaft.strasse
            if mitgliedschaft.nummer:
                adressblock += ' '
                adressblock += str(mitgliedschaft.nummer) or ''
                if mitgliedschaft.nummer_zu:
                    adressblock += str(mitgliedschaft.nummer_zu) or ''
            adressblock += '\n'
        
        if cint(mitgliedschaft.postfach) == 1:
            adressblock += 'Postfach '
            adressblock += str(mitgliedschaft.postfach_nummer) or ''
            adressblock += '\n'
        
        if mitgliedschaft.land and mitgliedschaft.land != 'Schweiz':
            laender_code = frappe.get_value("Country", mitgliedschaft.land, "code").upper() + "-"
        else:
            laender_code = ''
        adressblock += laender_code + str(mitgliedschaft.plz) or ''
        adressblock += ' '
        adressblock += mitgliedschaft.ort or ''
        
        return adressblock

def get_rg_adressblock(mitgliedschaft):
    adressblock = ''
    if mitgliedschaft.doctype == 'Mitgliedschaft':
        if cint(mitgliedschaft.abweichende_rechnungsadresse) != 1:
            return get_adressblock(mitgliedschaft)
        
        if cint(mitgliedschaft.unabhaengiger_debitor) != 1:
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
        
        if cint(mitgliedschaft.rg_postfach) == 1:
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
    elif mitgliedschaft.doctype == 'Kunden':
        if cint(mitgliedschaft.abweichende_rechnungsadresse) != 1:
            return get_adressblock(mitgliedschaft)
        
        if cint(mitgliedschaft.unabhaengiger_debitor) != 1:
            if mitgliedschaft.kundentyp == 'Unternehmen':
                if mitgliedschaft.firma:
                    adressblock += mitgliedschaft.firma or ''
                    adressblock += ' '
                if mitgliedschaft.zusatz_firma:
                    adressblock += mitgliedschaft.zusatz_firma or ''
                if mitgliedschaft.firma or mitgliedschaft.zusatz_firma:
                    adressblock += '\n'
            
            if mitgliedschaft.vorname:
                adressblock += mitgliedschaft.vorname or ''
                adressblock += ' '
            adressblock += mitgliedschaft.nachname or ''
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
        
        if cint(mitgliedschaft.rg_postfach) == 1:
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
    else:
        return 'Fehler!<br>Weder Mitgliedschaft noch Kunde'
    
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
    if mitgliedschaft.status_c == 'Interessent*in':
        customer.customer_group = 'Interessent*in'
    else:
        customer.customer_group = 'Mitglied'
    
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
    
    if mitgliedschaft.status_c == 'Interessent*in':
        customer_group = 'Interessent*in'
    else:
        customer_group = 'Mitglied'
    
    new_customer = frappe.get_doc({
        'doctype': 'Customer',
        'customer_name': customer_name,
        'customer_addition': customer_addition,
        'customer_type': customer_type,
        'sektion': mitgliedschaft.sektion_id,
        'customer_group': customer_group,
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
    if mitgliedschaft.status_c == 'Interessent*in':
        customer_group = 'Interessent*in'
    else:
        customer_group = 'Mitglied'
    
    # fallback wrong import data
    if customer.customer_name == ' ' and mitgliedschaft.firma:
        customer.customer_name = mitgliedschaft.firma
        customer.customer_addition = mitgliedschaft.zusatz_firma
        customer.customer_type = 'Company'
        frappe.log_error("{0}\n---\n{1}".format('fallback: customer_name was " "', mitgliedschaft.as_json()), 'update_kunde_mitglied')
    
    customer.save(ignore_permissions=True)
    frappe.db.set_value("Customer", customer.name, "customer_group", customer_group)
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
    if mitgliedschaft.status_c == 'Interessent*in':
        customer_group = 'Interessent*in'
    else:
        customer_group = 'Mitglied'
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
        'customer_group': customer_group,
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
                                                    WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'
                                                    AND `due_date` < CURDATE()
                                                    AND `docstatus` = 1
                                                    AND `sektion_id` = '{sektion}'""".format(mitgliedschaft=mitgliedschaft.name, sektion=mitgliedschaft.sektion_id), as_dict=True)[0].open_amount
        
        offene_rechnungen = frappe.db.sql("""SELECT IFNULL(SUM(`outstanding_amount`), 0) AS `open_amount`
                                            FROM `tabSales Invoice` 
                                            WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'
                                            AND `due_date` >= CURDATE()
                                            AND `docstatus` = 1
                                            AND `sektion_id` = '{sektion}'""".format(mitgliedschaft=mitgliedschaft.name, sektion=mitgliedschaft.sektion_id), as_dict=True)[0].open_amount
        
        if mitgliedschaft.status_c not in ('Anmeldung', 'Online-Anmeldung', 'Interessent*in'):
            eintritt = mitgliedschaft.eintrittsdatum
        else:
            eintritt = mitgliedschaft.eintritt if mitgliedschaft.eintritt else mitgliedschaft.creation
        
        # Anzeigen von Pseudo-Status "Inaktiv (verstorben)" wenn verstorben und Inaktiv
        if mitgliedschaft.verstorben_am and mitgliedschaft.status_c == 'Inaktiv':
            status = "Inaktiv (verstorben)"
        else:
            status = mitgliedschaft.status_c

        haftpflicht = False
        if len(mitgliedschaft.haftpflicht) > 0:
            haftpflicht = []
            for hv in mitgliedschaft.haftpflicht:
                haftpflicht.append(hv.datum.strftime("%d.%m.%Y"))
        
        mandat = False
        if len(mitgliedschaft.mandat) > 0:
            mandat = []
            for mnd in mitgliedschaft.mandat:
                mandat.append(mnd.datum.strftime("%d.%m.%Y"))
        
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
            'col_qty': cint(12 / col_qty),
            'allgemein': {
                'status': status,
                'eintritt': eintritt,
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
                'validierung': cint(mitgliedschaft.validierung_notwendig),
                'tel_g_1': mitgliedschaft.tel_g_1 or '',
                'tel_g_2': mitgliedschaft.tel_g_2 or '',
                'rg_tel_g': mitgliedschaft.rg_tel_g or '',
                'ist_geschenkmitgliedschaft': mitgliedschaft.ist_geschenkmitgliedschaft,
                'language': mitgliedschaft.language or 'de',
                'sektion': mitgliedschaft.sektion_id,
                'region': '({0})'.format(mitgliedschaft.region) if mitgliedschaft.region else '',
                'mitglied_nr': mitgliedschaft.mitglied_nr,
                'mandat': mandat,
                'haftpflicht': haftpflicht
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
        
        if mitgliedschaft.status_c not in ('Anmeldung', 'Online-Anmeldung', 'Interessent*in'):
            eintritt = mitgliedschaft.eintrittsdatum
        else:
            eintritt = mitgliedschaft.eintritt if mitgliedschaft.eintritt else mitgliedschaft.creation
        
        allgemein = {
            'status': mitgliedschaft.status_c,
            'mitgliedtyp': mitgliedschaft.mitgliedtyp_c,
            'eintritt': eintritt,
            'kuendigung': mitgliedschaft.kuendigung or False,
            'ist_geschenkmitgliedschaft': mitgliedschaft.ist_geschenkmitgliedschaft,
            'language': mitgliedschaft.language or 'de',
            'sektion': mitgliedschaft.sektion_id,
            'region': '({0})'.format(mitgliedschaft.region) if mitgliedschaft.region else '',
            'mitglied_nr': mitgliedschaft.mitglied_nr
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
        if cint(mitgliedschaft.hat_solidarmitglied) == 1:
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
            'postfach': 1 if cint(mitgliedschaft.postfach) == 1 else 0,
            'postfach_nummer': mitgliedschaft.postfach_nummer if mitgliedschaft.postfach_nummer else False,
            'plz': mitgliedschaft.plz,
            'ort': mitgliedschaft.ort
        }
        
        # Objektadresse
        if cint(mitgliedschaft.abweichende_objektadresse) == 1:
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
        if cint(mitgliedschaft.abweichende_rechnungsadresse) == 1:
            rechnungsadresse = {
                'zusatz': mitgliedschaft.rg_zusatz_adresse if mitgliedschaft.rg_zusatz_adresse else False,
                'strasse': mitgliedschaft.rg_strasse if mitgliedschaft.rg_strasse else False,
                'nummer': mitgliedschaft.rg_nummer if mitgliedschaft.rg_nummer else False,
                'nummer_zu': mitgliedschaft.rg_nummer_zu if mitgliedschaft.rg_nummer_zu else False,
                'postfach': 1 if cint(mitgliedschaft.rg_postfach) == 1 else 0,
                'postfach_nummer': mitgliedschaft.rg_postfach_nummer if mitgliedschaft.rg_postfach_nummer else False,
                'plz': mitgliedschaft.rg_plz,
                'ort': mitgliedschaft.rg_ort
            }
            col_qty += 1
        
        # Rechnungsempfänger
        if cint(mitgliedschaft.unabhaengiger_debitor) == 1:
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
            'col_qty': cint(12 / col_qty),
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
    
    if mitgliedschaft.doctype == 'Kunden':
        if cint(mitgliedschaft.unabhaengiger_debitor) == 1:
            # Rechnungs Anrede
            if mitgliedschaft.rg_anrede == 'Herr':
                return _('Sehr geehrter Herr {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.rg_nachname)
            elif mitgliedschaft.rg_anrede == 'Frau':
                return _('Sehr geehrte Frau {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.rg_nachname)
            else:
                return _('Guten Tag {vorname} {nachname}', mitgliedschaft.language or 'de').format(vorname=mitgliedschaft.rg_vorname or '', nachname=mitgliedschaft.rg_nachname)
        else:
            if mitgliedschaft.anrede == 'Herr':
                return _('Sehr geehrter Herr {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.nachname)
            elif mitgliedschaft.anrede == 'Frau':
                return _('Sehr geehrte Frau {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.nachname)
            else:
                return _('Guten Tag {vorname} {nachname}', mitgliedschaft.language or 'de').format(vorname=mitgliedschaft.vorname or '', nachname=mitgliedschaft.nachname)
    
    if mitgliedschaft.hat_solidarmitglied and not rg:
        # mit Solidarmitglied
        if mitgliedschaft.anrede_c not in ('Herr', 'Frau') and mitgliedschaft.anrede_2 not in ('Herr', 'Frau'):
            # enthält neutrale Anrede
            if mitgliedschaft.nachname_1 == mitgliedschaft.nachname_2 and mitgliedschaft.vorname_1 == mitgliedschaft.vorname_2:
                # gleiche Namen Fallback
                return _('Guten Tag', mitgliedschaft.language or 'de')
            else:
                return _('Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
        else:
            if mitgliedschaft.anrede_c == mitgliedschaft.anrede_2:
                # selbes Geschlecht
                if mitgliedschaft.nachname_1 == mitgliedschaft.nachname_2:
                    # gleiche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return _('Sehr geehrter Herr {vorname_1} {nachname_1}, sehr geehrter Herr {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return _('Sehr geehrte Frau {vorname_1} {nachname_1}, sehr geehrte Frau {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return _('Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                else:
                    # unterschiedliche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return _('Sehr geehrter Herr {nachname_1}, sehr geehrter Herr {nachname_2}', mitgliedschaft.language or 'de').format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return _('Sehr geehrte Frau {nachname_1}, sehr geehrte Frau {nachname_2}', mitgliedschaft.language or 'de').format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return _('Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
            else:
                # unterschiedliches Geschlecht
                if mitgliedschaft.nachname_1 == mitgliedschaft.nachname_2:
                    # gleiche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return _('Sehr geehrte Herr und Frau {nachname_1}', mitgliedschaft.language or 'de').format(nachname_1=mitgliedschaft.nachname_1)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return _('Sehr geehrte Frau und Herr {nachname_1}', mitgliedschaft.language or 'de').format(nachname_1=mitgliedschaft.nachname_1)
                    else:
                        # Fallback
                        return _('Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
                else:
                    # unterschiedliche Nachnamen
                    if mitgliedschaft.anrede_c == 'Herr':
                        return _('Sehr geehrter Herr {nachname_1}, sehr geehrte Frau {nachname_2}', mitgliedschaft.language or 'de').format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    elif mitgliedschaft.anrede_c == 'Frau':
                        return _('Sehr geehrte Frau {nachname_1}, sehr geehrter Herr {nachname_2}', mitgliedschaft.language or 'de').format(nachname_1=mitgliedschaft.nachname_1, nachname_2=mitgliedschaft.nachname_2)
                    else:
                        # Fallback
                        return _('Guten Tag {vorname_1} {nachname_1} und {vorname_2} {nachname_2}', mitgliedschaft.language or 'de').format(vorname_1=mitgliedschaft.vorname_1 or '', nachname_1=mitgliedschaft.nachname_1, vorname_2=mitgliedschaft.vorname_2, nachname_2=mitgliedschaft.nachname_2)
        
    else:
        if not rg:
            # ohne Solidarmitglied
            if mitgliedschaft.anrede_c == 'Herr':
                return _('Sehr geehrter Herr {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.nachname_1)
            elif mitgliedschaft.anrede_c == 'Frau':
                return _('Sehr geehrte Frau {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.nachname_1)
            else:
                return _('Guten Tag {vorname} {nachname}', mitgliedschaft.language or 'de').format(vorname=mitgliedschaft.vorname_1 or '', nachname=mitgliedschaft.nachname_1)
        else:
            if cint(mitgliedschaft.unabhaengiger_debitor) == 1:
                # Rechnungs Anrede
                if mitgliedschaft.rg_anrede == 'Herr':
                    return _('Sehr geehrter Herr {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.rg_nachname)
                elif mitgliedschaft.rg_anrede == 'Frau':
                    return _('Sehr geehrte Frau {nachname}', mitgliedschaft.language or 'de').format(nachname=mitgliedschaft.rg_nachname)
                else:
                    return _('Guten Tag {vorname} {nachname}', mitgliedschaft.language or 'de').format(vorname=mitgliedschaft.rg_vorname or '', nachname=mitgliedschaft.rg_nachname)
            else:
                return get_anredekonvention(self=mitgliedschaft)

@frappe.whitelist()
def sektionswechsel(mitgliedschaft, neue_sektion, zuzug_per):
    if str(get_sektion_code(neue_sektion)) not in ('ZH'):
        # Pseudo Sektion handling
        if cint(frappe.db.get_value("Sektion", neue_sektion, "pseudo_sektion")) == 1:
            return 1
        
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
            new_mitgliedschaft.wegzug_zu = ''
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
            new_mitgliedschaft.region_manuell = 0
            new_mitgliedschaft.region = None
            new_mitgliedschaft.status_change = []
            new_mitgliedschaft.haftpflicht = []
            new_mitgliedschaft.mandat = []
            new_mitgliedschaft.zuzug_massendruck = 0
            new_mitgliedschaft.zuzugs_rechnung = None
            new_mitgliedschaft.zuzug_korrespondenz = None
            new_mitgliedschaft.insert(ignore_permissions=True)
            
            frappe.db.commit()
            
            # erstelle ggf. neue Rechnung
            mit_rechnung = False
            if new_mitgliedschaft.bezahltes_mitgliedschaftsjahr < cint(now().split("-")[0]):
                if new_mitgliedschaft.naechstes_jahr_geschuldet == 1:
                    mit_rechnung = create_mitgliedschaftsrechnung(new_mitgliedschaft.name, jahr=cint(now().split("-")[0]), submit=True, attach_as_pdf=True, druckvorlage=get_druckvorlagen(sektion=neue_sektion, dokument='Zuzug mit EZ', mitgliedtyp=new_mitgliedschaft.mitgliedtyp_c, reduzierte_mitgliedschaft=new_mitgliedschaft.reduzierte_mitgliedschaft, language=new_mitgliedschaft.language)['default_druckvorlage'])
            
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
def create_mitgliedschaftsrechnung(mitgliedschaft, mitgliedschaft_obj=False, jahr=None, bezahlt=False, submit=False, attach_as_pdf=False, ignore_stichtage=False, inkl_hv=True, hv_bar_bezahlt=False, druckvorlage=False, massendruck=False, eigene_items=False, rechnungs_artikel=None, rechnungs_jahresversand=None, geschenk_reset=False):
    if not mitgliedschaft_obj:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    else:
        mitgliedschaft = mitgliedschaft_obj
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
    
    if not eigene_items or cint(eigene_items) == 0:
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
                        jahr = cint(getdate(today()).strftime("%Y")) + 1
            
            # prüfe Beitrittsgebühr
            if cint(mitgliedschaft.bezahltes_mitgliedschaftsjahr) == 0 and sektion.mitgliedschafts_artikel_beitritt:
                item.append({"item_code": sektion.mitgliedschafts_artikel_beitritt,"qty": 1, "cost_center": company.cost_center})
        
        if mitgliedschaft.mitgliedtyp_c == 'Geschäft':
            item = [{"item_code": sektion.mitgliedschafts_artikel_geschaeft,"qty": 1, "cost_center": company.cost_center}]
            # prüfe gratis ab stichtag
            gratis_ab = getdate(getdate(today()).strftime("%Y") + "-" + getdate(sektion.gratis_bis_ende_jahr).strftime("%m") + "-" + getdate(sektion.gratis_bis_ende_jahr).strftime("%d"))
            if getdate(today()) >= gratis_ab:
                item = [
                    {"item_code": sektion.mitgliedschafts_artikel_gratis,"qty": 1, "cost_center": company.cost_center},
                    {"item_code": sektion.mitgliedschafts_artikel_geschaeft,"qty": 1, "cost_center": company.cost_center}
                ]
                jahr = cint(getdate(today()).strftime("%Y")) + 1
            # prüfe Beitrittsgebühr
            if cint(mitgliedschaft.bezahltes_mitgliedschaftsjahr) == 0 and sektion.mitgliedschafts_artikel_beitritt_geschaeft:
                item.append({"item_code": sektion.mitgliedschafts_artikel_beitritt_geschaeft,"qty": 1, "cost_center": company.cost_center})
    else:
        rechnungs_artikel = json.loads(rechnungs_artikel)
        for item in rechnungs_artikel:
            del item['__islocal']
            # ~ item['qty'] = 1
            item['cost_center'] = company.cost_center
        item = rechnungs_artikel
        # ~ frappe.throw(rechnungs_artikel)
    
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
        'mitgliedschafts_jahr': jahr or cint(getdate(today()).strftime("%Y")),
        'due_date': add_days(today(), 30),
        'debit_to': company.default_receivable_account,
        'sektions_code': str(sektion.sektion_id) or '00',
        'sektion_id': mitgliedschaft.sektion_id,
        "items": item,
        "druckvorlage": druckvorlage if druckvorlage else '',
        "exclude_from_payment_reminder_until": exclude_from_payment_reminder_until,
        "rechnungs_jahresversand": rechnungs_jahresversand,
        "allocate_advances_automatically": 1 if rechnungs_jahresversand else 0
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
        bezugsjahr = jahr or cint(getdate(today()).strftime("%Y"))
        fr_rechnung = create_hv_fr(mitgliedschaft=mitgliedschaft.name, sales_invoice=sinv.name, bezahlt=hv_bar_bezahlt, bezugsjahr=bezugsjahr)
    
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
    
    if geschenk_reset:
        frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'geschenk_reset_rechnung', sinv.name)
    
    return sinv.name

@frappe.whitelist()
def make_kuendigungs_prozess(mitgliedschaft, datum_kuendigung, massenlauf, druckvorlage, grund='Ohne Begründung'):
    # erfassung Kündigung
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    mitgliedschaft.kuendigung = datum_kuendigung
    new_line = ''
    if mitgliedschaft.wichtig:
        new_line = '\n'
        mitgliedschaft.wichtig += '\nKündigungsgrund: {0}'.format(grund)
    else:
        mitgliedschaft.wichtig = 'Kündigungsgrund: {0}'.format(grund)
    
    # erstelle status change log und Status-Änderung
    change_log_row = mitgliedschaft.append('status_change', {})
    change_log_row.datum = now()
    change_log_row.status_alt = mitgliedschaft.status_c
    change_log_row.status_neu = 'Regulär &dagger;'
    change_log_row.grund = grund
    
    if mitgliedschaft.status_c == 'Online-Kündigung':
        mitgliedschaft.status_c = 'Regulär'
    
    mitgliedschaft.validierung_notwendig = 0
    mitgliedschaft.kuendigung_druckvorlage = druckvorlage
    if massenlauf == '1':
        mitgliedschaft.kuendigung_verarbeiten = 1
    mitgliedschaft.letzte_bearbeitung_von = 'User'
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
            return raise_xxx(400, 'Bad Request', 'mitgliedId == 0', str(kwargs))
    else:
        return raise_xxx(400, 'Bad Request', 'mitgliedId missing', str(kwargs))

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
        'onlinePaymentId',
        'kuendigungsgrund'
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
    curr_year = cint(getdate().strftime("%Y"))
    if inkl_hv:
        if cint(inkl_hv) >= curr_year:
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
    if email != 'None':
        return True
    else:
        return False

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
    if str(get_sektion_code(mitgliedschaft.sektion_id)) not in ('ZH', 'M+W-Abo'):
        if not cint(frappe.db.get_single_value('Service Plattform API', 'queue')) == 1:
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
        if mitgliedschaft.status_c not in ('Online-Beitritt', 'Online-Mutation'):
            queue = frappe.get_doc({
                "doctype": "Service Platform Queue",
                "status": "Open",
                "mv_mitgliedschaft": mitgliedschaft.mitglied_id,
                "sektion_id": mitgliedschaft.sektion_id,
                "update": 1 if update else 0
            })
            
            queue.insert(ignore_permissions=True, ignore_links=True)
        
        return

def send_mvm_sektionswechsel(mitgliedschaft):
    from mvd.mvd.service_plattform.api import sektionswechsel
    prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
    neue_sektion = ''
    if mitgliedschaft.wegzug_zu == 'MVZH':
        neue_sektion = 'ZH'
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
    
    kuendigungsgrund = None
    
    if mitgliedschaft.kuendigung:
        kuendigungsgrund = frappe.db.sql("""SELECT
                                                `grund`
                                            FROM `tabStatus Change`
                                            WHERE `status_neu` = 'Regulär &dagger;'
                                            AND `parent` = '{mitgliedschaft}'
                                            ORDER BY `idx` DESC""".format(mitgliedschaft=mitgliedschaft.name), as_dict=True)
        if len(kuendigungsgrund) > 0:
            kuendigungsgrund = kuendigungsgrund[0].grund or None
        else:
            kuendigungsgrund = None
        
    
    # Bei Wegzügen muss gem. SP-API der Key alteSektionCode leer sein
    if mitgliedschaft.status_c == 'Wegzug':
        alteSektionCode = ''
    else:
        alteSektionCode = str(get_sektion_code(mitgliedschaft.zuzug_von)) if mitgliedschaft.zuzug_von else None
    
    prepared_mvm = {
        "mitgliedNummer": str(mitgliedschaft.mitglied_nr) if str(mitgliedschaft.mitglied_nr) != 'MV' else None,
        "mitgliedId": cint(mitgliedschaft.mitglied_id),
        "sektionCode": str(get_sektion_code(mitgliedschaft.sektion_id)),
        "regionCode": frappe.get_value("Region", mitgliedschaft.region, "region_c") if mitgliedschaft.region else None,
        "regionManuell": True if mitgliedschaft.region_manuell else False,
        "typ": str(typ_mapper[mitgliedschaft.mitgliedtyp_c]),
        "status": str(status_mapper[mitgliedschaft.status_c]) if mitgliedschaft.status_c != 'Online-Mutation' else str(status_mapper[mitgliedschaft.status_vor_onl_mutation]),
        "sprache": get_sprache(language=mitgliedschaft.language) if mitgliedschaft.language else 'Deutsch',
        "istTemporaeresMitglied": False, # ???
        "fuerBewirtschaftungGesperrt": True if mitgliedschaft.adressen_gesperrt else False,
        "erfassungsdatum": str(mitgliedschaft.creation).replace(" ", "T"),
        "eintrittsdatum": str(mitgliedschaft.eintrittsdatum).replace(" ", "T") + "T00:00:00" if mitgliedschaft.eintrittsdatum else None,
        "austrittsdatum": str(mitgliedschaft.austritt).replace(" ", "T") + "T00:00:00" if mitgliedschaft.austritt else None,
        "alteSektionCode": alteSektionCode,
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
        "anzahlZeitungen": cint(mitgliedschaft.m_und_w),
        "zeitungAlsPdf": True if mitgliedschaft.m_und_w_pdf else False,
        "isKollektiv": True if cint(mitgliedschaft.ist_kollektiv) == 1 else False,
        "isGeschenkmitgliedschaft": True if cint(mitgliedschaft.ist_geschenkmitgliedschaft) == 1 else False,
        "isEinmaligeSchenkung": True if cint(mitgliedschaft.ist_einmalige_schenkung) == 1 else False,
        "schenkerHasGeschenkunterlagen": True if cint(mitgliedschaft.geschenkunterlagen_an_schenker) == 1 else False,
        "datumBezahltHaftpflicht": str(mitgliedschaft.datum_hv_zahlung).replace(" ", "T") + "T00:00:00" if mitgliedschaft.datum_hv_zahlung else None,
        "adressen": adressen,
        "onlineHaftpflicht": mitgliedschaft.online_haftpflicht if mitgliedschaft.online_haftpflicht and mitgliedschaft.online_haftpflicht != '' else None,
        "onlineGutschrift": mitgliedschaft.online_gutschrift if mitgliedschaft.online_gutschrift and mitgliedschaft.online_gutschrift != '' else None,
        "onlineBetrag": mitgliedschaft.online_betrag if mitgliedschaft.online_betrag and mitgliedschaft.online_betrag != '' else None,
        "datumOnlineVerbucht": mitgliedschaft.datum_online_verbucht if mitgliedschaft.datum_online_verbucht and mitgliedschaft.datum_online_verbucht != '' else None,
        "datumOnlineGutschrift": mitgliedschaft.datum_online_gutschrift if mitgliedschaft.datum_online_gutschrift and mitgliedschaft.datum_online_gutschrift != '' else None,
        "onlinePaymentMethod": mitgliedschaft.online_payment_method if mitgliedschaft.online_payment_method and mitgliedschaft.online_payment_method != '' else None,
        "onlinePaymentId": mitgliedschaft.online_payment_id if mitgliedschaft.online_payment_id and mitgliedschaft.online_payment_id != '' else None,
        "kuendigungsgrund": kuendigungsgrund,
        "mvbTyp":  mitgliedschaft.mvb_typ if mitgliedschaft.mvb_typ and mitgliedschaft.mvb_typ != '' else None
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
    
    if cint(mitgliedschaft.hat_solidarmitglied) == 1:
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
    
    if cint(mitgliedschaft.abweichende_objektadresse) == 1:
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
    
    if cint(mitgliedschaft.abweichende_rechnungsadresse) == 1:
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
        
        if cint(mitgliedschaft.unabhaengiger_debitor) == 1:
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
    skip = False
    if sinv.rechnungs_jahresversand:
        from frappe.utils.data import add_to_date
        ref_date = add_to_date(date=sinv.creation, hours=12)
        if getdate(sinv.modified) < getdate(ref_date):
            skip = True
            # gewährleistung dass trotz skip das Mitgliedschaftsjahr und bezahldatum korrekt geschrieben wird.
            if cint(frappe.db.get_value('Mitgliedschaft', sinv.mv_mitgliedschaft, 'bezahltes_mitgliedschaftsjahr')) < cint(sinv.mitgliedschafts_jahr):
                if sinv.is_pos == 1:
                    frappe.db.set_value('Mitgliedschaft', sinv.mv_mitgliedschaft, 'datum_zahlung_mitgliedschaft', sinv.posting_date)
                    frappe.db.set_value('Mitgliedschaft', sinv.mv_mitgliedschaft, 'bezahltes_mitgliedschaftsjahr', sinv.mitgliedschafts_jahr)
                else:
                    pes = frappe.db.sql("""SELECT `parent` FROM `tabPayment Entry Reference`
                                            WHERE `reference_doctype` = 'Sales Invoice'
                                            AND `reference_name` = '{sinv}' ORDER BY `creation` DESC""".format(sinv=sinv.name), as_dict=True)
                    if len(pes) > 0:
                        pe = frappe.get_doc("Payment Entry", pes[0].parent)
                        frappe.db.set_value('Mitgliedschaft', sinv.mv_mitgliedschaft, 'datum_zahlung_mitgliedschaft', pe.reference_date)
                        frappe.db.set_value('Mitgliedschaft', sinv.mv_mitgliedschaft, 'bezahltes_mitgliedschaftsjahr', sinv.mitgliedschafts_jahr)
                    else:
                        if len(sinv.advances) > 0:
                            pe = frappe.get_doc("Payment Entry", sinv.advances[0].reference_name)
                            frappe.db.set_value('Mitgliedschaft', sinv.mv_mitgliedschaft, 'datum_zahlung_mitgliedschaft', pe.reference_date)
                            frappe.db.set_value('Mitgliedschaft', sinv.mv_mitgliedschaft, 'bezahltes_mitgliedschaftsjahr', sinv.mitgliedschafts_jahr)
            # gewährleistung dass trotz skip die Mitgliedschafts Ampel aktualisiert wird
            if sinv.mv_mitgliedschaft:
                mitgliedschaft = frappe.get_doc("Mitgliedschaft", sinv.mv_mitgliedschaft)
                ampelfarbe = get_ampelfarbe(mitgliedschaft)
                frappe.db.set_value('Mitgliedschaft', sinv.mv_mitgliedschaft, 'ampel_farbe', ampelfarbe)
    
    if not skip:
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
            sinv_max_level = cint(sinv.payment_reminder_level or 0)
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
                mitgliedschaft.letzte_bearbeitung_von = 'User'
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
    sektionen = frappe.db.sql("""SELECT `name` FROM `tabSektion` WHERE `keine_mitgliedschaftssektion` != 1 ORDER BY `name` ASC""", as_dict=True)
    sektionen_zur_auswahl = ''
    for sektion in sektionen:
        sektionen_zur_auswahl += "\n" + sektion.name
    return sektionen_zur_auswahl

@frappe.whitelist()
def get_pseudo_sektionen_zur_auswahl():
    sektionen = frappe.db.sql("""SELECT `name` FROM `tabSektion` WHERE `pseudo_sektion` = 1 AND `keine_mitgliedschaftssektion` != 1 ORDER BY `name` ASC""", as_dict=True)
    sektionen_zur_auswahl = ''
    for sektion in sektionen:
        sektionen_zur_auswahl += "\n" + sektion.name
    return sektionen_zur_auswahl

@frappe.whitelist()
def sektionswechsel_pseudo_sektion(mitgliedschaft, eintrittsdatum, bezahltes_mitgliedschaftsjahr, zuzug_von, sektion_id, zuzug):
    try:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
        mitgliedschaft.eintrittsdatum = eintrittsdatum
        mitgliedschaft.bezahltes_mitgliedschaftsjahr = cint(bezahltes_mitgliedschaftsjahr)
        mitgliedschaft.zuzug_von = sektion_id
        mitgliedschaft.zuzug = zuzug
        mitgliedschaft.status_c = 'Regulär'
        
        
        # erstelle ggf. neue Rechnung
        mit_rechnung = False
        if mitgliedschaft.bezahltes_mitgliedschaftsjahr < cint(now().split("-")[0]):
            if mitgliedschaft.naechstes_jahr_geschuldet == 1:
                mit_rechnung = create_mitgliedschaftsrechnung(mitgliedschaft.name, jahr=cint(now().split("-")[0]), submit=True, attach_as_pdf=True, druckvorlage=get_druckvorlagen(sektion=mitgliedschaft.sektion_id, dokument='Zuzug mit EZ', mitgliedtyp=mitgliedschaft.mitgliedtyp_c, reduzierte_mitgliedschaft=mitgliedschaft.reduzierte_mitgliedschaft, language=mitgliedschaft.language)['default_druckvorlage'])
        
        if mit_rechnung:
            mitgliedschaft.zuzugs_rechnung = mit_rechnung
        else:
            druckvorlage = frappe.get_doc("Druckvorlage", get_druckvorlagen(sektion=mitgliedschaft.sektion_id, dokument='Zuzug ohne EZ', mitgliedtyp=mitgliedschaft.mitgliedtyp_c, reduzierte_mitgliedschaft=mitgliedschaft.reduzierte_mitgliedschaft, language=mitgliedschaft.language)['default_druckvorlage'])
            _new_korrespondenz = frappe.copy_doc(druckvorlage)
            _new_korrespondenz.doctype = 'Korrespondenz'
            _new_korrespondenz.sektion_id = mitgliedschaft.sektion_id
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
            
            new_korrespondenz['mv_mitgliedschaft'] = mitgliedschaft.name
            new_korrespondenz['massenlauf'] = 0
            
            new_korrespondenz = frappe.get_doc(new_korrespondenz)
            new_korrespondenz.insert(ignore_permissions=True)
            frappe.db.commit()
            
            mitgliedschaft.zuzug_korrespondenz = new_korrespondenz.name
        
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
        mitgliedschaft.eintrittsdatum = eintrittsdatum
        mitgliedschaft.bezahltes_mitgliedschaftsjahr = cint(bezahltes_mitgliedschaftsjahr)
        mitgliedschaft.zuzug_von = sektion_id
        mitgliedschaft.zuzug = zuzug
        mitgliedschaft.status_c = 'Regulär'
        mitgliedschaft.save(ignore_permissions=True)
                
        return 1
    except Exception as err:
        frappe.log_error("{0}\n---\n{1}".format(err, mitgliedschaft.as_json()), 'sektionswechsel_pseudo_sektion')
        return err

def get_ampelfarbe(mitgliedschaft):
    ''' mögliche Ampelfarben:
        - Grün: ampelgruen --> Mitglied kann alle Dienstleistungen beziehen (keine Karenzfristen, keine überfälligen oder offen Rechnungen)
        - Gelb: ampelgelb --> Karenzfristen oder offene Rechnungen
        - Rot: ampelrot --> überfällige offene Rechnungen
        
        MVZH Ausnahme:
        - Grün --> Jahr bezahlt >= aktuelles Jahr
        - Rot --> Jahr bezahlt < aktuelles Jahr
    '''
    
    if mitgliedschaft.status_c in ('Gestorben', 'Wegzug', 'Ausschluss', 'Inaktiv', 'Interessent*in'):
        ampelfarbe = 'ampelrot'
    else:
        
        # MVZH Ausnahme Start
        if mitgliedschaft.sektion_id == 'MVZH':
            if cint(mitgliedschaft.bezahltes_mitgliedschaftsjahr) < cint(datetime.date.today().year):
                return 'ampelrot'
            else:
                return 'ampelgruen'
        # MVZH Ausnahme Ende
        
        ueberfaellige_rechnungen = 0
        offene_rechnungen = 0
        
        sektion = frappe.get_doc("Sektion", mitgliedschaft.sektion_id)
        karenzfrist_in_d = sektion.karenzfrist
        ablauf_karenzfrist = add_days(getdate(mitgliedschaft.eintrittsdatum), karenzfrist_in_d)
        
        if getdate() < ablauf_karenzfrist:
            karenzfrist = False
        else:
            karenzfrist = True
        
        # musste mit v8.5.9 umgeschrieben werden, da negative Werte ebenfalls == True ergeben. (Beispiel: (1 + 2015 - 2023) == True)
        # ~ aktuelles_jahr_bezahlt = bool( 1 + cint(mitgliedschaft.bezahltes_mitgliedschaftsjahr) - cint(now().split("-")[0]) )
        aktuelles_jahr_bezahlt = False if ( 1 + cint(mitgliedschaft.bezahltes_mitgliedschaftsjahr) - cint(now().split("-")[0]) ) <= 0 else True
        
        if not aktuelles_jahr_bezahlt:
            ueberfaellige_rechnungen = frappe.db.sql("""SELECT IFNULL(SUM(`outstanding_amount`), 0) AS `open_amount`
                                                        FROM `tabSales Invoice` 
                                                        WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'
                                                        AND `ist_mitgliedschaftsrechnung` = 1
                                                        AND `due_date` < CURDATE()
                                                        AND `docstatus` = 1""".format(mitgliedschaft=mitgliedschaft.name), as_dict=True)[0].open_amount
        else:
            ueberfaellige_rechnungen = 0
        
        if ueberfaellige_rechnungen > 0:
            ampelfarbe = 'ampelrot'
        else:
            if not aktuelles_jahr_bezahlt:
                offene_rechnungen = frappe.db.sql("""SELECT IFNULL(SUM(`outstanding_amount`), 0) AS `open_amount`
                                                    FROM `tabSales Invoice` 
                                                    WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'
                                                    AND `ist_mitgliedschaftsrechnung` = 1
                                                    AND `due_date` >= CURDATE()
                                                    AND `docstatus` = 1""".format(mitgliedschaft=mitgliedschaft.name), as_dict=True)[0].open_amount
            else:
                offene_rechnungen = 0
            
            if offene_rechnungen > 0:
                ampelfarbe = 'ampelgelb'
            else:
                if not karenzfrist:
                    ampelfarbe = 'ampelgelb'
                else:
                    ampelfarbe = 'ampelgruen'
    
    return ampelfarbe

@frappe.whitelist()
def create_korrespondenz(mitgliedschaft, titel, druckvorlage=False, massenlauf=False, attach_as_pdf=False, sinv_mitgliedschaftsjahr=False):
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
        if sinv_mitgliedschaftsjahr:
            bezugsjahr = frappe.db.get_value("Sales Invoice", sinv_mitgliedschaftsjahr, 'mitgliedschafts_jahr')
            new_korrespondenz.mitgliedschafts_jahr_manuell = 1
            new_korrespondenz.mitgliedschafts_jahr = bezugsjahr
        new_korrespondenz.insert(ignore_permissions=True)
        frappe.db.commit()
        
        if attach_as_pdf:
            # add doc signature to allow print
            frappe.form_dict.key = new_korrespondenz.get_signature()
            
            # erstellung Rechnungs PDF
            output = PdfFileWriter()
            output = frappe.get_print("Korrespondenz", new_korrespondenz.name, 'Korrespondenz', as_pdf = True, output = output, ignore_zugferd=True)
            
            file_name = "{new_korrespondenz}_{datetime}".format(new_korrespondenz=new_korrespondenz.name, datetime=now().replace(" ", "_"))
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
    
    # notify
    if cint(notify) == 1:
        from frappe.desk.form.assign_to import notify_assignment
        notify_assignment(todo.assigned_by, todo.owner, todo.reference_type, todo.reference_name, action='ASSIGN',\
                 description=todo.description, notify=notify)
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
    mitgliedschafts_copy.status_change = []
    
    mitgliedschafts_copy.insert(ignore_permissions=True)
    frappe.db.commit()
    
    mitgliedschafts_copy.validierung_notwendig = 0
    mitgliedschafts_copy.save(ignore_permissions=True)
    
    alte_mitgliedschaft.add_comment('Comment', text='Mitgliedschaft (als Anmeldung) mittels {0} ({1}) reaktiviert.'.format(mitgliedschafts_copy.mitglied_nr, mitgliedschafts_copy.name))
    mitgliedschafts_copy.add_comment('Comment', text='Reaktivierte Mitgliedschaft aus {0} ({1})'.format(alte_mitgliedschaft.mitglied_nr, alte_mitgliedschaft.name))
    
    return mitgliedschafts_copy.name

@frappe.whitelist()
def check_erstelle_rechnung(mitgliedschaft, typ, sektion, jahr=False):
    gratis_case = False
    if not jahr:
        jahr = cint(getdate(today()).strftime("%Y"))
    else:
        jahr = cint(jahr)
    if typ == 'Privat':
        gratis_bis_ende_jahr = frappe.get_value("Sektion", sektion, "gratis_bis_ende_jahr")
        gratis_ab = getdate(getdate(today()).strftime("%Y") + "-" + getdate(gratis_bis_ende_jahr).strftime("%m") + "-" + getdate(gratis_bis_ende_jahr).strftime("%d"))
        if getdate(today()) >= gratis_ab:
            gratis_case = True
    
    if not gratis_case:
        vorhandene_rechnungen = frappe.db.sql("""SELECT
                                                    COUNT(`name`) AS `qty`
                                                FROM `tabSales Invoice`
                                                WHERE `docstatus` = 1
                                                AND `ist_mitgliedschaftsrechnung` = 1
                                                AND `mv_mitgliedschaft` = '{mitgliedschaft}'
                                                AND `mitgliedschafts_jahr` = '{jahr}'""".format(mitgliedschaft=mitgliedschaft, jahr=jahr), as_dict=True)[0].qty
    else:
        vorhandene_rechnungen = 0
    
    if vorhandene_rechnungen < 1:
        return 1
    else:
        return jahr + 1

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

@frappe.whitelist()
def get_returen_dashboard(mitgliedschaft):
    anz_offen = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabRetouren` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}' AND `status` = 'Offen'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)[0].qty
    anz_in_bearbeitung = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabRetouren` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}' AND `status` = 'In Bearbeitung'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)[0].qty
    return {
        'anz_offen': anz_offen,
        'anz_in_bearbeitung': anz_in_bearbeitung
    }

@frappe.whitelist()
def get_beratungen_dashboard(mitgliedschaft):
    offen = frappe.db.sql("""SELECT `name`, `status`, `kontaktperson` FROM `tabBeratung` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}' AND `status` NOT IN ('Closed', 'Zusammengeführt')""".format(mitgliedschaft=mitgliedschaft), as_dict=True)
    termine = []
    anz_offen = 0
    anz_termine = 0
    if len(offen) > 0:
        anz_offen = len(offen)
        for beratung in offen:
            if beratung.status == 'Rückfrage: Termin vereinbaren':
                termine.append('Offen')
                anz_termine += 1
            else:
                termin_dates = frappe.db.sql("""SELECT `von` FROM `tabBeratung Termin` WHERE `parent` = '{beratung}' AND `von` >= CURDATE() ORDER BY `von` ASC""".format(beratung=beratung.name, mitgliedschaft=mitgliedschaft), as_dict=True)
                for termin_date in termin_dates:
                    termine.append("{0} ({1})".format(frappe.utils.get_datetime(termin_date.von).strftime('%d.%m.%Y %H:%M'), beratung.kontaktperson or 'Ohne Berater*in Zuweisung'))
                    anz_termine += 1
        if len(termine) > 1:
            termine = ", nächste Termine: {0}".format(" / ".join(termine))
        elif len(termine) > 0:
            termine = ", nächster Termin: {0}".format(termine[0])
    
    ungelesen_qty = frappe.db.count("Beratung", {'mv_mitgliedschaft': mitgliedschaft, 'ungelesen': 1}) or 0
    return {
        'anz_offen': anz_offen,
        'termine': termine,
        'anz_termine': anz_termine,
        'ungelesen_qty': ungelesen_qty
    }

@frappe.whitelist()
def get_kuendigungsmail_txt(mitgliedschaft, sektion_id, language):
    if language == 'fr':
        txt_field = 'kuendigungs_bestaetigung_fr'
        subject = 'Résiliation de votre affiliation'
    else:
        txt_field = 'kuendigungs_bestaetigung_de'
        subject = 'Kündigung Ihrer Mitgliedschaft'
    
    txt_raw = frappe.db.get_value("Sektion", sektion_id, txt_field)
    if txt_raw:
        txt = replace_mv_keywords(txt_raw, mitgliedschaft)
    else:
        txt = ''
    email_body = '<div>{0}</div>'.format(txt.replace("\n", "<br>"))
    return {
        'subject': subject,
        'email_body': email_body
    }

@frappe.whitelist()
def erstellung_faktura_kunde(mitgliedschaft):
    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    
    # check ob kunde bereits existiert
    existing = frappe.db.sql("""SELECT `name` FROM `tabKunden` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}'""".format(mitgliedschaft=mitgliedschaft.name), as_dict=True)
    if len(existing) > 0:
        return existing[0].name
    
    kunde = frappe.get_doc({
        "doctype":"Kunden",
        "mv_mitgliedschaft": mitgliedschaft.name,
        "sektion_id": "MVD",
        'language': mitgliedschaft.language,
        'kundentyp': mitgliedschaft.kundentyp,
        'anrede': mitgliedschaft.anrede_c,
        'vorname': mitgliedschaft.vorname_1,
        'nachname': mitgliedschaft.nachname_1,
        'firma': mitgliedschaft.firma,
        'zusatz_firma': mitgliedschaft.zusatz_firma,
        'tel_p': mitgliedschaft.tel_p_1,
        'tel_m': mitgliedschaft.tel_m_1,
        'tel_g': mitgliedschaft.tel_g_1,
        'e_mail': mitgliedschaft.e_mail_1,
        'strasse': mitgliedschaft.strasse,
        'zusatz_adresse': mitgliedschaft.zusatz_adresse,
        'nummer': mitgliedschaft.nummer,
        'nummer_zu': mitgliedschaft.nummer_zu,
        'plz': mitgliedschaft.plz,
        'ort': mitgliedschaft.ort,
        'postfach': mitgliedschaft.postfach,
        'land': mitgliedschaft.land,
        'postfach_nummer': mitgliedschaft.postfach_nummer,
        'abweichende_rechnungsadresse': mitgliedschaft.abweichende_rechnungsadresse,
        'rg_zusatz_adresse': mitgliedschaft.rg_zusatz_adresse,
        'rg_strasse': mitgliedschaft.rg_strasse,
        'rg_nummer': mitgliedschaft.rg_nummer,
        'rg_nummer_zu': mitgliedschaft.rg_nummer_zu,
        'rg_postfach': mitgliedschaft.rg_postfach,
        'rg_postfach_nummer': mitgliedschaft.rg_postfach_nummer,
        'rg_plz': mitgliedschaft.rg_plz,
        'rg_ort': mitgliedschaft.rg_ort,
        'rg_land': mitgliedschaft.rg_land
    }).insert(ignore_permissions=True)
    
    return kunde.name

def get_mitglied_id_from_nr(mitglied_nr=None):
    if mitglied_nr:
        mitgliedschaften = frappe.db.sql("""SELECT
                                                `name`
                                            FROM `tabMitgliedschaft`
                                            WHERE `mitglied_nr` LIKE '%{0}'
                                            AND `status_c` != 'Inaktiv'
                                            ORDER BY `creation` DESC LIMIT 1""".format(mitglied_nr), as_dict=True)
        if len(mitgliedschaften) > 0:
            return mitgliedschaften[0].name
        else:
            return None
    else:
        return None

def get_last_open_sinv(mitgliedschaft):
    # diese Funktion übergibt die letzte ausstehende Mitgliedschaftsrechnung an das Kündigungsdruckformat
    sinvs = frappe.db.sql("""
                          SELECT `name`
                          FROM `tabSales Invoice`
                          WHERE `ist_mitgliedschaftsrechnung` = 1
                          AND `mv_mitgliedschaft` = '{0}'
                          AND `outstanding_amount` > 0
                          ORDER BY `mitgliedschafts_jahr` ASC
                          LIMIT 1
                          """.format(mitgliedschaft), as_dict=True)
    if len(sinvs) > 0:
        return sinvs[0].name
    else:
        return None

def get_naechstes_jahr_geschuldet(mitglied_id, live_data=False):
    if not live_data:
        bezahltes_mitgliedschafsjahr = cint(frappe.db.get_value("Mitgliedschaft", mitglied_id, 'bezahltes_mitgliedschaftsjahr'))
    else:
        bezahltes_mitgliedschafsjahr = cint(live_data.bezahltes_mitgliedschaftsjahr)
    current_year = cint(now().split("-")[0])

    if current_year > bezahltes_mitgliedschafsjahr:
        return True
    else:
        if not live_data:
            sektion = frappe.db.get_value("Mitgliedschaft", mitglied_id, 'sektion_id')
        else:
            sektion = live_data.sektion_id
        
        stichtag = frappe.db.get_value("Sektion", sektion, 'kuendigungs_stichtag')
        stichtag_datum = getdate("{0}-{1}-{2}".format(current_year, stichtag.strftime("%Y-%m-%d").split("-")[1], stichtag.strftime("%Y-%m-%d").split("-")[2]))
        if getdate(today()) > stichtag_datum:
            return True
        else:
            return False
