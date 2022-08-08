# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.doctype.druckvorlage.druckvorlage import replace_mv_keywords

@frappe.whitelist()
def get_textdaten(sinv):
    sinv = frappe.get_doc("Sales Invoice", sinv)
    sinv.manueller_rechnungstext = 1
    
    druckvorlage = frappe.get_doc("Druckvorlage", sinv.druckvorlage)
    
    sinv.doppelseitiger_druck = druckvorlage.doppelseitiger_druck
    sinv.anzahl_seiten = druckvorlage.anzahl_seiten
    sinv.seite_1_qrr = druckvorlage.seite_1_qrr
    sinv.seite_1_fusszeile_ausblenden = druckvorlage.seite_1_fusszeile_ausblenden
    sinv.seite_1_referenzblock_ausblenden = druckvorlage.seite_1_referenzblock_ausblenden
    sinv.seite_2_qrr = druckvorlage.seite_2_qrr
    sinv.seite_2_fusszeile_ausblenden = druckvorlage.seite_2_fusszeile_ausblenden
    sinv.seite_2_referenzblock_ausblenden = druckvorlage.seite_2_referenzblock_ausblenden
    sinv.seite_2_adressblock_ausblenden = druckvorlage.seite_2_adressblock_ausblenden
    sinv.seite_2_datum_ausblenden = druckvorlage.seite_2_datum_ausblenden
    sinv.seite_3_qrr = druckvorlage.seite_3_qrr
    sinv.seite_3_fusszeile_ausblenden = druckvorlage.seite_3_fusszeile_ausblenden
    sinv.seite_3_referenzblock_ausblenden = druckvorlage.seite_3_referenzblock_ausblenden
    sinv.seite_3_adressblock_ausblenden = druckvorlage.seite_3_adressblock_ausblenden
    sinv.seite_3_datum_ausblenden = druckvorlage.seite_3_datum_ausblenden
    
    if druckvorlage.seite_1a:
        sinv.seite_1a = replace_mv_keywords(druckvorlage.seite_1a, sinv.mv_mitgliedschaft, sinv=sinv.name)
    
    if druckvorlage.seite_1b:
        sinv.seite_1b = replace_mv_keywords(druckvorlage.seite_1b, sinv.mv_mitgliedschaft, sinv=sinv.name)
    
    if druckvorlage.seite_2a:
        sinv.seite_2a = replace_mv_keywords(druckvorlage.seite_2a, sinv.mv_mitgliedschaft, sinv=sinv.name)
    
    if druckvorlage.seite_2b:
        sinv.seite_2b = replace_mv_keywords(druckvorlage.seite_2b, sinv.mv_mitgliedschaft, sinv=sinv.name)
    
    if druckvorlage.seite_3a:
        sinv.seite_3a = replace_mv_keywords(druckvorlage.seite_3a, sinv.mv_mitgliedschaft, sinv=sinv.name)
    
    if druckvorlage.seite_3b:
        sinv.seite_3b = replace_mv_keywords(druckvorlage.seite_3b, sinv.mv_mitgliedschaft, sinv=sinv.name)
    
    sinv.save()
    return druckvorlage.name
