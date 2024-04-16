# -*- coding: utf-8 -*-
# Copyright (c) 2021-2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from PyPDF2 import PdfFileWriter
from frappe.utils import cint
from frappe.utils.data import now
from frappe.utils.pdf import get_file_data_from_writer


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

def sp_updater(mitgliedschaft):
    # sende neuanlage/update an sp wenn letzter bearbeiter nich SP
    if mitgliedschaft.letzte_bearbeitung_von == 'User':
        if mitgliedschaft.creation == mitgliedschaft.modified:
            # sende neuanlage an SP
            send_mvm_to_sp(mitgliedschaft, False)
        else:
            # sende update an SP
            send_mvm_to_sp(mitgliedschaft, True)
            # special case sektionswechsel nach ZH
            if mitgliedschaft.wegzug_zu == 'MVZH' and mitgliedschaft.status_c == 'Wegzug':
                send_mvm_sektionswechsel(mitgliedschaft)

def send_mvm_to_sp(mitgliedschaft, update):
    if str(get_sektion_code(mitgliedschaft.sektion_id)) not in ('ZH', 'M+W-Abo'):
        if not cint(frappe.db.get_single_value('Service Plattform API', 'queue')) == 1:
            from mvd.mvd.service_plattform.api import update_mvm
            prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
            update_status = update_mvm(prepared_mvm, update)
            return update_status
        else:
            create_sp_queue(mitgliedschaft, update)

def send_mvm_sektionswechsel(mitgliedschaft):
    from mvd.mvd.service_plattform.api import sektionswechsel
    prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
    neue_sektion = ''
    if mitgliedschaft.wegzug_zu == 'MVZH':
        neue_sektion = 'ZH'
    sektionswechsel(prepared_mvm, neue_sektion)

def get_sektion_code(sektion):
    sektionen = frappe.db.sql("""SELECT `sektion_c` FROM `tabSektion` WHERE `name` = '{sektion}'""".format(sektion=sektion), as_dict=True)
    if len(sektionen) > 0:
        return sektionen[0].sektion_c
    else:
        return False

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