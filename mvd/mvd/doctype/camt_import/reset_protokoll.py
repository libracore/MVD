# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from contextlib import contextmanager
from functools import wraps
import hashlib
import inspect
import json
import uuid
import frappe


MITGLIED_FELDER = [
    'datum_zahlung_mitgliedschaft',
    'bezahltes_mitgliedschaftsjahr',
    'eintrittsdatum',
    'status_c',
    'mitglied_nr',
    'datum_hv_zahlung',
    'zahlung_hv',
    'ampel_farbe',
    'begruessung_massendruck',
    'begruessung_via_zahlung',
    'begruessung_massendruck_dokument',
    'modified',
    'modified_by'
]

ERZEUGTE_BELEGE = (
    'Payment Entry',
    'Journal Entry',
    'Sales Invoice',
    'Fakultative Rechnung',
    'Korrespondenz',
    'Status Change',
    'Communication',
    'Email Queue',
    'File',
    'ToDo'
)

def normalisiere(value):
    return json.loads(json.dumps(value, default=str, ensure_ascii=False))

def fingerprint(doc):
    values = doc.as_dict()
    if doc.doctype == 'Communication':
        values = dict((field, doc.get(field)) for field in ('name', 'subject', 'content', 'sender', 'recipients', 'reference_doctype', 'reference_name'))
    
    return hashlib.sha256(json.dumps(normalisiere(values), sort_keys=True, ensure_ascii=True).encode('utf-8')).hexdigest()

def lade(camt, sperren=False):
    if sperren:
        rows = frappe.db.sql('SELECT reset_protokoll FROM `tabCAMT Import` WHERE name=%s FOR UPDATE', (camt,))
        data = rows[0][0] if rows else None
    else:
        data = frappe.db.get_value('CAMT Import', camt, 'reset_protokoll')
    
    return json.loads(data) if data else None

def speichere(camt, data):
    frappe.db.set_value('CAMT Import', camt, 'reset_protokoll', json.dumps(data, ensure_ascii=False), update_modified=False)

def initialisiere(camt):
    if not frappe.get_meta('CAMT Import').has_field('reset_protokoll'):
        frappe.throw('Bitte synchronisieren Sie zuerst die neuen CAMT-Felder. Das Rücksetzprotokoll fehlt.')
    
    data = lade(camt, sperren=True)
    if data:
        return data

    doc = frappe.get_doc('CAMT Import', camt)
    doc.check_permission('write')
    leer = not frappe.db.exists('Payment Entry', {'camt_import': camt})
    data = {
        'version': 1,
        'generation': uuid.uuid4().hex,
        'vollstaendig': bool(leer and doc.status == 'Open'),
        'offen': False,
        'vorher': [],
        'erstellt': []
    }

    speichere(camt, data)

    return data

def generation(camt):
    return initialisiere(camt)['generation']

def generation_fuer_verarbeitung(camt):
    data = initialisiere(camt)
    if data.get('reset_auftrag') and frappe.db.get_value('CAMT Import', camt, 'status') != 'In Verarbeitung':
        data.pop('reset_auftrag')
        speichere(camt, data)
    
    return data['generation']

def ist_aktuell(camt, erwartete_generation):
    data = lade(camt, sperren=True)
    if not erwartete_generation:
        return not (data and data.get('vollstaendig'))
    
    return bool(data and data['generation'] == erwartete_generation)

def _zustand(doctype, name, felder):
    return normalisiere(frappe.db.get_value(doctype, name, felder, as_dict=True))

def merke_vorzustand(doctype, name, felder):
    context = frappe.flags.get('camt_reset_kontext')
    if not context or frappe.flags.get('camt_reset_in_arbeit'):
        return
    
    data = context['data']
    if any(row['doctype'] == doctype and row['name'] == name for row in data['erstellt']):
        markiere_beleg(doctype, name)
        return
    
    # Objekt sperren, bevor sein Vorzustand gelesen und verändert wird
    if doctype not in ('Mitgliedschaft', 'Fakultative Rechnung', 'Mitglied Main Naming'):
        frappe.throw('Diese Belegart ist für CAMT-Vorzustände nicht vorgesehen.')
    
    frappe.db.sql('SELECT name FROM `tab{0}` WHERE name=%s FOR UPDATE'.format(doctype), (name,))

    key = (doctype, name)
    for row in data['vorher']:
        if row['doctype'] == doctype and row['name'] == name:
            if key not in context['vorher_beruehrt'] and row.get('nachher') is not None:
                current = _zustand(doctype, name, list(row['vorher']))
                fields = [field for field in row['vorher'] if doctype != 'Fakultative Rechnung' or field not in ('modified', 'modified_by')]
                if current is None or any(current.get(field) != row['nachher'].get(field) for field in fields):
                    row['konflikt'] = True
            
            neue_felder = [field for field in felder if field not in row['vorher']]
            if neue_felder:
                row['vorher'].update(_zustand(doctype, name, neue_felder))
            
            context['vorher_beruehrt'].add(key)
            speichere(context['camt'], data)

            return
    
    data['vorher'].append({'doctype': doctype, 'name': name, 'vorher': _zustand(doctype, name, felder)})
    context['vorher_beruehrt'].add(key)
    speichere(context['camt'], data)

def protokolliere_neuen_beleg(doc, event=None):
    context = frappe.flags.get('camt_reset_kontext')
    if not context or frappe.flags.get('camt_reset_in_arbeit') or doc.doctype not in ERZEUGTE_BELEGE:
        return
    
    rows = context['data']['erstellt']
    if not any(row['doctype'] == doc.doctype and row['name'] == doc.name for row in rows):
        rows.append({'doctype': doc.doctype, 'name': doc.name})
        context['erstellt_beruehrt'].add((doc.doctype, doc.name))
        speichere(context['camt'], context['data'])

def markiere_beleg(doctype, name):
    context = frappe.flags.get('camt_reset_kontext')
    if not context:
        return
    
    key = (doctype, name)
    for row in context['data']['erstellt']:
        if (row['doctype'], row['name']) == key:
            if key not in context['erstellt_beruehrt'] and row.get('fingerprint'):
                if fingerprint(frappe.get_doc(doctype, name)) != row['fingerprint']:
                    row['konflikt'] = True

            context['erstellt_beruehrt'].add(key)

            return

@contextmanager
def erfassen(camt):
    previous = frappe.flags.get('camt_reset_kontext')
    if not camt or frappe.flags.get('camt_reset_in_arbeit') or (previous and previous['camt'] == camt):
        yield
        return
    
    if previous:
        frappe.throw('Zwei CAMT-Importe dürfen nicht im selben Verarbeitungsschritt vermischt werden.')
    
    data = initialisiere(camt)
    data['offen'] = True

    speichere(camt, data)

    context = {
        'camt': camt,
        'data': data,
        'vorher_beruehrt': set(),
        'erstellt_beruehrt': set()
    }
    frappe.flags.camt_reset_kontext = context

    try:
        yield
    finally:
        try:
            current = lade(camt, sperren=True)
            if current and current['generation'] == data['generation']:
                for row in data['vorher']:
                    if (row['doctype'], row['name']) in context['vorher_beruehrt']:
                        row['nachher'] = _zustand(row['doctype'], row['name'], list(row['vorher']))
                
                for row in data['erstellt']:
                    if ((row['doctype'], row['name']) in context['erstellt_beruehrt'] and frappe.db.exists(row['doctype'], row['name'])):
                        row['fingerprint'] = fingerprint(frappe.get_doc(row['doctype'], row['name']))
                
                data['offen'] = False
                speichere(camt, data)
        finally:
            frappe.flags.camt_reset_kontext = previous

def mit_protokoll(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        kwargs = frappe.get_newargs(fn, kwargs)
        params = inspect.getcallargs(fn, *args, **kwargs)
        camt = params.get('camt_import')
        if not camt and params.get('pe'):
            camt = frappe.db.get_value('Payment Entry', params['pe'], 'camt_import')
        
        with erfassen(camt):
            return fn(*args, **kwargs)
        
    return wrapped

def beginne_zahlung(pe, event=None):
    if not pe.get('camt_import') or frappe.flags.get('camt_reset_in_arbeit'):
        return
    
    previous = frappe.flags.get('camt_reset_kontext')
    if previous and previous['camt'] != pe.camt_import:
        frappe.throw('Die Zahlung gehört zu einem anderen CAMT-Import als der laufende Verarbeitungsschritt.')
    
    if not frappe.flags.get('camt_reset_kontext'):
        context = erfassen(pe.camt_import)
        context.__enter__()
        pe.flags.camt_reset_context = context
    
    for row in pe.references:
        if row.reference_doctype == 'Sales Invoice':
            markiere_beleg('Sales Invoice', row.reference_name)
    
    if pe.get('camt_verrechnung_rechnung'):
        markiere_beleg('Sales Invoice', pe.camt_verrechnung_rechnung)

def beende_zahlung(pe, event=None):
    context = pe.flags.get('camt_reset_context')
    if context:
        pe.flags.camt_reset_context = None
        context.__exit__(None, None, None)

def merke_mitglied(mitglied_id):
    merke_vorzustand('Mitgliedschaft', mitglied_id, MITGLIED_FELDER)

def merke_nummer(mitglied_id):
    if not frappe.flags.get('camt_reset_kontext'):
        return
    
    name = frappe.db.get_value('Mitglied Main Naming', {'mitglied_id': mitglied_id}, 'name')
    if name:
        merke_vorzustand('Mitglied Main Naming', name, ['mitglied_nr', 'mitglied_nr_raw', 'modified', 'modified_by'])
