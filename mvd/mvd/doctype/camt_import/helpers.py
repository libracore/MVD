# -*- coding: utf-8 -*-
# Copyright (c) 2022-2026, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from bs4 import BeautifulSoup
import six
import json
import os
from urllib.parse import quote
from frappe.utils.data import today, cint, escape_html

def get_camt_file(file_path, test=False):
    prefixes = ('/private/files/', '/files/')
    if not file_path or not any(file_path.startswith(prefix) for prefix in prefixes):
        raise frappe.ValidationError('Bitte wählen Sie eine lokal hochgeladene CAMT-Datei aus.')
    
    prefix = next(prefix for prefix in prefixes if file_path.startswith(prefix))
    directory = os.path.realpath(frappe.get_site_path(prefix.strip('/')))
    physical_path = os.path.realpath(os.path.join(directory, file_path[len(prefix):]))

    if not physical_path.startswith(directory + os.sep):
        raise frappe.ValidationError('Der Pfad der CAMT-Datei liegt ausserhalb des Dateiordners.')
    
    try:
        with open(physical_path, 'rb') as f:
            content = f.read()
    except FileNotFoundError:
        raise frappe.ValidationError('Die CAMT-Datei {0} ist auf diesem System nicht vorhanden. Bitte stellen Sie die Datei aus einer Sicherung wieder her oder laden Sie sie erneut hoch.'.format(file_path))
    except OSError:
        raise frappe.ValidationError('Die CAMT-Datei {0} konnte nicht gelesen werden. Bitte prüfen Sie die Datei und ihre Leseberechtigung.'.format(file_path))
    
    soup = BeautifulSoup(content, 'lxml')
    if soup.document is None or soup.document.bktocstmrdbtcdtntfctn is None:
        raise frappe.ValidationError('Die Datei {0} enthält keine unterstützte CAMT-Meldung.'.format(file_path))
    
    # Die IBAN-Prüfung erfolgt separat und kann im Import ausdrücklich übersprungen werden.
    return True if test else soup

def pruefe_camt_iban(camt_file, camt_import):
    if cint(camt_import.get('ignoriere_iban_abweichung')):
        return

    if not camt_import.account:
        frappe.throw("Bitte wählen Sie im CAMT-Import zuerst ein Bankkonto aus.")
    
    konto_iban = frappe.db.get_value('Account', camt_import.account, 'iban')
    normalisierte_konto_iban = ''.join((konto_iban or '').split()).upper()
    if not normalisierte_konto_iban:
        frappe.throw('Beim gewählten Bankkonto {0} ist keine IBAN hinterlegt. Bitte ergänzen Sie die IBAN oder aktivieren Sie "IBAN-Abweichung ignorieren".'.format(escape_html(camt_import.account)))

    # Alle Kontoabschnitte prüfen
    kontoabschnitte = camt_file.find_all('ntfctn')
    if not kontoabschnitte:
        frappe.throw("Das CAMT-File enthält keine Kontoangaben für den IBAN-Abgleich.")
    
    for kontoabschnitt in kontoabschnitte:
        konto = kontoabschnitt.find('acct', recursive=False)
        iban = konto.find('iban') if konto is not None else None
        camt_iban = iban.get_text().strip() if iban is not None else ''

        if not camt_iban:
            frappe.throw('Ein Kontoabschnitt im CAMT-File enthält keine IBAN. Bitte prüfen Sie die Datei oder aktivieren Sie "IBAN-Abweichung ignorieren".')
        
        if ''.join(camt_iban.split()).upper() != normalisierte_konto_iban:
            frappe.throw('Die IBAN im CAMT-File ({0}) stimmt nicht mit der IBAN des gewählten Bankkontos {1} ({2}) überein. Es wurden keine Zahlungen eingelesen. Bitte wählen Sie das passende Bankkonto oder aktivieren Sie "IBAN-Abweichung ignorieren".'.format(
                    escape_html(camt_iban), escape_html(camt_import.account), escape_html(konto_iban)
                )
            )

def get_default_customer(sektion):
    default_customer = frappe.get_doc("Sektion", sektion).default_customer
    return default_customer

def camt_status_update(camt_import, status):
    frappe.db.set_value('CAMT Import', camt_import, 'status', status)

def erfasse_rg_match(camt_import):
    new_rg_match_qty = frappe.db.get_value('CAMT Import', camt_import, 'rg_match_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'rg_match_qty', new_rg_match_qty)

def erfasse_ausgelesene_zahlungen(transaction_reference, unique_reference, date, received_amount, camt_import):
    ausgelesene_zahlungen = frappe.db.get_value('CAMT Import', camt_import, 'ausgelesene_zahlungen')
    qty = frappe.db.get_value('CAMT Import', camt_import, 'ausgelesene_zahlungen_qty') + 1
    if ausgelesene_zahlungen:
        ausgelesene_zahlungen += '\n{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    else:
        ausgelesene_zahlungen = '{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    frappe.db.set_value('CAMT Import', camt_import, 'ausgelesene_zahlungen', ausgelesene_zahlungen)
    frappe.db.set_value('CAMT Import', camt_import, 'ausgelesene_zahlungen_qty', qty)

def erfasse_eingelesene_zahlungen(transaction_reference, unique_reference, date, received_amount, camt_import):
    eingelesene_zahlungen = frappe.db.get_value('CAMT Import', camt_import, 'eingelesene_zahlungen')
    qty = frappe.db.get_value('CAMT Import', camt_import, 'eingelesene_zahlungen_qty') + 1
    if eingelesene_zahlungen:
        eingelesene_zahlungen += '\n{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    else:
        eingelesene_zahlungen = '{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    frappe.db.set_value('CAMT Import', camt_import, 'eingelesene_zahlungen', eingelesene_zahlungen)
    frappe.db.set_value('CAMT Import', camt_import, 'eingelesene_zahlungen_qty', qty)
    no_match_qty = frappe.db.get_value('CAMT Import', camt_import, 'anz_unmatched_payments') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'anz_unmatched_payments', no_match_qty)

def erfasse_nicht_eingelesene_zahlungen(transaction_reference, unique_reference, date, received_amount, camt_import):
    nicht_eingelesene_zahlungen = frappe.db.get_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen')
    qty = frappe.db.get_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen_qty') + 1
    if nicht_eingelesene_zahlungen:
        nicht_eingelesene_zahlungen += '\n{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    else:
        nicht_eingelesene_zahlungen = '{0} ({1}): {2} / {3}'.format(transaction_reference, unique_reference, date, received_amount)
    frappe.db.set_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen', nicht_eingelesene_zahlungen)
    frappe.db.set_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen_qty', qty)

def entferne_nicht_eingelesene_zahlungen(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen_qty') - 1
    frappe.db.set_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen_qty', qty)

def bereinige_nachgeladene_zahlung(camt_import, transaction_id):
    """
        Sicherstellung, dass nachgeladene Files bereits aufgetretene Fehler statistisch nicht doppelt behandeln,
        sprich weder doppelt dazuzählen noch abziehen
    """
    daten = frappe.db.get_value('CAMT Import', camt_import, [
        'nicht_eingelesene_zahlungen',
        'nicht_eingelesene_zahlungen_qty',
        'fehlgeschlagenes_auslesen',
        'fehlgeschlagenes_auslesen_qty'
    ], as_dict=True)
    updates = {}
    markierung = 'Nachgeladen: '

    # Bereits vorhandene Zahlungen (Bankreferenzen) die als nicht eingelesen erfasst wurden
    zeilen = (daten['nicht_eingelesene_zahlungen'] or '').splitlines()
    for index, zeile in enumerate(zeilen):
        if zeile.startswith(markierung):
            continue

        # Bankreferenz am Ende vor Datum/Betrag vergleichen, da der Zahlungszweck Klammern stehen könnte
        referenz_teil = zeile.rpartition('): ')[0]
        if referenz_teil.endswith(' ({0}'.format(transaction_id)):
            zeilen[index] = markierung + zeile
            updates['nicht_eingelesene_zahlungen'] = '\n'.join(zeilen)
            updates['nicht_eingelesene_zahlungen_qty'] = max(0, (daten['nicht_eingelesene_zahlungen_qty'] or 0) - 1)
            break

    # Insert-Fehler (z.B. DB-Sperren)
    separator = '-----------------------------'
    fehler = (daten['fehlgeschlagenes_auslesen'] or '').split(separator)
    erledigt = 0
    for index, eintrag in enumerate(fehler):
        if not eintrag.strip() or eintrag.lstrip().startswith(markierung):
            continue

        transaction = BeautifulSoup(eintrag, 'lxml').find('txdtls')
        referenz = transaction.find('acctsvcrref') if transaction else None
        if referenz is not None and referenz.get_text() == transaction_id:
            fehler[index] = '\n{0}{1}\n{2}'.format(markierung, transaction_id, eintrag)
            erledigt += 1

    if erledigt:
        updates['fehlgeschlagenes_auslesen'] = separator.join(fehler)
        updates['fehlgeschlagenes_auslesen_qty'] = max(0, (daten['fehlgeschlagenes_auslesen_qty'] or 0) - erledigt)

    if updates:
        frappe.db.set_value('CAMT Import', camt_import, updates)

def erfasse_fehlgeschlagenes_auslesen(transaction, err, camt_import):
    fehlgeschlagenes_auslesen = frappe.db.get_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen')
    qty = frappe.db.get_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen_qty') + 1
    if fehlgeschlagenes_auslesen:
        fehlgeschlagenes_auslesen += '\n{0}\n{1}\n-----------------------------'.format(transaction, err)
    else:
        fehlgeschlagenes_auslesen = '{0}\n{1}\n-----------------------------'.format(transaction, err)
    frappe.db.set_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen', fehlgeschlagenes_auslesen)
    frappe.db.set_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen_qty', qty)


def get_offene_einlesefehler(camt_import):
    fehler = cint(frappe.db.get_value('CAMT Import', camt_import, 'fehlgeschlagenes_auslesen_qty'))
    if fehler > 0:
        fehler += min(0, cint(frappe.db.get_value('CAMT Import', camt_import, 'nicht_eingelesene_zahlungen_qty')))
    
    return max(0, fehler)

def get_matching_bankkonto(rechnung):
    bankkonto = rechnung.get('rechnungs_bankkonto')
    sektion = rechnung.get('sektion_id') or rechnung.get('sektion')

    if not bankkonto and sektion:
        bankkonto = frappe.get_cached_value('Sektion', sektion, 'account')
    
    return bankkonto

def get_matching_abweichung(rechnung, camt_import):
    if camt_import is None:
        return None
    
    abweichungen = []
    for label, rechnungswert, importwert in [
        ('Firma', rechnung.get('company'), camt_import.company),
        ('Sektion', rechnung.get('sektion_id') or rechnung.get('sektion'), camt_import.sektion_id),
        ('Bankkonto', get_matching_bankkonto(rechnung), camt_import.account)
    ]:
        if not rechnungswert or rechnungswert != importwert:
            abweichungen.append({'feld': label, 'rechnung': rechnungswert, 'camt_import': importwert})
    
    if abweichungen:
        return {
            'reference_doctype': rechnung.get('doctype') or 'Sales Invoice',
            'reference_name': rechnung.get('sinv') or rechnung.get('name'),
            'matching_abweichungen': abweichungen
        }

    return None

def sinv_lookup(qrr_ref, betrag, QRR_SINVS, camt_import=None):
    """
    Diese Funktion sucht nach gebuchten Sales Invoices anhand der QRR-Referenznummer aus der CAMT-Zahlung
    
    Mögliche Antwort Cases:
    -----------------------
    - Check: True & info: Sinv Match
        -> Zahlung wird erstellt und gegen Sinv verbucht (insofern Sinv unbezahlt)
    
    - Check: False & info: Multi-Sinvs
        -> Unzugewiesene Zahlung wird erstellt
    
    - Check: False & info: No Sinvs
        -> Unzugewiesene Zahlung wird erstellt
    
    - Check: False & info: Paid Fak
        -> Zugewiesene, aber unverbuchte Zahlung wird erstellt
    """

    if qrr_ref in QRR_SINVS:
        rechnung = QRR_SINVS[qrr_ref]
        return get_matching_abweichung(rechnung, camt_import) or rechnung
    else:
        # sinv nicht gefunden, starte suche nach Fakultativer Rechnung
        return fak_lookup(qrr_ref, betrag, camt_import=camt_import)

def fak_lookup(qrr_ref, betrag, camt_import=None):
    """
    Diese Funktion sucht nach gebuchten Fakultativen Rechnungen anhand der QRR-Referenznummer aus der CAMT-Zahlung
    """
    faks = frappe.db.sql("""SELECT *
                            FROM `tabFakultative Rechnung`
                            WHERE `docstatus` = 1
                            AND REPLACE(`qrr_referenz`, ' ', '') = '{qrr_ref}'
                            AND `status` = 'Unpaid'""".format(qrr_ref=qrr_ref), as_dict=True)
    
    if len(faks) > 0:
        # FK gefunden
        if len(faks) > 1:
            # mehere Fakultative Rechungen gefunden -> erzeuge unzugewiesene Zahlung
            return False
        else:
            # unique match -> umwandlung Fakultative Rechnung in Sales Invoice
            from mvd.mvd.doctype.camt_import.utils import create_unpaid_sinv
            return create_unpaid_sinv(faks[0].name, betrag, camt_import=camt_import)
    else:
        # FK nicht gefunden -> erzeuge unzugewiesene Zahlung
        return False

def get_matching_abweichungen_report(camt_import):
    daten = frappe.db.get_value('CAMT Import', camt_import, 'matching_abweichungen')
    abweichungen = json.loads(daten) if daten else []
    if not abweichungen:
        return ''

    offene_zahlungen = frappe.get_all(
        'Payment Entry', filters={
            'camt_import': camt_import,
            'name': ['in', [eintrag['payment_entry'] for eintrag in abweichungen]],
            'docstatus': 0
        },
        fields=['name']
    )

    offene_namen = set(zahlung.name for zahlung in offene_zahlungen)
    zeilen = []

    for eintrag in abweichungen:
        if eintrag['payment_entry'] not in offene_namen:
            continue

        details = '<br>'.join('{0}: Rechnung = {1}; CAMT-Import = {2}'.format(
            escape_html(abweichung['feld']), escape_html(abweichung['rechnung'] or 'nicht hinterlegt'),
            escape_html(abweichung['camt_import'] or 'nicht hinterlegt'))
            for abweichung in eintrag['matching_abweichungen'])

        zeilen.append('<tr><td><a href="/desk#Form/Payment Entry/{0}">{1}</a></td>'
                      '<td><a href="/desk#Form/{2}/{3}">{4}</a></td><td>{5}</td></tr>'.format(
                          quote(eintrag['payment_entry'], safe=''), escape_html(eintrag['payment_entry']),
                          quote(eintrag['reference_doctype'], safe=''), quote(eintrag['reference_name'], safe=''),
                          escape_html(eintrag['reference_name']), details))
    if not zeilen:
        return ''
    
    return ('<h3>Beim Matching ausgelassene Zahlungen wegen Abweichungen ({0})</h3>'
            '<table class="table table-bordered"><thead><tr><th>Zahlung</th><th>Rechnung</th>'
            '<th>Abweichungen</th></tr></thead><tbody>{1}</tbody></table>').format(len(zeilen), ''.join(zeilen))

def get_verrechnungen_report(zahlungen):
    if not zahlungen:
        return ''
    
    rows = []
    for pe in zahlungen:
        rows.append('<tr><td><a href="/desk#Form/Payment Entry/{0}">{1}</a></td>'
                    '<td>{2}</td><td><a href="/desk#Form/Journal Entry/{3}">{4}</a></td>'
                    '<td><a href="/desk#Form/Sales Invoice/{5}">{6}</a></td><td>{7:.2f}</td></tr>'.format(
                        quote(pe.name, safe=''), escape_html(pe.name), escape_html(pe.paid_to),
                        quote(pe.camt_verrechnung_journal, safe=''), escape_html(pe.camt_verrechnung_journal),
                        quote(pe.camt_verrechnung_rechnung, safe=''), escape_html(pe.camt_verrechnung_rechnung), pe.paid_amount))
    
    return ('<h3>Firmenverrechnungen</h3><p>Der Bankeingang ist bei der Importfirma gebucht. '
            'Die Gegenbuchung verrechnet den Betrag mit der Rechnung der anderen Firma. Ein Bankübertrag wurde nicht erfasst.</p>'
            '<table class="table table-bordered"><thead><tr><th>Zahlung</th><th>Eingangskonto</th>'
            '<th>Gegenbuchung</th><th>Rechnung</th><th>Betrag</th></tr></thead><tbody>{0}</tbody></table>').format(''.join(rows))

def camt_gebuchte_zahlung_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'verbuchte_zahlung_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'verbuchte_zahlung_qty', qty)

def camt_mitgliedschaften_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'mitgliedschaften_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'mitgliedschaften_qty', qty)

def camt_hv_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'hv_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'hv_qty', qty)

def camt_spenden_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'spenden_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'spenden_qty', qty)

def camt_produkte_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'produkte_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'produkte_qty', qty)

def camt_ueberzahlung_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'ueberzahlung_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'ueberzahlung_qty', qty)

def camt_zugewiesen_nicht_verbucht_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'zugewiesen_unverbucht_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'zugewiesen_unverbucht_qty', qty)

def camt_rueckzahlung_update(camt_import):
    qty = frappe.db.get_value('CAMT Import', camt_import, 'rueckzahlung_qty') + 1
    frappe.db.set_value('CAMT Import', camt_import, 'rueckzahlung_qty', qty)

@frappe.whitelist()
def aktualisiere_camt_uebersicht(camt_import):
    # Reset Gesamtsumme
    reset_camt_amount_from_camt_file(camt_import)
    verrechnete_zahlungen = frappe.get_all(
        'Payment Entry',
        filters={
            'camt_import': camt_import,
            'docstatus': 1,
            'camt_verrechnung_journal': ['is', 'set']
        },
        fields=['name', 'paid_to', 'paid_amount', 'camt_verrechnung_journal', 'camt_verrechnung_rechnung']
    )

    # verbuchte Zahlungen
    verbuchte_zahlungen = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 1""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'verbuchte_zahlung_qty', verbuchte_zahlungen)
    
    # nicht zugewiesene Zahlungen
    nicht_zugewiesene_zahlungen = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 0
                                            AND `camt_status` = 'Nicht zugewiesen'""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'anz_unmatched_payments', nicht_zugewiesene_zahlungen)
    
    # zugewiesene aber unverbuchte Zahlungen
    zugewiesen_unverbucht_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 0
                                            AND `mv_mitgliedschaft` IS NOT NULL""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'zugewiesen_unverbucht_qty', zugewiesen_unverbucht_qty)
    
    # Verbuchte Zahlungen welche ein Guthaben auslösen
    guthaben_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 1
                                            AND `unallocated_amount` > 0""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'guthaben_qty', guthaben_qty)
    
    # Stornierte Zahlungen
    storno_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `docstatus` = 2""".format(camt_import=camt_import), as_dict=True)[0].qty
    frappe.db.set_value('CAMT Import', camt_import, 'stornierte_zahlungen_qty', storno_qty)
    
    # HV, Mitgliedschaften, Produkte und Spenden
    gebuchte_pes = frappe.db.sql("""SELECT `name`
                                    FROM `tabPayment Entry`
                                    WHERE `camt_import` = '{camt_import}'
                                    AND `docstatus` = 1""".format(camt_import=camt_import), as_dict=True)
    # reset old values
    frappe.db.set_value('CAMT Import', camt_import, 'mitgliedschaften_qty', 0)
    frappe.db.set_value('CAMT Import', camt_import, 'hv_qty', 0)
    frappe.db.set_value('CAMT Import', camt_import, 'spenden_qty', 0)
    frappe.db.set_value('CAMT Import', camt_import, 'produkte_qty', 0)
    frappe.db.set_value('CAMT Import', camt_import, 'rueckzahlung_qty', 0)

    summe_rueckzahlungen = 0
    
    # set new values
    for pe in gebuchte_pes:
        pe_doc = frappe.get_doc("Payment Entry", pe.name)
        if len(pe_doc.references) > 0:
            for reference in pe_doc.references:
                if int(frappe.db.get_value('Sales Invoice', reference.reference_name, 'ist_mitgliedschaftsrechnung')) == 1:
                    camt_mitgliedschaften_update(camt_import)
                elif int(frappe.db.get_value('Sales Invoice', reference.reference_name, 'ist_hv_rechnung')) == 1:
                    camt_hv_update(camt_import)
                elif int(frappe.db.get_value('Sales Invoice', reference.reference_name, 'ist_spenden_rechnung')) == 1:
                    camt_spenden_update(camt_import)
                elif int(frappe.db.get_value('Sales Invoice', reference.reference_name, 'ist_sonstige_rechnung')) == 1:
                    camt_produkte_update(camt_import)
        elif not pe_doc.get('camt_verrechnung_journal'):
            # Verbuchte Rückzahlungen
            if pe_doc.unallocated_amount == 0:
                camt_rueckzahlung_update(camt_import)
                summe_rueckzahlungen += pe_doc.paid_amount
    
    # update report data
    verbuchte_zahlungen_gegen_rechnung = frappe.db.sql("""SELECT
                                                            SUM(`amount`) AS `amount`,
                                                            `item_code`,
                                                            `income_account`
                                                        FROM `tabSales Invoice Item` WHERE `parent` IN (
                                                            SELECT DISTINCT
                                                                `reference_name`
                                                            FROM `tabPayment Entry Reference`
                                                            WHERE `parent` IN (
                                                                SELECT
                                                                    `name`
                                                                FROM `tabPayment Entry`
                                                                WHERE `camt_import` = '{camt_import}'
                                                                AND `docstatus` = 1
                                                            )
                                                            AND `total_amount` = `allocated_amount`
                                                        )
                                                        GROUP BY `item_code`""".format(camt_import=camt_import), as_dict=True)
    
    verbuchte_teilzahlungen_gegen_rechnung = frappe.db.sql("""SELECT
                                                                `reference_name`,
                                                                SUM(`allocated_amount`) AS `teilzahlungsbetrag`
                                                            FROM `tabPayment Entry Reference`
                                                            WHERE `parent` IN (
                                                                SELECT
                                                                    `name`
                                                                FROM `tabPayment Entry`
                                                                WHERE `camt_import` = '{camt_import}'
                                                                AND `docstatus` = 1
                                                            )
                                                            AND `total_amount` != `allocated_amount`
                                                            GROUP BY `reference_name`
                                                        """.format(camt_import=camt_import), as_dict=True)
    
    # Der Rechnungsbezug der Firmenverrechnung liegt auf dem Journal Entry der Zielfirma.
    for pe in verrechnete_zahlungen:
        verbuchte_teilzahlungen_gegen_rechnung.append(frappe._dict(reference_name=pe.camt_verrechnung_rechnung, teilzahlungsbetrag=pe.paid_amount))
        invoice = frappe.get_doc('Sales Invoice', pe.camt_verrechnung_rechnung)
        if invoice.ist_mitgliedschaftsrechnung:
            camt_mitgliedschaften_update(camt_import)
        elif invoice.ist_hv_rechnung:
            camt_hv_update(camt_import)
        elif invoice.ist_spenden_rechnung:
            camt_spenden_update(camt_import)
        elif invoice.ist_sonstige_rechnung:
            camt_produkte_update(camt_import)
    
    verbuchte_guthaben = frappe.db.sql("""SELECT
                                                SUM(`unallocated_amount`) AS `amount`,
                                                `mv_mitgliedschaft` AS `mitgliedschaft`
                                            FROM `tabPayment Entry`
                                            WHERE `camt_import` = '{camt_import}'
                                            AND `mv_mitgliedschaft` IS NOT NULL
                                            AND `docstatus` = 1
                                            AND `unallocated_amount` > 0
                                            GROUP BY `mv_mitgliedschaft`""".format(camt_import=camt_import), as_dict=True)
    
    falsch_verbuchte_guthaben = frappe.db.sql("""SELECT
                                                        `unallocated_amount` AS `amount`,
                                                        `name`
                                                    FROM `tabPayment Entry`
                                                    WHERE `camt_import` = '{camt_import}'
                                                    AND (
                                                        `mv_mitgliedschaft` IS NULL
                                                        AND
                                                        `mv_kunde` IS NULL
                                                    )
                                                    AND `docstatus` = 1""".format(camt_import=camt_import), as_dict=True)
    
    nicht_gebuchte_pes = frappe.db.sql("""SELECT `name`
                                    FROM `tabPayment Entry`
                                    WHERE `camt_import` = '{camt_import}'
                                    AND `docstatus` != 1""".format(camt_import=camt_import), as_dict=True)
    
    verrechnete_namen = set(pe.name for pe in verrechnete_zahlungen)
    falsch_verbuchte_guthaben = [pe for pe in falsch_verbuchte_guthaben if pe.name not in verrechnete_namen]
    report_data = get_matching_abweichungen_report(camt_import) + get_verrechnungen_report(verrechnete_zahlungen)
    # nicht eingelesene Zahlungen
    einlesefehler = get_offene_einlesefehler(camt_import)
    if einlesefehler:
        report_data += """<p style="color: red;"><br>Achtung; {0} Zahlung(en) konnte(n) <u>nicht</u> eingelesen werden!</p>""".format(einlesefehler)
    
    
    # Artikel und Ertragskonten Aufschlüsselung
    ertragskonten = {}
    artikel_betraege = {}

    # Teilzahlungen
    if len(verbuchte_teilzahlungen_gegen_rechnung) > 0:
        for teilzahlung in verbuchte_teilzahlungen_gegen_rechnung:
            teilzahlungsbetrag = teilzahlung.teilzahlungsbetrag
            teilzahlungs_invoice = frappe.get_doc("Sales Invoice", teilzahlung.reference_name)
            teilzahlungs_ertragskonten = {}
            teilzahlungs_artikel_betraege = {}
            maximal_werte = []

            for item in teilzahlungs_invoice.items:
                maximal_werte.append(item.amount)
            
            list_teilzahlungs_verteilung = teilzahlungs_verteilung(teilzahlungsbetrag, maximal_werte)
            loop_index = 0

            for item in teilzahlungs_invoice.items:
                if item.item_code in teilzahlungs_artikel_betraege:
                    teilzahlungs_artikel_betraege[item.item_code] += list_teilzahlungs_verteilung[loop_index]
                else:
                    teilzahlungs_artikel_betraege[item.item_code] = list_teilzahlungs_verteilung[loop_index]
                
                if item.income_account in teilzahlungs_ertragskonten:
                    teilzahlungs_ertragskonten[item.income_account] += list_teilzahlungs_verteilung[loop_index]
                else:
                    teilzahlungs_ertragskonten[item.income_account] = list_teilzahlungs_verteilung[loop_index]
                loop_index += 1
            
            for teilzahlungs_artikel_betrag in teilzahlungs_artikel_betraege:
                if teilzahlungs_artikel_betrag in artikel_betraege:
                    artikel_betraege[teilzahlungs_artikel_betrag] += teilzahlungs_artikel_betraege[teilzahlungs_artikel_betrag]
                else:
                    artikel_betraege[teilzahlungs_artikel_betrag] = teilzahlungs_artikel_betraege[teilzahlungs_artikel_betrag]
            
            for teilzahlungs_ertragskonto in teilzahlungs_ertragskonten:
                if teilzahlungs_ertragskonto in ertragskonten:
                    ertragskonten[teilzahlungs_ertragskonto] += teilzahlungs_ertragskonten[teilzahlungs_ertragskonto]
                else:
                    ertragskonten[teilzahlungs_ertragskonto] = teilzahlungs_ertragskonten[teilzahlungs_ertragskonto]

    # "Voll"-Zahlungen
    if len(verbuchte_zahlungen_gegen_rechnung) > 0:
        for entry in verbuchte_zahlungen_gegen_rechnung:
            if entry.income_account in ertragskonten:
                ertragskonten[entry.income_account] += entry.amount
            else:
                ertragskonten[entry.income_account] = entry.amount
            
            if entry.item_code in artikel_betraege:
                artikel_betraege[entry.item_code] += entry.amount
            else:
                artikel_betraege[entry.item_code] = entry.amount
        
    # Artikel Aufschlüsselung
    artikel_totalbetrag = 0
    report_data += """<h3>Aufschlüsselung nach Artikel</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Artikel</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                </tr>"""

    for artikel_betrag in artikel_betraege:
        report_data += """
                        <tr>
                            <td style="text-align: left;">{0} ({1})</td>
                            <td style="text-align: right;">{2}</td>
                        </tr>""".format(frappe.get_value("Item", artikel_betrag, "item_name"), frappe.get_value("Item", artikel_betrag, "sektion_id"), "{:,.2f}".format(artikel_betraege[artikel_betrag]).replace(",", "'"))
        artikel_totalbetrag += artikel_betraege[artikel_betrag]
    report_data += """
                    <tr>
                        <td style="text-align: left;"><b>Total</b></td>
                        <td style="text-align: right;"><b>{0}</b></td>
                    </tr>""".format("{:,.2f}".format(artikel_totalbetrag).replace(",", "'"))
    
    report_data += """</tbody></table>"""
    
    # Ertragskonten Aufschlüsselung
    ertragskonten_totalbetrag = 0
    report_data += """<h3>Aufschlüsselung nach Ertragskonten</h3>
                    <table style="width: 100%;">
                        <tbody>
                            <tr>
                                <td style="text-align: left;"><b>Ertragskonto</b></td>
                                <td style="text-align: right;"><b>Betrag</b></td>
                            </tr>"""
    for key, value in ertragskonten.items():
        report_data += """
                        <tr>
                            <td style="text-align: left;">{0}</td>
                            <td style="text-align: right;">{1}</td>
                        </tr>""".format(key, "{:,.2f}".format(value).replace(",", "'"))
        ertragskonten_totalbetrag += value
    report_data += """
                    <tr>
                        <td style="text-align: left;"><b>Total</b></td>
                        <td style="text-align: right;"><b>{0}</b></td>
                    </tr>""".format("{:,.2f}".format(ertragskonten_totalbetrag).replace(",", "'"))
    
    report_data += """</tbody></table>"""

    # Besonderes (Rückzahlungen)
    if summe_rueckzahlungen > 0:
        report_data += """<h3>Besonderes</h3>
                            <table style="width: 100%;">
                                <tbody>
                                    <tr>
                                        <td style="text-align: left;">Rückzahlungen</td>
                                        <td style="text-align: right;">{summe_rueckzahlungen}</td>
                                    </tr>
                                </tbody>
                            </table>""".format(summe_rueckzahlungen="{:,.2f}".format(summe_rueckzahlungen).replace(",", "'"))
    
    # Verbuchte Guthaben
    if len(verbuchte_guthaben) > 0:
        report_data += """<h3>Verbuchte Guthaben</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Mitglied</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                </tr>"""
        for entry in verbuchte_guthaben:
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0}</td>
                                <td style="text-align: right;">{1}</td>
                            </tr>""".format("""<a href="/desk#Form/Mitgliedschaft/{0}">""".format(entry.mitgliedschaft) + str(frappe.get_value("Mitgliedschaft", entry.mitgliedschaft, "mitglied_nr")) + """</a>""", \
                            "{:,.2f}".format(entry.amount).replace(",", "'"))
        report_data += """</tbody></table>"""
    
    # Falsch verbuchte Guthaben
    if len(falsch_verbuchte_guthaben) > 0:
        report_data += """<h3>Falsch verbuchte Guthaben</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Zahlung</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                </tr>"""
        for entry in falsch_verbuchte_guthaben:
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0}</td>
                                <td style="text-align: right;">{1}</td>
                            </tr>""".format("""<a href="/desk#Form/Payment Entry/{pe}">{pe}</a>""".format(pe=entry.name), "{:,.2f}".format(entry.amount).replace(",", "'"))
        report_data += """</tbody></table>"""
    
    # Zahlungsliste (Unverbucht)
    if len(nicht_gebuchte_pes) > 0:
        report_data += """<h3>Zahlungsliste (Unverbucht)</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Mitgliedschaft</b></td>
                                    <td style="text-align: left;"><b>Details</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                    <td style="text-align: right;"><b>Status</b></td>
                                </tr>"""
        for pe in nicht_gebuchte_pes:
            pe_doc = frappe.get_doc("Payment Entry", pe.name)
            if pe_doc.mv_mitgliedschaft:
                mitgliedschafts_link_string = """<a href="/desk#Form/Mitgliedschaft/{0}">""".format(pe_doc.mv_mitgliedschaft) + str(frappe.get_value("Mitgliedschaft", pe_doc.mv_mitgliedschaft, "mitglied_nr")) + """</a>"""
            else:
                mitgliedschafts_link_string = '---'
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0}</td>
                                <td style="text-align: left;">{1}</td>
                                <td style="text-align: right;">{2}</td>
                                <td style="text-align: right;">{3}</td>
                            </tr>""".format(mitgliedschafts_link_string, \
                            pe_doc.remarks, \
                            "{:,.2f}".format(pe_doc.paid_amount).replace(",", "'"), \
                            'Entwurf' if pe_doc.docstatus == 0 else 'Storniert')
        report_data += """</tbody></table>"""
    
    # Zahlungsliste (Verbucht)
    if len(gebuchte_pes) > 0:
        report_data += """<h3>Zahlungsliste (Verbucht)</h3>
                        <table style="width: 100%;">
                            <tbody>
                                <tr>
                                    <td style="text-align: left;"><b>Mitgliedschaft</b></td>
                                    <td style="text-align: left;"><b>Details</b></td>
                                    <td style="text-align: right;"><b>Betrag</b></td>
                                </tr>"""
        for pe in gebuchte_pes:
            pe_doc = frappe.get_doc("Payment Entry", pe.name)
            if pe_doc.mv_mitgliedschaft:
                hyperlink = """<a href="/desk#Form/Mitgliedschaft/{0}">""".format(pe_doc.mv_mitgliedschaft) + str(frappe.get_value("Mitgliedschaft", pe_doc.mv_mitgliedschaft, "mitglied_nr")) + """</a>"""
            elif pe_doc.mv_kunde:
                hyperlink = """<a href="/desk#Form/Kunden/{0}">""".format(pe_doc.mv_kunde) + str(pe_doc.mv_kunde) + """</a>"""
            else:
                hyperlink = """---"""
            
            report_data += """
                            <tr>
                                <td style="text-align: left;">{0}</td>
                                <td style="text-align: left;">{1}</td>
                                <td style="text-align: right;">{2}</td>
                            </tr>""".format(hyperlink, \
                            pe_doc.remarks, \
                            "{:,.2f}".format(pe_doc.paid_amount).replace(",", "'"))
        report_data += """</tbody></table>"""
    
    
    frappe.db.set_value('CAMT Import', camt_import, 'report', report_data)
    
    alter_status = frappe.db.get_value('CAMT Import', camt_import, 'status')
    if alter_status in ('Verarbeitet', 'Closed', 'Aktualisierung notwendig'):
        draft_pe_qty = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabPayment Entry` WHERE `docstatus` = 0 AND `camt_import` = '{camt_import}'""".format(camt_import=camt_import), as_dict=True)[0].qty
        frappe.db.set_value('CAMT Import', camt_import, 'status', 'Verarbeitet' if draft_pe_qty > 0 or einlesefehler else 'Closed')

# Hilfsmethoden für die faire Verteilung von Teilzahlungen auf die Artikel und entsprechenden Ertragskonten
def teilzahlungs_verteilung(betrag, maximalwerte):
    n = len(maximalwerte)
    roh_anteil = betrag / n

    # Initialverteilung (minimal von Anteil und Maximalwert)
    anteile = [min(roh_anteil, m) for m in maximalwerte]
    skaliert_summe = sum(anteile)

    # Wenn Gesamtbetrag nicht erreicht, skaliere proportional runter
    if skaliert_summe != betrag:
        faktor = betrag / skaliert_summe
        anteile = [min(round(a * faktor, 10), m) for a, m in zip(anteile, maximalwerte)]

    # Runde auf 0.01
    gerundet = [round(a, 2) for a in anteile]
    diff = round(betrag - sum(gerundet), 2)

    # Korrektur in 0.01-Schritten
    step = 0.01 if diff > 0 else -0.01
    steps = int(round(abs(diff) / 0.01))

    # Fair verteilen der Korrektur
    indices = sorted(range(n), key=lambda i: (gerundet[i], -maximalwerte[i]), reverse=(step < 0))

    for i in range(steps):
        idx = indices[i % n]
        neuer_wert = round(gerundet[idx] + step, 2)
        if 0 <= neuer_wert <= maximalwerte[idx]:
            gerundet[idx] = neuer_wert
        else:
            # Suche nächstbeste Position
            for j in indices:
                kandidat = round(gerundet[j] + step, 2)
                if 0 <= kandidat <= maximalwerte[j]:
                    gerundet[j] = kandidat
                    break

    return gerundet

def reset_camt_amount_from_camt_file(camt_import):
    """
    Diese Funktion list das CAMT-File aus und setzt den CAMT Amount neu
    Manuelle ausgeführung: bench execute mvd.mvd.doctype.camt_import.helpers.reset_camt_amount_from_camt_file --kwargs "{'camt_import': 'CAMT-25-02-05-04'}"
    """
    camt_file = get_camt_file(frappe.db.get_value('CAMT Import', camt_import, 'camt_file'))

    if camt_file:
        # Reset CAMT Base Data
        frappe.db.set_value('CAMT Import', camt_import, 'camt_amount', 0)
        camt_amount = 0
        transaction_entries = camt_file.find_all('ntry')
        for entry in transaction_entries:
            entry_soup = BeautifulSoup(six.text_type(entry), 'lxml')
            transactions = entry_soup.find_all('txdtls')
            for transaction in transactions:
                transaction_soup = BeautifulSoup(six.text_type(transaction), 'lxml')
                try:
                    amount = float(transaction_soup.amt.get_text())
                    try:
                        camt_amount += amount
                    except:
                        pass
                except:
                    pass
        
        frappe.db.set_value('CAMT Import', camt_import, 'camt_amount', camt_amount)

def get_mahnungen(sinv=None, mitgliedschaft=None, mv_kunde=None):
    offene_mahnungen = frappe.db.sql(
        """
            SELECT
                `name` AS `mahnung`,
                `reminder_charge`
            FROM `tabMahnung`
            WHERE `docstatus` = 1
            AND IFNULL(`reminder_charge`, 0) > 0
            AND (
                `mv_mitgliedschaft` = '{mitgliedschaft}'
                OR
                `mv_kunde` = '{mv_kunde}'
            )
            AND `name` IN (
                SELECT `parent` FROM `tabMahnung Invoices`
                WHERE `sales_invoice` = '{sinv}'
            )
            ORDER BY `highest_level` DESC
        """.format(mitgliedschaft=mitgliedschaft, mv_kunde=mv_kunde, sinv=sinv),
        as_dict=True
    )
    if len(offene_mahnungen) > 0:
        return {
            'mahnung': offene_mahnungen[0].mahnung,
            'reminder_charge': offene_mahnungen[0].reminder_charge
        }

    return False

def create_sinv_from_sinv(sinv=None, mahngebuehr=0, ignore_permissions=True):
    if not sinv:
        return False
    
    origin_sinv = frappe.get_doc("Sales Invoice", sinv)
    sinv_copy = frappe.copy_doc(origin_sinv)
    sinv_copy.rechnungs_bankkonto = get_matching_bankkonto(origin_sinv)
    sinv_copy.due_date = today()
    sinv_copy.payment_schedule = []
    sinv_copy.ist_mitgliedschaftsrechnung = 0
    sinv_copy.ist_hv_rechnung = 0
    sinv_copy.ist_spenden_rechnung = 0
    sinv_copy.ist_sonstige_rechnung = 1
    sinv_copy.ohne_betrag = 0
    
    first_item_line = sinv_copy.items[0]
    first_item_line.item_name = "Mahngebühr"
    first_item_line.rate = mahngebuehr
    first_item_line.amount = mahngebuehr
    sinv_copy.items = [first_item_line]

    if not ignore_permissions:
        sinv_copy.check_permission('create')
        sinv_copy.check_permission('submit')
    
    sinv_copy.insert(ignore_permissions=ignore_permissions)
    sinv_copy.docstatus = 1
    sinv_copy.save(ignore_permissions=ignore_permissions)

    return sinv_copy.name
