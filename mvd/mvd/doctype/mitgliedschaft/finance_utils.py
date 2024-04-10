# -*- coding: utf-8 -*-
# Copyright (c) 2021-2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe.utils.data import add_days, getdate, now
import datetime
from mvd.mvd.doctype.druckvorlage.druckvorlage import get_druckvorlagen
from mvd.mvd.doctype.mitgliedschaft.utils import create_korrespondenz

def check_zahlung_mitgliedschaft(mitgliedschaft, external=False):
    if external:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    noch_kein_eintritt = False
    if not mitgliedschaft.datum_zahlung_mitgliedschaft:
        noch_kein_eintritt = True
    
    sinvs = frappe.db.sql("""SELECT
                                `name`,
                                `is_pos`,
                                `posting_date`,
                                `mitgliedschafts_jahr`
                            FROM `tabSales Invoice`
                            WHERE `docstatus` = 1
                            AND `ist_mitgliedschaftsrechnung` = 1
                            AND `mv_mitgliedschaft` = '{mitgliedschaft}'
                            AND `status` = 'Paid'
                            ORDER BY `mitgliedschafts_jahr` DESC""".format(mitgliedschaft=mitgliedschaft.name), as_dict=True)
    if len(sinvs) > 0:
        sinv = sinvs[0]
        sinv_year = cint(sinv.mitgliedschafts_jahr)
        if sinv.is_pos == 1:
            # Fallback wenn sinv.mitgliedschafts_jahr == 0
            if sinv_year < 1:
                sinv_year = getdate(sinv.posting_date).strftime("%Y")
            mitgliedschaft.datum_zahlung_mitgliedschaft = sinv.posting_date
        else:
            pes = frappe.db.sql("""SELECT
                                        `parent`
                                    FROM `tabPayment Entry Reference`
                                    WHERE `reference_doctype` = 'Sales Invoice'
                                    AND `reference_name` = '{sinv}' 
                                    AND `docstatus` = 1
                                    ORDER BY `creation` DESC""".format(sinv=sinv.name), as_dict=True)
            if len(pes) > 0:
                # pe = frappe.get_doc("Payment Entry", pes[0].parent)
                pe_reference_date = frappe.db.get_value("Payment Entry", pes[0].parent, 'reference_date')
                # # Fallback wenn sinv.mitgliedschafts_jahr == 0
                if sinv_year < 1:
                    sinv_year = getdate(pe_reference_date).strftime("%Y")
                mitgliedschaft.datum_zahlung_mitgliedschaft = pe_reference_date
                # self.datum_zahlung_mitgliedschaft = pe.reference_date
        
        if mitgliedschaft.bezahltes_mitgliedschaftsjahr < sinv_year:
            mitgliedschaft.bezahltes_mitgliedschaftsjahr = sinv_year
    
    # Zahldatum = Eintrittsdatum
    if mitgliedschaft.status_c in ('Anmeldung', 'Online-Anmeldung', 'Interessent*in') and mitgliedschaft.bezahltes_mitgliedschaftsjahr > 0:
        if noch_kein_eintritt:
            mitgliedschaft.eintrittsdatum = mitgliedschaft.datum_zahlung_mitgliedschaft
    
    if mitgliedschaft.bezahltes_mitgliedschaftsjahr > 0 and mitgliedschaft.status_c in ('Anmeldung', 'Online-Anmeldung', 'Interessent*in'):
        # erstelle status change log und Status-Änderung
        change_log_row = mitgliedschaft.append('status_change', {})
        change_log_row.datum = now()
        change_log_row.status_alt = mitgliedschaft.status_c
        change_log_row.status_neu = 'Regulär'
        change_log_row.grund = 'Zahlungseingang'
        mitgliedschaft.status_c = 'Regulär'
        
        # erstellung Begrüssungsschreiben
        mitgliedschaft.begruessung_massendruck = 1
        mitgliedschaft.begruessung_via_zahlung = 1
        druckvorlage = get_druckvorlagen(sektion=mitgliedschaft.sektion_id, \
                                         dokument='Begrüssung mit Ausweis', \
                                        mitgliedtyp=mitgliedschaft.mitgliedtyp_c, \
                                        language=mitgliedschaft.language)['default_druckvorlage']
        
        mitgliedschaft.begruessung_massendruck_dokument = create_korrespondenz(mitgliedschaft=mitgliedschaft.name, \
                                                                               druckvorlage=druckvorlage, \
                                                                               titel='Begrüssung (Autom.)')
    
    # prüfe offene Rechnungen bei sektionswechsel
    if mitgliedschaft.status_c == 'Wegzug':
        sinvs = frappe.db.sql("""SELECT
                                    `name`,
                                    `docstatus`
                                FROM `tabSales Invoice`
                                WHERE `docstatus` != 2
                                AND `ist_mitgliedschaftsrechnung` = 1
                                AND `mv_mitgliedschaft` = '{mitgliedschaft}'
                                AND `status` != 'Paid'""".format(mitgliedschaft=mitgliedschaft.name), as_dict=True)
        for sinv in sinvs:
            # sinv = frappe.get_doc("Sales Invoice", sinv.name)
            if sinv.docstatus == 1:
                # cancel linked FR
                linked_fr = frappe.db.sql("""SELECT
                                                `name`
                                            FROM `tabFakultative Rechnung`
                                            WHERE `sales_invoice` = '{sinv}'
                                            AND `docstatus` = 1""".format(sinv=sinv.name), as_dict=True)
                if len(linked_fr) > 0:
                    for _fr in linked_fr:
                        fr = frappe.get_doc("Fakultative Rechnung", _fr.name)
                        if fr.status == 'Paid':
                            fr.add_comment('Comment', text="Verknüpfung zu Rechnung {0} aufgrund Sektionswechsel aufgehoben".format(fr.sales_invoice))
                            frappe.db.set_value("Fakultative Rechnung", fr.name, 'sales_invoice', None)
                            # frappe.db.sql("""UPDATE `tabFakultative Rechnung` SET `sales_invoice` = '' WHERE `name` = '{0}'""".format(fr.name), as_list=True)
                        else:
                            fr.cancel()
                
                # cancel linked mahnungen
                linked_mahnungen = frappe.db.sql("""SELECT DISTINCT
                                                        `parent`
                                                    FROM `tabMahnung Invoices`
                                                    WHERE `sales_invoice` = '{sinv}'
                                                    AND `docstatus` = 1""".format(sinv=sinv.name), as_dict=True)
                if len(linked_mahnungen) > 0:
                    for _mahnung in linked_mahnungen:
                        mahnung = frappe.get_doc("Mahnung", _mahnung.parent)
                        mahnung.cancel()
                
                # load & cancel sinv
                sinv = frappe.get_doc("Sales Invoice", sinv.name)
                sinv.cancel()
            else:
                if sinv.docstatus == 0:
                    # load & delete sinv
                    sinv.delete()
    
    if external:
        mitgliedschaft.save()
    
    return

def set_max_reminder_level(mitgliedschaft):
    # mitgliedschaft = frappe.get_doc("Mitgliedschaft", sinv.mv_mitgliedschaft)
    # mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)
    
    try:
        sql_query = ("""SELECT MAX(`payment_reminder_level`) AS `max` FROM `tabSales Invoice` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}' AND `status` = 'Overdue' AND `docstatus` = 1""".format(mitgliedschaft=mitgliedschaft.name))
        max_level = frappe.db.sql(sql_query, as_dict=True)[0]['max']
        if not max_level:
            max_level = 0
    except:
        max_level = 0
    # sinv_max_level = cint(sinv.payment_reminder_level or 0)
    # if max_level < sinv_max_level:
    #     max_level = sinv_max_level
    mitgliedschaft.max_reminder_level = max_level
    # frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'max_reminder_level', max_level)
    # frappe.db.commit()

    # if external:
    #     mitgliedschaft.save(ignore_permissions=True)
    
    return

def get_ampelfarbe(mitgliedschaft, external=False):
    ''' mögliche Ampelfarben:
        - Grün: ampelgruen --> Mitglied kann alle Dienstleistungen beziehen (keine Karenzfristen, keine überfälligen oder offen Rechnungen)
        - Gelb: ampelgelb --> Karenzfristen oder offene Rechnungen
        - Rot: ampelrot --> überfällige offene Rechnungen
        
        MVZH Ausnahme:
        - Grün --> Jahr bezahlt >= aktuelles Jahr
        - Rot --> Jahr bezahlt < aktuelles Jahr
    '''
    
    if external:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitgliedschaft)

    if mitgliedschaft.status_c in ('Gestorben', 'Wegzug', 'Ausschluss', 'Inaktiv', 'Interessent*in'):
        ampelfarbe = 'ampelrot'
    else:
        
        # MVZH Ausnahme Start
        if mitgliedschaft.sektion_id == 'MVZH':
            if cint(mitgliedschaft.bezahltes_mitgliedschaftsjahr) < cint(datetime.date.today().year):
                ampelfarbe = 'ampelrot'
            else:
                ampelfarbe = 'ampelgruen'
        # MVZH Ausnahme Ende
        else:
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
    
    mitgliedschaft.ampel_farbe = ampelfarbe

    if external:
        mitgliedschaft.save()

    return

def sinv_update(sinv, event):
    if sinv.mv_mitgliedschaft:
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", sinv.mv_mitgliedschaft)
        mitgliedschaft.save()
    
    return

def check_mitgliedschaft_in_pe(pe, event):
    if not pe.mv_mitgliedschaft:
        mitgliedschaft = suche_nach_mitgliedschaft(pe.party)
        if mitgliedschaft:
            frappe.db.sql("""UPDATE `tabPayment Entry` SET `mv_mitgliedschaft` = '{mitgliedschaft}' WHERE `name` = '{pe}'""".format(mitgliedschaft=mitgliedschaft, pe=pe.name), as_list=True)
            frappe.db.commit()

def suche_nach_mitgliedschaft(customer):
    mitgliedschaften = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `kunde_mitglied` = '{customer}' OR `rg_kunde` = '{customer}'""".format(customer=customer), as_list=True)
    if len(mitgliedschaften) > 0:
        return mitgliedschaften[0][0]
    else:
        return False