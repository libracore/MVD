# -*- coding: utf-8 -*-
# Copyright (c) 2022-2026, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import hashlib
import json
import frappe
from frappe.utils import flt
from frappe.utils.background_jobs import enqueue
from mvd.mvd.doctype.camt_import.helpers import get_matching_bankkonto, get_matching_abweichung, get_default_customer
from mvd.mvd.doctype.camt_import.reset_protokoll import mit_protokoll, generation, ist_aktuell, erfassen, markiere_beleg

def _zugriff(camt_import, schreiben=False):
    if not set(frappe.get_roles()).intersection(['System Manager', 'MV_RW', 'MV_GL']):
        frappe.throw('Sie haben keine Berechtigung für Firmenverrechnungen.', frappe.PermissionError)
    
    if schreiben and frappe.local.request.method != 'POST':
        frappe.throw('Diese Aktion muss als POST-Anfrage ausgeführt werden.', frappe.PermissionError)
    
    if schreiben:
        frappe.db.sql('SELECT name FROM `tabCAMT Import` WHERE name=%s FOR UPDATE', (camt_import,))
    
    doc = frappe.get_doc('CAMT Import', camt_import)
    doc.check_permission('write')

    if doc.status == 'In Verarbeitung':
        frappe.throw('Bitte warten Sie, bis die CAMT-Verarbeitung abgeschlossen ist.')
    
    return doc

def _eintraege(camt):
    source = camt.get('matching_abweichungen') or '[]'
    cached = camt.get('_camt_abweichungen_cache')
    if cached is None or cached[0] != source:
        entries = json.loads(source)
        by_payment = {}
        for entry in entries:
            by_payment.setdefault(entry['payment_entry'], []).append(entry)
        cached = (source, entries, by_payment)
        camt._camt_abweichungen_cache = cached
    
    return cached[1]

def _eintrag(camt, payment_entry):
    _eintraege(camt)

    return camt.get('_camt_abweichungen_cache')[2].get(payment_entry, [])

def _offene_eintraege(camt, firmenwechsel):
    entries = _eintraege(camt)
    if not entries:
        return []
    
    names = list(set(entry['payment_entry'] for entry in entries))
    payments = frappe.get_all(
        'Payment Entry',
        filters={
            'name': ['in', names]
        },
        fields=['name', 'camt_import', 'docstatus'],
        order_by='name',
        ignore_ifnull=True
    )
    open_names = set(row.name for row in payments if row.camt_import == camt.name and row.docstatus == 0)
    entries = [entry for entry in entries if entry['payment_entry'] in open_names]
    targets = set()

    for doctype in ('Sales Invoice', 'Fakultative Rechnung'):
        names = list(set(entry['reference_name'] for entry in entries if entry['reference_doctype'] == doctype))
        if not names:
            continue

        invoices = frappe.get_all(doctype, filters={'name': ['in', names]}, fields=['name', 'company', 'sektion_id'], order_by='name', ignore_ifnull=True)
        for invoice in invoices:
            if (firmenwechsel and invoice.company != camt.company) or (not firmenwechsel and invoice.company == camt.company and invoice.sektion_id == camt.sektion_id):
                targets.add((doctype, invoice.name))
    
    return [entry for entry in entries if (entry['reference_doctype'], entry['reference_name']) in targets]

def _konto(name, company, currency, root_type=None, account_type=None):
    if not name:
        frappe.throw('Bitte wählen Sie beide Verrechnungskonten aus.')
    
    account = frappe.get_cached_doc('Account', name)
    account.check_permission('read')
    if account.company != company or account.is_group or account.disabled or account.docstatus == 2:
        frappe.throw('Das Konto {0} muss ein aktives Einzelkonto der Firma {1} sein.'.format(name, company))
    
    if (account.account_currency or currency) != currency:
        frappe.throw('Für diesen Verrechnungsablauf müssen alle Konten dieselbe Währung haben.')
    
    if root_type and (account.root_type != root_type or account.account_type in ['Bank', 'Cash', 'Receivable', 'Payable']):
        frappe.throw('Das Verrechnungskonto {0} muss ein {1}-Bilanzkonto ohne Bank-, Kassen-, Debitoren- oder Kreditorentyp sein.'.format(name, 'Passiv' if root_type == 'Liability' else 'Aktiv'))
    
    if account_type and account.account_type != account_type:
        frappe.throw('Das Konto {0} muss den Kontotyp {1} haben.'.format(name, account_type))
    
    return account

def _kontext(camt, payment_entry, sperren=False):
    entries = _eintrag(camt, payment_entry)
    if len(entries) != 1:
        frappe.throw('Diese Zahlung ist nicht eindeutig als blockierter Rechnungstreffer im CAMT-Import erfasst.')
    
    entry = entries[0]
    doctype = entry['reference_doctype']
    if doctype not in ['Sales Invoice', 'Fakultative Rechnung']:
        frappe.throw('Die hinterlegte Rechnungsart wird nicht unterstützt.')
    
    if sperren:
        frappe.db.sql('SELECT name FROM `tabPayment Entry` WHERE name=%s FOR UPDATE', (payment_entry,))
        frappe.db.sql('SELECT name FROM `tab{0}` WHERE name=%s FOR UPDATE'.format(doctype), (entry['reference_name'],))
    
    pe = frappe.get_doc('Payment Entry', payment_entry)
    pe.check_permission('write')
    target = frappe.get_doc(doctype, entry['reference_name'])
    target.check_permission('read')

    if pe.camt_import != camt.name or pe.docstatus != 0 or pe.payment_type != 'Receive':
        frappe.throw('Es kann nur eine ungebuchte Eingangszahlung dieses CAMT-Imports verrechnet werden.')
    
    if pe.references or pe.deductions or pe.get('camt_verrechnung_journal'):
        frappe.throw('Die Zahlung wurde bereits bearbeitet. Bitte prüfen Sie ihre Referenzen und Abzüge.')
    
    if pe.company != camt.company or pe.sektion_id != camt.sektion_id or pe.paid_to != camt.account:
        frappe.throw('Firma, Sektion und Eingangskonto der Zahlung müssen weiterhin dem CAMT-Import entsprechen.')
    
    if target.docstatus != 1 or (doctype == 'Fakultative Rechnung' and target.status != 'Unpaid'):
        frappe.throw('Die Zielrechnung muss gebucht und noch offen sein.')
    
    if target.company == camt.company:
        frappe.throw('Diese Aktion ist für Zahlungen zwischen unterschiedlichen Firmen vorgesehen.')
    
    source_company = frappe.get_cached_doc('Company', camt.company)
    target_company = frappe.get_cached_doc('Company', target.company)
    source_company.check_permission('read')
    target_company.check_permission('read')
    currency = source_company.default_currency

    if target_company.default_currency != currency or (target.get('currency') or currency) != currency:
        frappe.throw('Diese erste Version unterstützt Firmenverrechnungen nur innerhalb derselben Währung.')
    
    amount = flt(pe.received_amount, 2)
    if amount <= 0 or amount != flt(pe.paid_amount, 2) or amount != flt(pe.camt_amount, 2):
        frappe.throw('Es muss der unveränderte positive CAMT-Zahlungsbetrag verrechnet werden.')
    
    if flt(pe.source_exchange_rate) != 1 or flt(pe.target_exchange_rate) != 1:
        frappe.throw('Zahlungen mit Währungsumrechnung werden in diesem Ablauf nicht unterstützt.')
    
    _konto(pe.paid_to, pe.company, currency, account_type='Bank')
    _konto(pe.paid_from, pe.company, currency, account_type='Receivable')

    if doctype == 'Sales Invoice':
        outstanding = flt(target.outstanding_amount, 2)
        customer = target.customer
        receivable = target.debit_to
    else:
        member = frappe.get_doc('Mitgliedschaft', target.mv_mitgliedschaft)
        section = frappe.get_doc('Sektion', target.sektion_id)
        member_section = frappe.get_doc('Sektion', member.sektion_id)
        if section.company != target.company or member_section.company != target.company:
            frappe.throw('Die Firmen der fakultativen Rechnung und ihrer Sektionen stimmen nicht überein.')
        
        outstanding = flt(target.betrag, 2) if target.typ == 'HV' else amount
        customer = member.rg_kunde or member.kunde_mitglied
        receivable = target_company.default_receivable_account
    
    if amount > outstanding or outstanding <= 0:
        frappe.throw('Der Zahlungsbetrag übersteigt den offenen Rechnungsbetrag. Bitte behandeln Sie die Überzahlung separat.')
    
    _konto(receivable, target.company, currency, account_type='Receivable')

    return pe, target, {
        'payment_entry': pe.name,
        'camt_import': camt.name,
        'reference_doctype': doctype,
        'reference_name': target.name,
        'source_company': pe.company,
        'target_company': target.company,
        'source_section': pe.sektion_id,
        'target_section': target.sektion_id,
        'bank_account': pe.paid_to,
        'customer': customer,
        'receivable': receivable,
        'amount': amount,
        'currency': currency,
        'posting_date': str(pe.posting_date),
        'outstanding_amount': outstanding,
        'payment_modified': str(pe.modified),
        'invoice_modified': str(target.modified),
        'source_cost_center': source_company.cost_center,
        'target_cost_center': target_company.cost_center
    }

def _plan(camt, payment_entry, verbindlichkeit, forderung, sperren=False):
    pe, target, plan = _kontext(camt, payment_entry, sperren=sperren)
    _konto(verbindlichkeit, plan['source_company'], plan['currency'], root_type='Liability')
    _konto(forderung, plan['target_company'], plan['currency'], root_type='Asset')
    plan.update(verbindlichkeit=verbindlichkeit, forderung=forderung)
    plan['buchungen'] = [
        {'firma': plan['source_company'], 'soll': plan['bank_account'], 'haben': verbindlichkeit, 'betrag': plan['amount']},
        {'firma': plan['target_company'], 'soll': forderung, 'haben': plan['receivable'], 'betrag': plan['amount']}
    ]
    plan['token'] = hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=True).encode('utf-8')).hexdigest()

    return pe, target, plan

@frappe.whitelist()
def kandidaten(camt_import):
    camt = _zugriff(camt_import)

    return _kandidaten(camt)

def _standard_verrechnungskonto(sektion, field, company, currency, root_type):
    if not sektion:
        return None
    
    name = frappe.get_cached_value('Sektion', sektion, field)
    if not name:
        return None
    
    try:
        _konto(name, company, currency, root_type=root_type)
    except (frappe.ValidationError, frappe.PermissionError):
        frappe.clear_messages()

        return None
    
    return name

def _kandidaten(camt, nur_erster=False):
    result = []
    ausgelassen = []
    entries = _offene_eintraege(camt, firmenwechsel=True) if nur_erster else _eintraege(camt)
    for row in entries:
        try:
            pe, target, info = _kontext(camt, row['payment_entry'])
            pe.check_permission('submit')
            journal = frappe.get_doc({'doctype': 'Journal Entry', 'company': target.company})
            journal.check_permission('create')
            journal.check_permission('submit')

            if target.doctype == 'Fakultative Rechnung':
                target.check_permission('write')
                invoice = frappe.get_doc({'doctype': 'Sales Invoice', 'company': target.company, 'sektion_id': target.sektion_id, 'customer': info['customer']})
                invoice.check_permission('create')
                invoice.check_permission('submit')
            
            if not nur_erster:
                info['default_verbindlichkeit'] = _standard_verrechnungskonto(info['source_section'], 'firmenverrechnung_verbindlichkeitskonto', info['source_company'], info['currency'], 'Liability')
                info['default_forderung'] = _standard_verrechnungskonto(info['target_section'], 'firmenverrechnung_forderungskonto', info['target_company'], info['currency'], 'Asset')
            
            result.append(info)

            if nur_erster:
                break

        except (frappe.ValidationError, frappe.PermissionError) as err:
            ausgelassen.append({'payment_entry': row['payment_entry'], 'grund': str(err)})
            frappe.clear_messages()

    return {
        'kandidaten': result,
        'ausgelassen': ausgelassen
    }

@frappe.whitelist()
def vorschau(camt_import, payment_entry, verbindlichkeit, forderung):
    camt = _zugriff(camt_import)

    return _plan(camt, payment_entry, verbindlichkeit, forderung)[2]

def _sammelplan(camt, zahlungen, sperren=False):
    if isinstance(zahlungen, str):
        try:
            zahlungen = json.loads(zahlungen)
        except ValueError:
            frappe.throw('Die Zahlungsauswahl konnte nicht gelesen werden.')
    
    if not isinstance(zahlungen, list) or not zahlungen:
        frappe.throw('Bitte wählen Sie mindestens eine Zahlung für die Sammelbuchung aus.')
    
    seen = set()
    plans = []
    allocated = {}
    for row in zahlungen:
        if not isinstance(row, dict) or not all(isinstance(row.get(field), str) and row[field] for field in ('payment_entry', 'verbindlichkeit', 'forderung')):
            frappe.throw('Bitte ergänzen Sie für jede Zahlung beide Verrechnungskonten.')
        
        if row['payment_entry'] in seen:
            frappe.throw('Eine Zahlung darf nur einmal in der Sammelbuchung enthalten sein.')
        
        seen.add(row['payment_entry'])
        pe, target, plan = _plan(camt, row['payment_entry'], row['verbindlichkeit'], row['forderung'], sperren=sperren)
        key = (plan['reference_doctype'], plan['reference_name'])
        before = flt(plan['outstanding_amount'] - allocated.get(key, 0), 2)

        if plan['amount'] > before:
            frappe.throw('Die Summe der ausgewählten Zahlungen übersteigt den offenen Betrag von {0}.'.format(plan['reference_name']))
        
        allocated[key] = flt(allocated.get(key, 0) + plan['amount'], 2)
        plan['outstanding_amount'] = before
        plan['outstanding_after'] = flt(before - plan['amount'], 2)
        plans.append(plan)

    result = {
        'plaene': plans,
        'anzahl': len(plans),
        'currency': plans[0]['currency'],
        'betrag': flt(sum(plan['amount'] for plan in plans), 2)
    }

    result['token'] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=True).encode('utf-8')).hexdigest()

    return result

@frappe.whitelist()
def vorschau_alle(camt_import, zahlungen):
    return _sammelplan(_zugriff(camt_import), zahlungen)

@frappe.whitelist()
@mit_protokoll
def buchen_alle(camt_import, zahlungen, token):
    camt = _zugriff(camt_import, schreiben=True)
    plan = _sammelplan(camt, zahlungen, sperren=True)
    if plan['token'] != token:
        frappe.throw('Die Daten haben sich seit der Sammelvorschau geändert. Bitte erstellen Sie eine neue Vorschau.')
    
    queued_before = list(frappe.flags.get('enqueue_after_commit') or [])
    realtime_before = list(getattr(frappe.local, 'realtime_log', None) or [])
    old_batch = frappe.flags.get('camt_verrechnung_sammellauf')
    frappe.flags.camt_verrechnung_sammellauf = True
    converted = {}
    results = []
    try:
        for item in plan['plaene']:
            reference = (item['reference_doctype'], item['reference_name'])
            current_camt = frappe.get_doc('CAMT Import', camt.name)
            if reference in converted:
                entries = _eintraege(current_camt)
                for entry in entries:
                    if entry['payment_entry'] == item['payment_entry']:
                        entry['reference_doctype'] = 'Sales Invoice'
                        entry['reference_name'] = converted[reference]
                value = json.dumps(entries, ensure_ascii=False)
                frappe.db.set_value('CAMT Import', camt.name, 'matching_abweichungen', value)
                current_camt.matching_abweichungen = value
            
            current = _plan(current_camt, item['payment_entry'], item['verbindlichkeit'], item['forderung'])[2]
            result = buchen(camt.name, item['payment_entry'], item['verbindlichkeit'], item['forderung'], current['token'])
            results.append(result)
            if item['reference_doctype'] == 'Fakultative Rechnung':
                converted[reference] = result['sales_invoice']
            
        _aktualisiere_report(camt.name)

        return {
            'buchungen': results,
            'anzahl': len(results)
        }
    
    except Exception:
        frappe.db.rollback()
        frappe.flags.enqueue_after_commit = queued_before
        frappe.local.realtime_log = realtime_before
        raise

    finally:
        frappe.flags.camt_verrechnung_sammellauf = old_batch

def _folgeprozesse(payment_entry, rechnung_beglichen=False, camt_import=None):
    camt = camt_import or frappe.db.get_value('Payment Entry', payment_entry, 'camt_import')
    enqueue('mvd.mvd.doctype.camt_import.verrechnung.aktualisiere_folgeprozesse', queue='short', enqueue_after_commit=True, payment_entry=payment_entry, rechnung_beglichen=rechnung_beglichen, reset_generation=generation(camt))

@frappe.whitelist()
@mit_protokoll
def buchen(camt_import, payment_entry, verbindlichkeit, forderung, token):
    camt = _zugriff(camt_import, schreiben=True)
    pe, target, plan = _plan(camt, payment_entry, verbindlichkeit, forderung, sperren=True)
    if plan['token'] != token:
        frappe.throw('Die Daten haben sich seit der Vorschau geändert. Bitte erstellen Sie eine neue Vorschau.')
    
    pe.check_permission('submit')
    old_skip = frappe.flags.get('skip_mitgliedschaft_zahlungsdaten')
    old_guard = frappe.flags.get('camt_verrechnung_in_arbeit')
    frappe.flags.skip_mitgliedschaft_zahlungsdaten = True
    frappe.flags.camt_verrechnung_in_arbeit = pe.name
    try:
        if target.doctype == 'Fakultative Rechnung':
            target.check_permission('write')
            permission_doc = frappe.get_doc({'doctype': 'Sales Invoice', 'company': target.company, 'sektion_id': target.sektion_id, 'customer': plan['customer']})
            permission_doc.check_permission('create')
            permission_doc.check_permission('submit')

            from mvd.mvd.doctype.camt_import.utils import create_unpaid_sinv
            data = create_unpaid_sinv(target.name, plan['amount'], camt_import=frappe._dict(company=target.company, sektion_id=target.sektion_id, account=get_matching_bankkonto(target)), commit=False)

            if not data or data.get('matching_abweichungen'):
                frappe.throw('Die fakultative Rechnung konnte nicht eindeutig umgewandelt werden.')

            target = frappe.get_doc('Sales Invoice', data['sinv'])

        journal = frappe.get_doc({
            'doctype': 'Journal Entry',
            'voucher_type': 'Journal Entry',
            'company': target.company,
            'posting_date': pe.posting_date,
            'camt_verrechnung_zahlung': pe.name,
            'user_remark': 'Firmenverrechnung von CAMT-Zahlung {0} ({1}) für Rechnung {2}. Kein Bankübertrag.'.format(pe.name, camt.name, target.name),
            'accounts': [
                {
                    'account': forderung,
                    'debit_in_account_currency': plan['amount'],
                    'exchange_rate': 1,
                    'cost_center': plan['target_cost_center']
                },
                {
                    'account': target.debit_to,
                    'party_type': 'Customer',
                    'party': target.customer,
                    'credit_in_account_currency': plan['amount'],
                    'exchange_rate': 1,
                    'reference_type': 'Sales Invoice',
                    'reference_name': target.name,
                    'cost_center': plan['target_cost_center']
                }
            ]
        })
        journal.check_permission('create')
        journal.check_permission('submit')
        journal.insert()

        pe.camt_verrechnung_journal = journal.name
        pe.camt_verrechnung_rechnung = target.name
        pe.party = target.customer
        pe.mv_mitgliedschaft = target.mv_mitgliedschaft
        pe.mv_kunde = target.mv_kunde

        deduction = pe.append('deductions', {})
        deduction.account = verbindlichkeit
        deduction.amount = -plan['amount']
        deduction.cost_center = plan['source_cost_center']

        pe.camt_status = 'Verbucht'
        pe.save()
        pe.submit()
        journal.submit()

        rechnung_beglichen = frappe.db.get_value('Sales Invoice', target.name, 'status') == 'Paid'

        entries = _eintraege(camt)
        for entry in entries:
            if entry['payment_entry'] == pe.name:
                entry['reference_doctype'] = 'Sales Invoice'
                entry['reference_name'] = target.name
        
        frappe.db.set_value('CAMT Import', camt.name, 'matching_abweichungen', json.dumps(entries, ensure_ascii=False))
        pe.add_comment('Comment', text='Firmenverrechnung: Gegenbuchung {0}, Rechnung {1}.'.format(journal.name, target.name))

        if not frappe.flags.get('camt_verrechnung_sammellauf'):
            _aktualisiere_report(camt.name)

        _folgeprozesse(pe.name, rechnung_beglichen=rechnung_beglichen, camt_import=camt.name)

        return {
            'payment_entry': pe.name,
            'journal_entry': journal.name,
            'sales_invoice': target.name
        }
    
    except Exception:
        frappe.db.rollback()
        raise

    finally:
        frappe.flags.skip_mitgliedschaft_zahlungsdaten = old_skip
        frappe.flags.camt_verrechnung_in_arbeit = old_guard

def pruefe_verrechnungsbeleg(doc, event=None):
    source = doc.get('camt_verrechnung_zahlung') or (doc.name if doc.get('camt_verrechnung_journal') else None)
    if source and frappe.flags.get('camt_verrechnung_in_arbeit') != source:
        frappe.throw('Diese Belege gehören zu einer Firmenverrechnung. Bitte buchen oder stornieren Sie sie gemeinsam über den CAMT-Import.')

@frappe.whitelist()
def gebuchte_verrechnungen(camt_import):
    camt = _zugriff(camt_import)

    return _gebuchte_verrechnungen(camt)

def _gebuchte_verrechnungen(camt, nur_erster=False):
    rows = frappe.get_all('Payment Entry', filters={'camt_import': camt.name, 'docstatus': 1, 'camt_verrechnung_journal': ['is', 'set']}, fields=['name', 'camt_verrechnung_journal', 'camt_verrechnung_rechnung'])
    result = []
    for row in rows:
        try:
            _storno_kontext(camt, row.name)
            result.append(row)
            if nur_erster:
                break
        except (frappe.ValidationError, frappe.PermissionError):
            frappe.clear_messages()

    return result

@frappe.whitelist()
def verfuegbare_aktionen(camt_import):
    result = {'verrechnen': False, 'stornieren': False}
    try:
        camt = _zugriff(camt_import)
    except (frappe.ValidationError, frappe.PermissionError):
        frappe.clear_messages()
        return result
    
    result['verrechnen'] = bool(_kandidaten(camt, nur_erster=True)['kandidaten'])
    result['stornieren'] = bool(_gebuchte_verrechnungen(camt, nur_erster=True))

    return result

def _storno_kontext(camt, payment_entry, sperren=False):
    if sperren:
        frappe.db.sql('SELECT name FROM `tabPayment Entry` WHERE name=%s FOR UPDATE', (payment_entry,))
    
    pe = frappe.get_doc('Payment Entry', payment_entry)
    pe.check_permission('cancel')
    if pe.camt_import != camt.name or pe.docstatus != 1 or not pe.get('camt_verrechnung_journal'):
        frappe.throw('Diese Zahlung ist keine gebuchte Firmenverrechnung dieses CAMT-Imports.')
    
    journal = frappe.get_doc('Journal Entry', pe.camt_verrechnung_journal)
    journal.check_permission('cancel')
    if journal.docstatus != 1 or journal.get('camt_verrechnung_zahlung') != pe.name:
        frappe.throw('Die verknüpften Belege passen nicht zusammen.')
    
    target = frappe.get_doc('Sales Invoice', pe.camt_verrechnung_rechnung)
    target.check_permission('read')
    if target.docstatus != 1:
        frappe.throw('Die verknüpfte Rechnung ist nicht mehr gebucht. Bitte prüfen Sie die Belege vor dem Storno.')
    
    replacement = frappe.copy_doc(pe)
    replacement.references = []
    replacement.deductions = []
    replacement.camt_verrechnung_journal = None
    replacement.camt_verrechnung_rechnung = None
    replacement.camt_status = 'Nicht zugewiesen'
    replacement.party = get_default_customer(pe.sektion_id)
    replacement.mv_mitgliedschaft = None
    replacement.mv_kunde = None
    replacement.amended_from = pe.name
    replacement.check_permission('create')

    return pe, journal, target, replacement

@frappe.whitelist()
@mit_protokoll
def stornieren(camt_import, payment_entry):
    camt = _zugriff(camt_import, schreiben=True)
    pe, journal, target, replacement = _storno_kontext(camt, payment_entry, sperren=True)
    old_skip = frappe.flags.get('skip_mitgliedschaft_zahlungsdaten')
    old_guard = frappe.flags.get('camt_verrechnung_in_arbeit')
    frappe.flags.skip_mitgliedschaft_zahlungsdaten = True
    frappe.flags.camt_verrechnung_in_arbeit = pe.name
    try:
        markiere_beleg('Sales Invoice', target.name)
        pe.db_set('camt_verrechnung_journal', None)

        journal.cancel()
        pe.cancel()

        pe.db_set('camt_verrechnung_journal', journal.name)

        replacement.insert()

        entry = get_matching_abweichung(target, camt)
        entry['payment_entry'] = replacement.name
        entries = [row for row in _eintraege(camt) if row['payment_entry'] != pe.name]
        entries.append(entry)

        frappe.db.set_value('CAMT Import', camt.name, 'matching_abweichungen', json.dumps(entries, ensure_ascii=False))

        pe.add_comment('Comment', text='Firmenverrechnung storniert. Neue ungebuchte Zahlung: {0}.'.format(replacement.name))

        _aktualisiere_report(camt.name)
        _folgeprozesse(pe.name, camt_import=camt.name)

        return {
            'payment_entry': replacement.name,
            'cancelled_payment_entry': pe.name,
            'journal_entry': journal.name,
            'sales_invoice': target.name
        }
    
    except Exception:
        frappe.db.rollback()
        raise

    finally:
        frappe.flags.skip_mitgliedschaft_zahlungsdaten = old_skip
        frappe.flags.camt_verrechnung_in_arbeit = old_guard

def _aktualisiere_report(camt_import):
    from mvd.mvd.doctype.camt_import.helpers import aktualisiere_camt_uebersicht
    aktualisiere_camt_uebersicht(camt_import)

def aktualisiere_folgeprozesse(payment_entry, rechnung_beglichen=False, reset_generation=None):
    if not frappe.db.exists('Payment Entry', payment_entry):
        return
    
    pe = frappe.get_doc('Payment Entry', payment_entry)
    if not ist_aktuell(pe.camt_import, reset_generation):
        return
    
    if not frappe.db.exists('Payment Entry', payment_entry):
        return
    
    pe = frappe.get_doc('Payment Entry', payment_entry)

    with erfassen(pe.camt_import):
        _aktualisiere_folgeprozesse(pe, rechnung_beglichen)

def _aktualisiere_folgeprozesse(pe, rechnung_beglichen):
    if pe.docstatus not in (1, 2) or not pe.get('camt_verrechnung_rechnung'):
        return
    
    if pe.docstatus == 1:
        journal = frappe.get_doc('Journal Entry', pe.camt_verrechnung_journal)
        if journal.docstatus != 1 or journal.get('camt_verrechnung_zahlung') != pe.name:
            frappe.throw('Die Firmenverrechnung ist nicht vollständig gebucht. Die Folgeprozesse wurden nicht ausgeführt.')
    
    invoice = frappe.get_doc('Sales Invoice', pe.camt_verrechnung_rechnung)
    if invoice.mv_mitgliedschaft:
        frappe.db.sql('SELECT name FROM `tabMitgliedschaft` WHERE name=%s FOR UPDATE', (invoice.mv_mitgliedschaft,))
        from mvd.mvd.doctype.mitgliedschaft.process_utils.update_zahlungsdaten import run
        run(invoice.mv_mitgliedschaft)
    
    if pe.docstatus == 1:
        from mvd.mvd.utils.hook_utils import pe_zahlungsfolgeprozesse
        pe_zahlungsfolgeprozesse(pe, zahlungsbestaetigung=rechnung_beglichen)
    
    _aktualisiere_report(pe.camt_import)
