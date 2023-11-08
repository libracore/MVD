# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.doctype.druckvorlage.druckvorlage import replace_mv_keywords

@frappe.whitelist()
def get_textdaten(sinv, druckvorlage):
    sinv = frappe.get_doc("Sales Invoice", sinv)
    sinv.manueller_rechnungstext = 1
    druckvorlage = frappe.get_doc("Druckvorlage", druckvorlage)
    
    for druckvorlage_seite in druckvorlage.seiten:
        row = sinv.append('seiten', {})
        row.stichwort = druckvorlage_seite.stichwort
        row.kopfzeile = druckvorlage_seite.kopfzeile
        row.ausweis = druckvorlage_seite.ausweis
        row.adressblock = druckvorlage_seite.adressblock
        row.pp = druckvorlage_seite.pp
        row.plz_und_ort = druckvorlage_seite.plz_und_ort
        row.referenzblock = druckvorlage_seite.referenzblock
        row.inhalt = druckvorlage_seite.inhalt
        row.seitenzahlen = druckvorlage_seite.seitenzahlen
        row.einzahlungsschein = druckvorlage_seite.einzahlungsschein
        row.ez_typ = druckvorlage_seite.ez_typ
    
    mitglied_ref = sinv.mv_mitgliedschaft or sinv.mv_kunde
    
    for seite in sinv.seiten:
        if seite.inhalt:
            seite.inhalt = replace_mv_keywords(seite.inhalt, mitglied_ref, sinv=sinv.name)
    
    sinv.save()
    
    return druckvorlage.name
