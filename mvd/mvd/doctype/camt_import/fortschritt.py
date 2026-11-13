# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from contextlib import contextmanager
import json
import time
import uuid
import frappe
from mvd.mvd.doctype.camt_import.reset_protokoll import lade, speichere


"""
    Methodensammlung zur Fortschritt-Anzeige einzelner CAMT-Schritte
"""

def _key(camt, token):
    return 'camt_fortschritt:{0}:{1}'.format(camt, token)

def _speichere_status(camt, token, state):
    try:
        frappe.cache().set_value(_key(camt, token), state, expires_in_sec=86400)
    except Exception:
        pass

def pruefe_start(camt):
    doc = frappe.get_doc('CAMT Import', camt)
    doc.check_permission('write')

    active = _laufender_auftrag(camt, doc.status, json.loads(doc.get('reset_protokoll') or '{}'))
    if active:
        return active

    rows = frappe.db.sql('SELECT status, reset_protokoll FROM `tabCAMT Import` WHERE name=%s FOR UPDATE', (camt,), as_dict=True)
    row = rows[0]

    return _laufender_auftrag(camt, row.status, json.loads(row.reset_protokoll or '{}'))

def _laufender_auftrag(camt, status, data):
    if status == 'In Verarbeitung' and (data.get('reset_auftrag') or {}).get('status') in ('queued', 'running'):
        frappe.throw('Der CAMT Reset läuft noch. Bitte warten Sie auf den Abschluss.')
    
    job = data.get('verarbeitung_auftrag') or {}
    context = frappe.flags.get('camt_fortschritt') or {}
    eigener_folgeschritt = (context.get('camt') == camt and context.get('token') == job.get('token') and context.get('generation') == data.get('generation'))

    if (status != 'Failed' and job.get('status') in ('queued', 'running') and job.get('generation') == data.get('generation') and not eigener_folgeschritt):
        return {'status': 'In Verarbeitung', 'progress_token': job['token']}
    
    if status == 'In Verarbeitung' and not eigener_folgeschritt:
        frappe.throw('Dieser CAMT-Import wird bereits verarbeitet. Bitte warten Sie auf den Abschluss.')
    
    return None

def beginnen(camt, generation, schritt):
    doc = frappe.get_doc('CAMT Import', camt)
    doc.check_permission('write')
    data = lade(camt, sperren=True) or {}

    if data.get('generation') != generation:
        frappe.throw('Der CAMT-Import wurde zwischenzeitlich zurückgesetzt. Bitte laden Sie ihn erneut.')
    
    token = uuid.uuid4().hex
    state = {
        'token': token,
        'generation': generation,
        'schritt': schritt,
        'status': 'queued',
        'done': 0,
        'total': None,
        'percent': 0,
        'message': 'Warte auf einen Hintergrund-Worker.'
    }
    previous = data.get('verarbeitung_auftrag') or {}
    context = frappe.flags.get('camt_fortschritt') or {}

    if (context.get('camt') == camt and context.get('token') == previous.get('token') and context.get('generation') == generation):
        state['vorgaenger'] = list(previous.get('vorgaenger') or []) + [previous['token']]
    
    data['verarbeitung_auftrag'] = dict(state)
    speichere(camt, data)
    _speichere_status(camt, token, state)

    return token

@contextmanager
def erfassen(camt, token, generation, schritt):
    data = lade(camt, sperren=True) or {}
    job = data.get('verarbeitung_auftrag') or {}

    if (job.get('token') != token or data.get('generation') != generation or job.get('status') not in ('queued', 'running') or (data.get('reset_auftrag') or {}).get('status') in ('queued', 'running')):
        yield False
        return
    
    previous = frappe.flags.get('camt_fortschritt')
    context = {
        'camt': camt,
        'token': token,
        'generation': generation,
        'schritt': schritt,
        'done': 0,
        'total': None,
        'last_update': None,
        'message': 'Bereite Verarbeitung vor.'
    }

    frappe.flags.camt_fortschritt = context

    try:
        _melden(context, force=True)
        yield True
    finally:
        frappe.flags.camt_fortschritt = previous

def _melden(context, force=False):
    now = time.monotonic()
    if not force and context['last_update'] is not None and now - context['last_update'] < 1:
        return
    
    context['last_update'] = now
    total = context['total']
    state = {
        'status': 'running',
        'token': context['token'],
        'generation': context['generation'],
        'schritt': context['schritt'],
        'done': context['done'],
        'total': total,
        'percent': min(95, round(95 * context['done'] / total, 1)) if total else 0,
        'message': context['message']
    }

    _speichere_status(context['camt'], context['token'], state)

def melden(camt, schritt, done, total, message=None):
    context = frappe.flags.get('camt_fortschritt')
    if context and context['camt'] == camt and context['schritt'] == schritt:
        text = message or 'Verarbeite Zahlungen.'
        changed = text != context['message']
        context.update(done=done, total=total, message=text)
        _melden(context, force=changed)

def uebersicht(camt):
    context = frappe.flags.get('camt_fortschritt')
    if context and context['camt'] == camt:
        context['message'] = 'Schliesse Rücksetzprotokoll und Übersicht ab.'
        _melden(context, force=True)

def abschliessen(camt, token, result):
    data = lade(camt, sperren=True) or {}
    job = data.get('verarbeitung_auftrag') or {}
    context = frappe.flags.get('camt_fortschritt') or {}
    if context.get('token') != token:
        context = {}
    
    next_token = result.get('progress_token') if isinstance(result, dict) else None

    if next_token and next_token != token and job.get('token') == next_token:
        state = {
            'status': 'weiter',
            'next_token': next_token,
            'token': token,
            'generation': data.get('generation')
        }
    elif job.get('token') == token:
        failed = isinstance(result, dict) and result.get('status') == 'Failed'
        paused = isinstance(result, dict) and result.get('status') == 'paused'
        state = dict(job, status='failed' if failed else 'paused' if paused else 'done', percent=100, done=context.get('done', 0), total=context.get('total'), message='Verarbeitung abgeschlossen.')
        if failed:
            state['error'] = result.get('message')
        if paused:
            state['message'] = result.get('message')
        data['verarbeitung_auftrag'] = dict(state)
        speichere(camt, data)
    else:
        return
    
    frappe.db.commit()
    _speichere_status(camt, token, state)

def beim_laden(doc):
    if doc.status == 'Failed':
        return None
    
    data = json.loads(doc.get('reset_protokoll') or '{}')
    job = data.get('verarbeitung_auftrag') or {}

    if ((data.get('reset_auftrag') or {}).get('status') not in ('queued', 'running') and job.get('generation') == data.get('generation') and job.get('status') in ('queued', 'running')):
        return {
            'token': job['token'],
            'schritt': job['schritt']
        }
    
    return None

@frappe.whitelist()
def status(camt, token):
    doc = frappe.get_doc('CAMT Import', camt)
    doc.check_permission('write')
    data = json.loads(doc.get('reset_protokoll') or '{}')
    job = data.get('verarbeitung_auftrag') or {}
    try:
        cached = frappe.cache().get_value(_key(camt, token), expires=True)
    except Exception:
        cached = None
    
    if job.get('token') != token:
        if (token in (job.get('vorgaenger') or []) and job.get('generation') == data.get('generation') and (data.get('reset_auftrag') or {}).get('status') not in ('queued', 'running')):
            return {
                'status': 'weiter',
                'next_token': job['token'],
                'token': token,
                'generation': data.get('generation')
            }
        
        if (cached and cached.get('status') == 'weiter' and cached.get('generation') == data.get('generation') and (data.get('reset_auftrag') or {}).get('status') not in ('queued', 'running')):
            return cached
        
        return {'status': 'veraltet'}
    
    if job.get('generation') != data.get('generation') or (data.get('reset_auftrag') or {}).get('status') in ('queued', 'running'):
        return {'status': 'veraltet'}
    
    if job.get('status') in ('done', 'failed', 'paused'):
        return job
    
    if doc.status == 'Failed':
        return dict(job, status='failed', error=doc.get('errors'))
    
    return cached if cached and cached.get('generation') == data.get('generation') else job
