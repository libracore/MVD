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

def check_zahlung_mitgliedschaft(mitgliedschaft, db_direct=False):
    '''
        mitgliedschaft -> Muss immer einem Objekt entsprechen!
    
        db_direct -> Ist dieser Parameter gesetzt, so werden die Werte mittels db.set_value direkt in die DB geschrieben.
        Dadurch können die Werte aktualisiert werden, ohne dass die gesamte Mitgliedschaft gespeichert werden muss (Performance verbesserung).
    '''
    
    noch_kein_eintritt = False
    if not mitgliedschaft.datum_zahlung_mitgliedschaft:
        noch_kein_eintritt = True
    
    # Muss zwingend vorgängig Commitet werden, damit die aktuellen und benötigten Info's in der DB verfügbar sind
    # Siehe #1475
    frappe.db.commit()

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
            if db_direct:
                frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'datum_zahlung_mitgliedschaft', sinv.posting_date)
        else:
            pes = frappe.db.sql("""SELECT
                                        `parent`
                                    FROM `tabPayment Entry Reference`
                                    WHERE `reference_doctype` = 'Sales Invoice'
                                    AND `reference_name` = '{sinv}' 
                                    AND `docstatus` = 1
                                    ORDER BY `creation` DESC""".format(sinv=sinv.name), as_dict=True)
            if len(pes) > 0:
                pe_reference_date = frappe.db.get_value("Payment Entry", pes[0].parent, 'reference_date')
                # # Fallback wenn sinv.mitgliedschafts_jahr == 0
                if sinv_year < 1:
                    sinv_year = getdate(pe_reference_date).strftime("%Y")
                
                mitgliedschaft.datum_zahlung_mitgliedschaft = pe_reference_date
                if db_direct:
                    frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'datum_zahlung_mitgliedschaft', pe_reference_date)
        
        if mitgliedschaft.bezahltes_mitgliedschaftsjahr < sinv_year:
            mitgliedschaft.bezahltes_mitgliedschaftsjahr = sinv_year
            if db_direct:
                frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'bezahltes_mitgliedschaftsjahr', sinv_year)
    
    # Zahldatum = Eintrittsdatum
    if mitgliedschaft.status_c in ('Anmeldung', 'Online-Anmeldung', 'Interessent*in') and mitgliedschaft.bezahltes_mitgliedschaftsjahr > 0:
        if noch_kein_eintritt:
            mitgliedschaft.eintrittsdatum = mitgliedschaft.datum_zahlung_mitgliedschaft
            if db_direct:
                frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'eintrittsdatum', mitgliedschaft.datum_zahlung_mitgliedschaft)
    
    if mitgliedschaft.bezahltes_mitgliedschaftsjahr > 0 and mitgliedschaft.status_c in ('Anmeldung', 'Online-Anmeldung', 'Interessent*in'):
        # erstelle status change log und Status-Änderung
        druckvorlage = get_druckvorlagen(sektion=mitgliedschaft.sektion_id, \
                                            dokument='Begrüssung mit Ausweis', \
                                            mitgliedtyp=mitgliedschaft.mitgliedtyp_c, \
                                            language=mitgliedschaft.language)['default_druckvorlage']
            
        begruessung_massendruck_dokument = create_korrespondenz(mitgliedschaft=mitgliedschaft.name, \
                                                                            druckvorlage=druckvorlage, \
                                                                            titel='Begrüssung (Autom.)')
        if not db_direct:
            change_log_row = mitgliedschaft.append('status_change', {})
            change_log_row.datum = now()
            change_log_row.status_alt = mitgliedschaft.status_c
            change_log_row.status_neu = 'Regulär'
            change_log_row.grund = 'Zahlungseingang'
            mitgliedschaft.status_c = 'Regulär'
            
            # erstellung Begrüssungsschreiben
            mitgliedschaft.begruessung_massendruck = 1
            mitgliedschaft.begruessung_via_zahlung = 1
            mitgliedschaft.begruessung_massendruck_dokument = begruessung_massendruck_dokument
            
        else:
            create_zahlungseingang_change_log_row(mitgliedschaft, mitgliedschaft.status_c)
            frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'status_c', 'Regulär')
            frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'begruessung_massendruck', 1)
            frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'begruessung_via_zahlung', 1)
            frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'begruessung_massendruck_dokument', begruessung_massendruck_dokument)
            get_and_set_mitgliednr(mitgliedschaft.name)
    
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
    
    if db_direct:
        frappe.db.commit()
    
    return

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

def get_ampelfarbe(mitgliedschaft, db_direct=False):
    ''' mögliche Ampelfarben:
        - Grün: ampelgruen --> Mitglied kann alle Dienstleistungen beziehen (keine Karenzfristen, keine überfälligen oder offen Rechnungen)
        - Gelb: ampelgelb --> Karenzfristen oder offene Rechnungen
        - Rot: ampelrot --> überfällige offene Rechnungen
        
        MVZH Ausnahme:
        - Grün --> Jahr bezahlt >= aktuelles Jahr
        - Rot --> Jahr bezahlt < aktuelles Jahr
        ---------------------------------------------------------
        mitgliedschaft -> Muss immer einem Objekt entsprechen!
    
        db_direct -> Ist dieser Parameter gesetzt, so werden die Werte mittels db.set_value direkt in die DB geschrieben.
        Dadurch können die Werte aktualisiert werden, ohne dass die gesamte Mitgliedschaft gespeichert werden muss (Performance verbesserung).
    '''

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
    if db_direct:
        frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'ampel_farbe', ampelfarbe)
        frappe.db.commit()
    
    return

def check_zahlung_hv(mitgliedschaft, db_direct=False):
    '''
        mitgliedschaft -> Muss immer einem Objekt entsprechen!
    
        db_direct -> Ist dieser Parameter gesetzt, so werden die Werte mittels db.set_value direkt in die DB geschrieben.
        Dadurch können die Werte aktualisiert werden, ohne dass die gesamte Mitgliedschaft gespeichert werden muss (Performance verbesserung).
    '''

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
                            ORDER BY `posting_date` DESC""".format(mvm=mitgliedschaft.name), as_dict=True)
    if len(sinvs) > 0:
        sinv = sinvs[0]
        if sinv.is_pos == 1:
            sinv_year = sinv.mitgliedschafts_jahr if sinv.mitgliedschafts_jahr and sinv.mitgliedschafts_jahr > 0 else getdate(sinv.posting_date).strftime("%Y")
            mitgliedschaft.datum_hv_zahlung = sinv.posting_date
            if db_direct:
                frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'datum_hv_zahlung', sinv.posting_date)
        else:
            pes = frappe.db.sql("""SELECT `parent` FROM `tabPayment Entry Reference`
                                    WHERE `reference_doctype` = 'Sales Invoice'
                                    AND `reference_name` = '{sinv}' ORDER BY `creation` DESC""".format(sinv=sinv.name), as_dict=True)
            if len(pes) > 0:
                pe = frappe.get_doc("Payment Entry", pes[0].parent)
                sinv_year = sinv.mitgliedschafts_jahr if sinv.mitgliedschafts_jahr and sinv.mitgliedschafts_jahr > 0 else getdate(pe.reference_date).strftime("%Y")
                mitgliedschaft.datum_hv_zahlung = pe.reference_date
                if db_direct:
                    frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'datum_hv_zahlung', pe.reference_date)
        
        mitgliedschaft.zahlung_hv = sinv_year
        if db_direct:
            frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'zahlung_hv', sinv_year)
    
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

    if not update_blocked:
        if sinv.mv_mitgliedschaft and not is_job_already_running('Aktualisiere Mitgliedschaft {0}'.format(sinv.mv_mitgliedschaft)):
            args = {
                'mv_mitgliedschaft': sinv.mv_mitgliedschaft
            }
            enqueue("mvd.mvd.doctype.mitgliedschaft.finance_utils._sinv_update", queue='short', job_name='Aktualisiere Mitgliedschaft {0}'.format(sinv.mv_mitgliedschaft), timeout=5000, **args)
    return

def _sinv_update(mv_mitgliedschaft, timestamp_missmatch=0, does_not_exist=0, dead_lock=0):
    import pymysql

    def get_retry_stats():
        return "TimeStampMissMatch: {0}\nDoesNotExist: {1}\nDeadLock: {2}".format(timestamp_missmatch, does_not_exist, dead_lock)
    def get_error_log_description(step, err):
        return "Mitglied-ID: {0}\nWorkflow-State: {1}\nFehler: {2}\nRetry-Stats:\n{3}\nTraceBack:\n{4}".format(mv_mitgliedschaft, step, str(err), get_retry_stats(), frappe.get_traceback())
    
    try:
        # Speichern der Mitgliedschaft zum triggern der validate() Funktion, diese aktualisiert alle relevanten Informationen rund um das Mitglied
        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mv_mitgliedschaft)
        mitgliedschaft.save(ignore_permissions=True)
    except frappe.TimestampMismatchError as err:
        # Möglicher Fehler 1: Zwei Prozesse Bearbeiten/Speichern gleichzeitig -> Konflikt -> Retry
        # Es werden maximal 3 Versuche zugelassen -> Danach Abbruch & ErrorLog
        if timestamp_missmatch < 3:
            timestamp_missmatch += 1
            if not is_job_already_running('Aktualisiere Mitgliedschaft {0}'.format(mv_mitgliedschaft)):
                frappe.clear_messages()
                args = {
                    'mv_mitgliedschaft': mv_mitgliedschaft,
                    'timestamp_missmatch': timestamp_missmatch,
                    'does_not_exist': does_not_exist,
                    'dead_lock': dead_lock
                }
                enqueue("mvd.mvd.doctype.mitgliedschaft.finance_utils._sinv_update", queue='short', job_name='Aktualisiere Mitgliedschaft {0}'.format(mv_mitgliedschaft), timeout=5000, **args)
            pass
        else:
            frappe.log_error(get_error_log_description("TimeStampMissMatch", err), '_sinv_update Failed')
            frappe.clear_messages()
            pass
    except frappe.exceptions.DoesNotExistError as err2:
        # Möglicher Fehler 2: Die Mitgliedschaft existiert noch nicht -> Retry in der Hoffnung dass die Anlage in der Zwischenzeit erfolgt ist
        # Es werden maximal 3 Versuche zugelassen -> Danach Abbruch & ErrorLog
        if does_not_exist < 3:
            does_not_exist += 1
            if not is_job_already_running('Aktualisiere Mitgliedschaft {0}'.format(mv_mitgliedschaft)):
                frappe.clear_messages()
                args = {
                    'mv_mitgliedschaft': mv_mitgliedschaft,
                    'timestamp_missmatch': timestamp_missmatch,
                    'does_not_exist': does_not_exist,
                    'dead_lock': dead_lock
                }
                enqueue("mvd.mvd.doctype.mitgliedschaft.finance_utils._sinv_update", queue='short', job_name='Aktualisiere Mitgliedschaft {0}'.format(mv_mitgliedschaft), timeout=5000, **args)
            pass
        else:
            frappe.log_error(get_error_log_description("DoesNotExist", err2), '_sinv_update Failed')
            frappe.clear_messages()
            pass
    except pymysql.err.OperationalError as err3:
        if err3.args and err3.args[0] == 1205:
            # Möglicher Fehler 3: Die DB-Tabelle die gespeichert werden soll ist gesperrt -> Retry
            # Es werden maximal 3 Versuche zugelassen -> Danach Abbruch & ErrorLog
            if dead_lock < 3:
                dead_lock += 1
                if not is_job_already_running('Aktualisiere Mitgliedschaft {0}'.format(mv_mitgliedschaft)):
                    frappe.clear_messages()
                    args = {
                        'mv_mitgliedschaft': mv_mitgliedschaft,
                        'timestamp_missmatch': timestamp_missmatch,
                        'does_not_exist': does_not_exist,
                        'dead_lock': dead_lock
                    }
                    enqueue("mvd.mvd.doctype.mitgliedschaft.finance_utils._sinv_update", queue='short', job_name='Aktualisiere Mitgliedschaft {0}'.format(mv_mitgliedschaft), timeout=5000, **args)
                pass
            else:
                frappe.log_error(get_error_log_description("DeadLock", err3), '_sinv_update Failed')
                frappe.clear_messages()
                pass
        else:
            # Möglicher Fehler 4: Sonstiger DB-Fehler -> Abbruch & ErrorLog
            frappe.log_error(get_error_log_description("DB", err3), '_sinv_update Failed')
            frappe.clear_messages()
            pass
    except Exception as err4:
        # Möglicher Fehler 5: Sonstiger Fehler -> Abbruch & ErrorLog
        frappe.log_error(get_error_log_description("Unhandled Exception", err4), '_sinv_update Failed')
        frappe.clear_messages()
        pass

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