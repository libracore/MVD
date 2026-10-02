# -*- coding: utf-8 -*-
# Copyright (c) 2021-2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe.utils.data import add_days, getdate, now
import datetime
from mvd.mvd.doctype.druckvorlage.druckvorlage import get_druckvorlagen
from mvd.mvd.doctype.mitgliedschaft.utils import create_korrespondenz, sp_updater
from frappe.utils.background_jobs import enqueue
from mvd.mvd.utils import is_job_already_running
from frappe.utils.pdf import get_pdf
from mvd.mvd.doctype.mitgliedschaft.process_utils.update_zahlungsdaten import run as run_update_zahlungsdaten

def cancel_sinv_fak_sektionswechsel(mitgliedschaft):
    sinvs = frappe.db.sql("""SELECT
                                    `name`,
                                    `docstatus`
                                FROM `tabSales Invoice`
                                WHERE `docstatus` != 2
                                AND `ist_mitgliedschaftsrechnung` = 1
                                AND `mv_mitgliedschaft` = '{mitgliedschaft}'
                                AND `status` != 'Paid'""".format(mitgliedschaft=mitgliedschaft), as_dict=True)
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

def set_max_reminder_level(mitgliedschaft, db_direct=False):
    '''
        mitgliedschaft -> Muss immer einem Objekt entsprechen!
    
        db_direct -> Ist dieser Parameter gesetzt, so werden die Werte mittels db.set_value direkt in die DB geschrieben.
        Dadurch können die Werte aktualisiert werden, ohne dass die gesamte Mitgliedschaft gespeichert werden muss (Performance verbesserung).
    '''
    try:
        sql_query = ("""SELECT MAX(`payment_reminder_level`) AS `max` FROM `tabSales Invoice` WHERE `mv_mitgliedschaft` = '{mitgliedschaft}' AND `status` = 'Overdue' AND `docstatus` = 1""".format(mitgliedschaft=mitgliedschaft.name))
        max_level = frappe.db.sql(sql_query, as_dict=True)[0]['max']
        if not max_level:
            max_level = 0
    except:
        max_level = 0
    mitgliedschaft.max_reminder_level = max_level
    if db_direct:
        frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'max_reminder_level', max_level)
    
    if db_direct:
        frappe.db.commit()
    
    return

def check_folgejahr_regelung(mitgliedschaft, db_direct=False):
    '''
        mitgliedschaft -> Muss immer einem Objekt entsprechen!
    
        db_direct -> Ist dieser Parameter gesetzt, so werden die Werte mittels db.set_value direkt in die DB geschrieben.
        Dadurch können die Werte aktualisiert werden, ohne dass die gesamte Mitgliedschaft gespeichert werden muss (Performance verbesserung).
    '''
    # prüfe ob Folgejahr Regelung der Sektion aktiviert ist:
    if cint(frappe.get_value("Sektion", mitgliedschaft.sektion_id, "folgejahr_regelung")) == 1:
        if mitgliedschaft.datum_zahlung_mitgliedschaft:
        # prüfe Mitgliedschaftsjahr
            datum_zahlung_mitgliedschaft = getdate(mitgliedschaft.datum_zahlung_mitgliedschaft)
            jahr_datum_zahlung_mitgliedschaft = cint(datum_zahlung_mitgliedschaft.strftime("%Y"))
            bezahltes_mitgliedschaftsjahr = cint(mitgliedschaft.bezahltes_mitgliedschaftsjahr)
            
            if bezahltes_mitgliedschaftsjahr == jahr_datum_zahlung_mitgliedschaft:
                current_year = str(now().split("-")[0])
                eintrittsjahr = cint(getdate(mitgliedschaft.eintrittsdatum).strftime("%Y"))
                if cint(current_year) == eintrittsjahr:
                    if datum_zahlung_mitgliedschaft >= getdate(current_year + '-09-15') and datum_zahlung_mitgliedschaft <= getdate(current_year + '-12-31'):
                        bezahltes_mitgliedschaftsjahr_neu = mitgliedschaft.bezahltes_mitgliedschaftsjahr + 1
                        mitgliedschaft.bezahltes_mitgliedschaftsjahr = bezahltes_mitgliedschaftsjahr_neu
                        if db_direct:
                            frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'bezahltes_mitgliedschaftsjahr', bezahltes_mitgliedschaftsjahr_neu)
        
        if mitgliedschaft.datum_hv_zahlung:
            # prüfe HV-Jahr
            datum_hv_zahlung = getdate(mitgliedschaft.datum_hv_zahlung)
            jahr_datum_hv_zahlung = cint(datum_hv_zahlung.strftime("%Y"))
            zahlung_hv = cint(mitgliedschaft.zahlung_hv)
            
            current_year = str(now().split("-")[0])
            eintrittsjahr = cint(getdate(mitgliedschaft.eintrittsdatum).strftime("%Y"))
            if cint(current_year) == eintrittsjahr:
                if zahlung_hv == jahr_datum_hv_zahlung:
                    current_year = str(now().split("-")[0])
                    if datum_hv_zahlung >= getdate(current_year + '-09-15') and datum_hv_zahlung <= getdate(current_year + '-12-31'):
                        zahlung_hv_neu = mitgliedschaft.zahlung_hv + 1
                        mitgliedschaft.zahlung_hv = zahlung_hv_neu
                        if db_direct:
                            frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'zahlung_hv', zahlung_hv_neu)
    if db_direct:
        frappe.db.commit()
    
    return

def sinv_update(sinv, event):
    update_blocked = False
    if "create_mitgliedschaftsrechnung_block" in sinv.flags and sinv.flags['create_mitgliedschaftsrechnung_block']:
        update_blocked = True
    
    old_sinv = sinv.get_doc_before_save()
    if old_sinv:
        if old_sinv.status and old_sinv.status == sinv.status:
            update_blocked = True
            if old_sinv.outstanding_amount == 0.0:
                items = frappe.get_all(
                    "Sales Invoice Item",
                    filters={"parent": sinv.name},
                    fields=["name", "amount"]
                )
                total_amount = sum(item["amount"] for item in items)
                payments = frappe.get_all(
                    "Sales Invoice Payment",
                    filters={"parent": sinv.name},
                    fields=["name"]
                )
                # Only update if exactly one payment row exists
                if len(payments) == 1:
                    frappe.db.set_value("Sales Invoice Payment", payments[0]["name"], "amount", total_amount)
                    frappe.db.set_value("Sales Invoice Payment", payments[0]["name"], "base_amount", total_amount)
                    frappe.db.set_value("Sales Invoice", sinv.name, "outstanding_amount", 0.0)

    if not update_blocked and sinv.mv_mitgliedschaft:
        run_update_zahlungsdaten(sinv.mv_mitgliedschaft)

    return

def check_mitgliedschaft_in_pe(pe):
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

def create_zahlungseingang_change_log_row(mitgliedschaft, status_alt):
    idx = len(mitgliedschaft.status_change) + 1
    change_log_row = frappe.get_doc({
        "doctype": "Status Change",
        "parent": mitgliedschaft.name,
        "parentfield": "status_change",
        "parenttype": "Mitgliedschaft",
        "datum": now(),
        "status_alt": status_alt,
        "status_neu": 'Regulär',
        "grund": 'Zahlungseingang',
        "idx": idx
    }).insert()
    return

def get_and_set_mitgliednr(mitgliedId):
    from mvd.mvd.doctype.mitglied_main_naming.mitglied_main_naming import create_new_number
    try:
        mitgliedNr = create_new_number(id=mitgliedId)['nr']
        frappe.db.set_value("Mitgliedschaft", mitgliedId, 'mitglied_nr', mitgliedNr)
    except Exception as err:
        frappe.log_error("Mitgliednummer für Mitglied {0} konnte nicht bezogen werden".format(mitgliedId), 'get_and_set_mitgliednr')
        pass
    return

@frappe.whitelist()
def quittung_drucken(sales_invoice):
    sinv = frappe.get_doc("Sales Invoice", sales_invoice)

    payment_entry_name = frappe.db.get_value(
        "Payment Entry Reference",
        {"reference_doctype": "Sales Invoice", "reference_name": sales_invoice, "docstatus": 1},
        "parent"
    )

    if payment_entry_name:
        zahlungsdatum = frappe.db.get_value("Payment Entry", payment_entry_name, "posting_date")
    else:
        zahlungsdatum = None

    html = frappe.render_template(
        'templates/mvd/mvzh/quittung.html',
        {
            "doc": sinv,
            "zahlungsdatum": zahlungsdatum
        }
    )

    pdf = get_pdf(html)

    frappe.local.response.filename = "Quittung_{0}.pdf".format(sales_invoice)
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"
    frappe.local.response.content_type = "application/pdf"
