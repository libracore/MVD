# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import add_days, getdate

@frappe.whitelist()
def get_resultate_html(name):
    col_qty = 1
    mitgliedschaft = frappe.get_doc("MV Mitgliedschaft", name)
    
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
    
    ''' mögliche Ampelfarben:
        - Grün: ampelgruen --> Mitglied kann alle Dienstleistungen beziehen (keine Karenzfristen, keine überfälligen oder offen Rechnungen)
        - Gelb: ampelgelb --> Karenzfristen oder offene Rechnungen
        - Rot: ampelrot --> überfällige offene Rechnungen
    '''
    
    rechnungs_kunde = mitgliedschaft.kunde_mitglied
    ueberfaellige_rechnungen = 0
    offene_rechnungen = 0
    
    sektion = frappe.get_doc("Sektion", mitgliedschaft.sektion_id)
    karenzfrist_in_d = sektion.karenzfrist
    ablauf_karenzfrist = add_days(getdate(mitgliedschaft.eintritt), karenzfrist_in_d)
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
    
    if mitgliedschaft.inkl_hv:
        if mitgliedschaft.zahlung_hv:
            hv_status = 'HV bezahlt am {0}'.format(frappe.utils.get_datetime(mitgliedschaft.zahlung_hv).strftime('%d.%m.%Y'))
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
            'eintritt': mitgliedschaft.eintritt,
            'ampelfarbe': ampelfarbe,
            'ueberfaellige_rechnungen': ueberfaellige_rechnungen,
            'offene_rechnungen': offene_rechnungen,
            'ablauf_karenzfrist': ablauf_karenzfrist,
            'zuzug': zuzug,
            'wegzug': wegzug,
            'zuzug_von': zuzug_von,
            'wegzug_zu': wegzug_zu,
            'mitgliedart': mitgliedschaft.mitglied_c,
            'hv_status': hv_status
        }
    }
    
    return frappe.render_template('templates/includes/mvd_suchresultate.html', data)
