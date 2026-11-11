# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import math
import os
import re
import frappe
from frappe.utils import cint, flt
from tqdm import tqdm
from mvd.mvd.utils import is_job_already_running
from mvd.mvd.utils.manuelle_rechnungs_items import get_mitgliedschafts_artikel_geschaeft

"""
Gezielte Korrektur des MVZH-Jahreslaufs MRJ-2027-3 (kein Migrationspatch).

Erwartet als erste Excel-Spalte:
Mitglied-Nr ohne MV; aktives Tabellenblatt (.xls: erstes Blatt), mit Kopfzeile.

Vorschau (keine Schreibzugriffe):
    bench --site libracore.mieterverband.ch execute mvd.mvd.data_import.mvzh_mrj_2027_reduktionen.run \
        --kwargs '{"file_path":"/absoluter/pfad/reduktionen.xlsx"}'

Korrektur nach Prüfung der Vorschau, gleicher Aufruf mit "dry_run": False
Ohne Kopfzeile zusätzlich "has_header": False

Pro Mitglied werden Beitrag, Preisregel und Rechnung gemeinsam gespeichert
oder bei Fehlern vollständig zurückgerollt. Bereits korrekte Rechnungen bleiben
unverändert. Gesperrte Fälle werden ohne Änderungen protokolliert.
Bestehende PDF-Anhänge müssten anschliessend über die PDF-Neuerstellung des
Jahreslaufs erneuert werden.
"""

MRJ = 'MRJ-2027-3'
SEKTION = 'MVZH'
JAHR = 2027
NEUE_REDUKTION = {
    'reduzierte_mitgliedschaft': 1,
    'grund_abweichender_betrag': 'Reduziert',
    'reduzierter_betrag': 50,
    'reduzierung_bis': '2099-12-31'
}


class Blockiert(ValueError):
    pass


def run(file_path, dry_run=True, has_header=True):
    dry_run = bool(cint(dry_run))
    rows = _read_members(file_path, bool(cint(has_header)))
    _check_run()
    sektion = frappe.get_doc('Sektion', SEKTION)
    numbers = [row['mitglied_nr'] for row in rows if row.get('mitglied_nr')]
    members = frappe.get_all('Mitgliedschaft',
        filters={'mitglied_nr': ['in', numbers], 'sektion_id': SEKTION},
        fields=['name', 'mitglied_nr']) if numbers else []
    by_number = {}
    for member in members:
        by_number.setdefault(member.mitglied_nr, []).append(member.name)

    result = {'jahreslauf': MRJ, 'sektion': SEKTION, 'dry_run': dry_run,
        'bereit': 0, 'korrigiert': 0, 'bereits_korrekt': 0,
        'blockiert': 0, 'fehler': 0, 'details': []}
    flag = 'skip_mitgliedschaft_zahlungsdaten'
    previous = frappe.flags.get(flag)
    if not dry_run:
        frappe.flags[flag] = True
    try:
        for row in tqdm(rows, total=len(rows), unit=' Mitglied',
                desc='{0}: {1}'.format(MRJ, 'Prüflauf' if dry_run else 'Korrektur')):
            entry = dict(row)
            try:
                if not dry_run:
                    # Eigenständiger Reparaturlauf; keine fremden Änderungen übernehmen.
                    frappe.db.rollback()
                    _check_run(check_jobs=False)
                if row.get('grund'):
                    raise Blockiert(row['grund'])
                names = by_number.get(row['mitglied_nr'], [])
                if len(names) != 1:
                    raise Blockiert('Erwartet genau eine MVZH-Mitgliedschaft, gefunden: {0}.'.format(len(names)))
                if not dry_run:
                    frappe.db.sql('SELECT name FROM `tabMitgliedschaft` WHERE name = %s FOR UPDATE', (names[0],))
                member = frappe.get_doc('Mitgliedschaft', names[0])
                if member.sektion_id != SEKTION or member.mitglied_nr != row['mitglied_nr']:
                    raise Blockiert('Mitgliedschaft wurde zwischenzeitlich geändert.')
                entry['mitgliedschaft'] = member.name
                invoice = _get_invoice(member, lock=not dry_run)
                entry['rechnung'] = invoice.name
                target, set_reduction = _target(member)
                _check_invoice(invoice, member, sektion)
                change_invoice = not _same(invoice.items[0].rate, target)
                entry.update(bisheriger_betrag=flt(invoice.items[0].rate), zielbetrag=target,
                    reduktion_setzen=set_reduction, rechnung_korrigieren=change_invoice)
                if not set_reduction and not change_invoice:
                    entry['status'] = 'bereits_korrekt'
                else:
                    if change_invoice:
                        _check_unpaid(invoice)
                    _check_price_rule(member, sektion, set_reduction)
                    if dry_run:
                        entry['status'] = 'bereit'
                    else:
                        _apply(member, invoice, sektion, target, set_reduction, change_invoice)
                        frappe.db.commit()
                        entry['status'] = 'korrigiert'
            except Blockiert as error:
                if not dry_run:
                    frappe.db.rollback()
                entry.update(status='blockiert', grund=str(error))
            except Exception as error:
                if not dry_run:
                    frappe.db.rollback()
                entry.update(status='fehler', grund=str(error))
            finally:
                if not dry_run:
                    # Auch reine Lesetransaktionen geben ihre Sperren wieder frei.
                    frappe.db.rollback()
            result[entry['status']] += 1
            result['details'].append(entry)
    finally:
        if not dry_run:
            if previous is None:
                frappe.flags.pop(flag, None)
            else:
                frappe.flags[flag] = previous
    return result


def _read_members(file_path, has_header):
    from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file, read_xls_file_from_attached_file

    extension = os.path.splitext(file_path)[1].lower()
    if extension == '.xlsx':
        rows = read_xlsx_file_from_attached_file(filepath=file_path)
    elif extension == '.xls':
        with open(file_path, 'rb') as source:
            rows = read_xls_file_from_attached_file(source.read())
    else:
        raise ValueError('Bitte eine .xlsx- oder .xls-Datei angeben.')
    entries = []
    seen = set()
    for index, row in enumerate(rows):
        if index == 0 and has_header:
            continue
        value = row[0] if row else None
        if value is None or str(value).strip() == '':
            continue
        entry = {'excel_zeile': index + 1}
        try:
            number = _member_number(value)
            entry['mitglied_nr'] = number
            if number in seen:
                raise Blockiert('Doppelte Mitglied-Nr in Excel; nur die erste Zeile wird verarbeitet.')
            seen.add(number)
        except ValueError as error:
            entry['grund'] = str(error)
        entries.append(entry)
    if not entries:
        raise ValueError('Keine Mitglied-Nr in der ersten Excel-Spalte gefunden.')
    return entries


def _member_number(value):
    if isinstance(value, bool):
        raise ValueError('Ungültige Mitglied-Nr.')
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError('Mitglied-Nr muss eine ganze Zahl sein.')
        value = int(value)
    text = str(value).strip().upper()
    if text.startswith('MV'):
        text = text[2:]
    if not re.match(r'^[0-9]{1,8}$', text) or int(text) <= 0:
        raise ValueError('Ungültige Mitglied-Nr: {0}.'.format(value))
    return 'MV{0}'.format(text.zfill(8))


def _check_run(check_jobs=True):
    run = frappe.get_doc('Mitglied RG Jahreslauf', MRJ)
    if cint(run.bezugsjahr) != JAHR:
        raise Blockiert('Der Jahreslauf hat nicht das Bezugsjahr 2027.')
    if run.status not in ('Rechnungen erstellt', 'PDFs erstellt', 'Test E-Mails versendet',
            'E-Mails versendet', 'Abgeschlossen', 'Abgebrochen', 'Fehlgeschlagen') or run.get('pdf_recreation_documents'):
        raise Blockiert('Jahreslauf ist aktiv oder besitzt eine ausstehende PDF-Neuerstellung.')
    if not check_jobs:
        return
    for job in ('Erstellung Rechnungen', 'Erstellung PDF', 'PDF Neuerstellung',
            'Versende Test E-Mails', 'Versende E-Mails'):
        if is_job_already_running('{0} {1}'.format(job, MRJ)):
            raise Blockiert('Für den Jahreslauf ist noch ein Auftrag aktiv.')


def _target(member):
    enabled = cint(member.reduzierte_mitgliedschaft) == 1
    target = flt(member.reduzierter_betrag) if enabled else NEUE_REDUKTION['reduzierter_betrag']
    if not math.isfinite(target) or target <= 0:
        raise Blockiert('Bestehender abweichender Beitrag ist ungültig oder gratis; manuell prüfen.')
    return target, not enabled


def _get_invoice(member, lock=False):
    invoices = frappe.db.sql('''SELECT name FROM `tabSales Invoice`
        WHERE mrj = %s AND mv_mitgliedschaft = %s AND docstatus < 2
        ORDER BY name{0}'''.format(' FOR UPDATE' if lock else ''), (MRJ, member.name), as_dict=True)
    if len(invoices) != 1:
        raise Blockiert('Erwartet genau eine aktive Rechnung im Jahreslauf, gefunden: {0}.'.format(len(invoices)))
    return frappe.get_doc('Sales Invoice', invoices[0].name)


def _same(left, right):
    return abs(flt(left) - flt(right)) < 0.00001


def _article(member, sektion):
    if member.mitgliedtyp_c == 'Privat':
        return sektion.mitgliedschafts_artikel
    if member.mitgliedtyp_c == 'Geschäft':
        return get_mitgliedschafts_artikel_geschaeft(sektion, member.get('mvb_typ'))
    raise Blockiert('Unbekannter Mitgliedtyp.')


def _check_invoice(invoice, member, sektion):
    if (invoice.docstatus != 1 or invoice.mrj != MRJ or invoice.sektion_id != SEKTION
            or invoice.company != sektion.company or invoice.mv_mitgliedschaft != member.name
            or cint(invoice.mitgliedschafts_jahr) != JAHR or not cint(invoice.ist_mitgliedschaftsrechnung)):
        raise Blockiert('Rechnung ist nicht als MVZH-Mitgliedschaftsrechnung 2027 gebucht.')
    if (len(invoice.items) != 1 or invoice.items[0].item_code != _article(member, sektion)
            or not _same(invoice.items[0].qty, 1)):
        raise Blockiert('Keine eindeutige einzelne Mitgliedschaftsposition mit Menge 1.')
    if (flt(invoice.grand_total) <= 0 or invoice.currency != 'CHF' or invoice.party_account_currency != 'CHF'
            or not _same(invoice.conversion_rate, 1) or invoice.get('taxes')
            or flt(invoice.get('discount_amount')) or flt(invoice.get('additional_discount_percentage'))
            or not _same(invoice.grand_total, invoice.items[0].rate)
            or not _same(invoice.get('rounded_total') or invoice.grand_total, invoice.grand_total)):
        raise Blockiert('Währung, Steuern, Rabatt oder Gesamtbetrag erfordern eine manuelle Prüfung.')


def _check_unpaid(invoice):
    if (invoice.status not in ('Unpaid', 'Overdue')
            or not _same(invoice.outstanding_amount, invoice.grand_total)
            or any(cint(invoice.get(field)) for field in ('is_return', 'is_pos', 'update_stock', 'redeem_loyalty_points'))
            or any(invoice.get(field) for field in ('advances', 'payments', 'timesheets',
                'inter_company_invoice_reference', 'loyalty_program', 'is_deferred_revenue'))
            or any(flt(invoice.get(field)) for field in ('paid_amount', 'total_advance', 'write_off_amount'))
            or any(item.get(field) for item in invoice.items for field in
                ('sales_order', 'delivery_note', 'is_fixed_asset', 'enable_deferred_revenue'))):
        raise Blockiert('Rechnung ist bezahlt, teilbezahlt oder besitzt Zahlungen bzw. Sonderfälle.')
    links = frappe.db.sql('''
        SELECT parent AS name FROM `tabPayment Entry Reference`
        WHERE reference_doctype = 'Sales Invoice' AND reference_name = %s AND docstatus < 2
        UNION ALL
        SELECT parent AS name FROM `tabJournal Entry Account`
        WHERE reference_type = 'Sales Invoice' AND reference_name = %s AND docstatus < 2
        UNION ALL
        SELECT name FROM `tabSales Invoice` WHERE return_against = %s AND docstatus < 2
        UNION ALL
        SELECT voucher_no AS name FROM `tabGL Entry`
        WHERE against_voucher_type = 'Sales Invoice' AND against_voucher = %s
        AND NOT (voucher_type = 'Sales Invoice' AND voucher_no = %s)
        UNION ALL
        SELECT parent AS name FROM `tabMahnung Invoices` WHERE sales_invoice = %s AND docstatus = 1
    ''', (invoice.name,) * 6, as_dict=True)
    if links:
        raise Blockiert('Zahlungszuordnungen, Gutschriften oder Mahnungen vorhanden: {0}.'.format(
            ', '.join(sorted(set(row.name for row in links)))))


def _check_price_rule(member, sektion, needed):
    if not needed:
        return
    if not member.get('mitglied_id') or not (member.rg_kunde or member.kunde_mitglied):
        raise Blockiert('Mitglied-ID oder Rechnungskunde für die Preisregel fehlt.')
    name = 'Reduzierung {0}'.format(member.mitglied_id)
    if frappe.db.exists('Pricing Rule', name):
        rule = frappe.get_doc('Pricing Rule', name)
        if (len(rule.items) != 1 or rule.items[0].item_code != _article(member, sektion)
                or rule.applicable_for != 'Customer' or rule.rate_or_discount != 'Rate'):
            raise Blockiert('Bestehende Preisregel ist ein Sonderfall: {0}.'.format(name))


def _set_reduction(member, sektion):
    # Mitgliedschaft.save() würde zahlreiche fachfremde Prozesse und teilweise
    # commits auslösen. Nur die angefragten Felder und ihre Preisregel ändern.
    frappe.db.set_value('Mitgliedschaft', member.name, NEUE_REDUKTION)
    customer = member.rg_kunde or member.kunde_mitglied
    name = 'Reduzierung {0}'.format(member.mitglied_id)
    if frappe.db.exists('Pricing Rule', name):
        rule = frappe.get_doc('Pricing Rule', name)
        rule.disable = 0
        rule.customer = customer
        rule.valid_upto = NEUE_REDUKTION['reduzierung_bis']
        rule.rate = NEUE_REDUKTION['reduzierter_betrag']
        rule.save(ignore_permissions=True)
    else:
        # Entspricht Mitgliedschaft.erstelle_preisregel(), ohne Zwischen-commit.
        frappe.get_doc({'doctype': 'Pricing Rule', 'title': name, 'selling': 1,
            'applicable_for': 'Customer', 'customer': customer, 'valid_from': '',
            'valid_upto': NEUE_REDUKTION['reduzierung_bis'], 'rate_or_discount': 'Rate',
            'rate': NEUE_REDUKTION['reduzierter_betrag'],
            'items': [{'item_code': _article(member, sektion)}]}).insert(ignore_permissions=True)
    member.add_comment('Comment', text='{0}: Abweichender Mitgliederbeitrag gemäss Excel gesetzt: '
        'Reduziert, CHF 50, gültig bis 31.12.2099. Vorher: {1}.'.format(MRJ,
            ', '.join('{0}={1}'.format(field, member.get(field)) for field in sorted(NEUE_REDUKTION))))


def _apply(member, invoice, sektion, target, set_reduction, change_invoice):
    if set_reduction:
        _set_reduction(member, sektion)
    if not change_invoice:
        return
    expected = invoice.as_dict()
    # unlink_fr() committet im before_cancel-Hook. Deshalb die bekannten FR-Links
    # vorübergehend selbst lösen und innerhalb derselben Transaktion zurücksetzen.
    linked = frappe.db.sql('''SELECT name FROM `tabFakultative Rechnung`
        WHERE sales_invoice = %s AND docstatus = 1 FOR UPDATE''', (invoice.name,), as_dict=True)
    for row in linked:
        frappe.db.set_value('Fakultative Rechnung', row.name, 'sales_invoice', '', update_modified=False)
    invoice.flags.ignore_permissions = True
    invoice.flags.create_mitgliedschaftsrechnung_block = True
    invoice.cancel()
    if invoice.docstatus != 2:
        raise ValueError('Rechnung konnte nicht storniert werden.')
    frappe.db.set_value('Sales Invoice', invoice.name, {'docstatus': 0, 'status': 'Draft'})
    for field in invoice.meta.get_table_fields():
        table = field.options.replace('`', '``')
        frappe.db.sql('UPDATE `tab{0}` SET docstatus = 0 WHERE parent = %s '
            'AND parenttype = %s AND parentfield = %s'.format(table),
            (invoice.name, 'Sales Invoice', field.fieldname))
    invoice.reload()
    invoice.flags.ignore_permissions = True
    invoice.flags.create_mitgliedschaftsrechnung_block = True
    invoice.set_posting_time = 1
    invoice.allocate_advances_automatically = 0
    invoice.items[0].rate = target
    invoice.items[0].price_list_rate = target
    invoice.items[0].discount_percentage = 0
    invoice.items[0].discount_amount = 0
    invoice.outstanding_amount = target
    invoice.save()
    invoice.submit()
    for row in linked:
        frappe.db.set_value('Fakultative Rechnung', row.name, 'sales_invoice', invoice.name, update_modified=False)
    frappe.db.set_value('Sales Invoice', invoice.name,
        'allocate_advances_automatically', expected.get('allocate_advances_automatically'))
    invoice.reload()
    _verify(invoice, expected, target)
    for row in linked:
        if frappe.db.get_value('Fakultative Rechnung', row.name, 'sales_invoice') != invoice.name:
            raise ValueError('Verknüpfung der fakultativen Rechnung wurde nicht wiederhergestellt.')
    invoice.add_comment('Comment', text='{0}: Mitgliederbeitrag gemäss Excel korrigiert '
        'von CHF {1} auf CHF {2}; Originalrechnung storniert und erneut gebucht. '
        'Bestehende PDFs müssen neu erstellt werden.'.format(MRJ, expected['grand_total'], target))


def _verify(invoice, expected, target):
    if invoice.docstatus != 1 or any(row.docstatus != 1 for row in invoice.get_all_children()):
        raise ValueError('Rechnung oder Kindzeilen sind nicht vollständig gebucht.')
    for field in ('name', 'creation', 'amended_from', 'posting_date', 'posting_time', 'due_date',
            'customer', 'company', 'currency', 'party_account_currency', 'esr_reference',
            'mv_mitgliedschaft', 'mitgliedschafts_jahr', 'sektion_id', 'mrj', 'mrj_sektions_selektion'):
        if str(invoice.get(field) or '') != str(expected.get(field) or ''):
            raise ValueError('Feld {0} wurde unerwartet geändert.'.format(field))
    for value in (invoice.items[0].rate, invoice.items[0].amount, invoice.grand_total,
            invoice.base_grand_total, invoice.outstanding_amount,
            invoice.get('rounded_total') or invoice.grand_total):
        if not _same(value, target):
            raise ValueError('Beitrag, Gesamtbetrag oder Restbetrag ist nach Wiederbuchung nicht korrekt.')
    ledger = frappe.db.sql('''SELECT SUM(debit) AS debit, SUM(credit) AS credit,
        SUM(CASE WHEN account = %s AND party_type = 'Customer' AND party = %s
            THEN debit_in_account_currency - credit_in_account_currency ELSE 0 END) AS receivable
        FROM `tabGL Entry` WHERE voucher_type = 'Sales Invoice' AND voucher_no = %s''',
        (invoice.debit_to, invoice.customer, invoice.name), as_dict=True)[0]
    if not (_same(ledger.debit, target) and _same(ledger.credit, target) and _same(ledger.receivable, target)):
        raise ValueError('Buchhaltungseinträge stimmen nicht mit dem korrigierten Beitrag überein.')
