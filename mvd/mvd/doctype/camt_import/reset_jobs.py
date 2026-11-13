# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import time
import uuid
import frappe
from frappe.utils.background_jobs import enqueue
from mvd.mvd.doctype.camt_import.reset_protokoll import initialisiere, lade, speichere
from mvd.mvd.doctype.camt_import.reset import _zuruecksetzen

def _cache_key(camt):
    return 'camt_reset_status:' + camt

def _status_speichern(camt, state):
    try:
        frappe.cache().set_value(_cache_key(camt), state, expires_in_sec=86400)
    except Exception:
        pass

def _zugriff(camt, post=False):
    if 'System Manager' not in frappe.get_roles() or (post and frappe.local.request.method != 'POST'):
        frappe.throw('Nur System Manager dürfen einen CAMT-Reset ausführen.', frappe.PermissionError)
    
    doc = frappe.get_doc('CAMT Import', camt)
    doc.check_permission('write')

    return doc

def starten(camt):
    doc = _zugriff(camt, post=True)
    data = json.loads(doc.get('reset_protokoll') or '{}')
    active = data.get('reset_auftrag') or {}

    if doc.status == 'In Verarbeitung':
        if active.get('status') in ('queued', 'running'):
            return {'status': 'queued', 'token': active['token']}
        
        frappe.throw('Bitte warten Sie, bis die CAMT-Verarbeitung abgeschlossen ist.')
    
    frappe.db.sql('SELECT name FROM `tabCAMT Import` WHERE name=%s FOR UPDATE', (camt,))
    doc = _zugriff(camt)

    if doc.status == 'In Verarbeitung':
        active = (lade(camt) or {}).get('reset_auftrag') or {}
        if active.get('status') in ('queued', 'running'):
            return {
                'status': 'queued',
                'token': active['token']
            }
        
        frappe.throw('Bitte warten Sie, bis die CAMT-Verarbeitung abgeschlossen ist.')
    
    data = initialisiere(camt)
    if data.get('offen'):
        frappe.throw('Ein CAMT-Verarbeitungsschritt ist noch offen. Bitte prüfen Sie zuerst dessen Fehlerprotokoll.')
    
    token = uuid.uuid4().hex
    data['reset_auftrag'] = {'token': token, 'status': 'queued'}

    speichere(camt, data)

    frappe.db.set_value('CAMT Import', camt, {'status': 'In Verarbeitung', 'errors': None})
    try:
        enqueue('mvd.mvd.doctype.camt_import.reset_jobs.ausfuehren', queue='long', timeout=7200, job_name='CAMT Reset {0} ({1})'.format(camt, token), camt=camt, token=token, generation=data['generation'])
    except Exception:
        frappe.db.rollback()
        raise

    state = {
        'status': 'queued',
        'token': token,
        'percent': 0,
        'message': 'CAMT Reset wartet auf einen Hintergrund-Worker.'
    }
    _status_speichern(camt, state)

    return state

@frappe.whitelist()
def status(camt, token):
    doc = _zugriff(camt)
    data = json.loads(doc.get('reset_protokoll') or '{}')
    active = data.get('reset_auftrag') or {}

    if active and active.get('token') != token:
        return {'status': 'veraltet'}
    
    if doc.status not in ('In Verarbeitung', 'Open', 'Failed') or (doc.status == 'In Verarbeitung' and data.get('offen')):
        return {'status': 'veraltet'}
    
    cached = frappe.cache().get_value(_cache_key(camt), expires=True)
    if cached and cached.get('token') == token and (cached.get('status') == 'done' and doc.status != 'Open' or cached.get('status') == 'failed' and doc.status != 'Failed'):
        return {'status': 'veraltet'}
    
    if cached and cached.get('token') == token and (active or doc.status == 'Open'):
        return cached
    
    if active.get('token') == token:
        if active.get('status') in ('queued', 'running') and doc.status != 'In Verarbeitung':
            return {'status': 'veraltet'}
        
        return {
            'status': active['status'],
            'token': token,
            'percent': 0,
            'message': 'CAMT Reset läuft im Hintergrund.',
            'error': doc.get('errors')
        }
    
    return {
        'status': 'done' if doc.status == 'Open' else 'veraltet',
        'token': token
    }

def ausfuehren(camt, token, generation):
    frappe.db.sql('SELECT name FROM `tabCAMT Import` WHERE name=%s FOR UPDATE', (camt,))

    data = lade(camt) or {}
    if data.get('generation') != generation or (data.get('reset_auftrag') or {}).get('token') != token:
        return {'status': 'veraltet'}
    
    queued_before = list(frappe.flags.get('enqueue_after_commit') or [])
    realtime_before = list(getattr(frappe.local, 'realtime_log', None) or [])
    last_update = [0]

    def progress(percent, message):
        now = time.monotonic()
        if now - last_update[0] >= 1:
            last_update[0] = now
            _status_speichern(camt, {'status': 'running', 'token': token, 'percent': round(percent, 1), 'message': message})

    progress(0, 'Prüfe Belege und Vorzustände')

    try:
        _zugriff(camt)
        result = _zuruecksetzen(camt, reset_token=token, fortschritt=progress)
        frappe.db.commit()
    except Exception as err:
        details = 'CAMT Reset: {0}\n\n{1}'.format(str(err) or type(err).__name__, frappe.get_traceback())
        frappe.db.rollback()
        frappe.flags.enqueue_after_commit = queued_before
        frappe.local.realtime_log = realtime_before
        frappe.db.sql('SELECT name FROM `tabCAMT Import` WHERE name=%s FOR UPDATE', (camt,))
        current = lade(camt) or {}
        if (current.get('reset_auftrag') or {}).get('token') == token:
            current['reset_auftrag']['status'] = 'failed'
            speichere(camt, current)
            frappe.db.set_value('CAMT Import', camt, {'status': 'Failed', 'errors': details})

            try:
                frappe.log_error(details, 'CAMT Reset {0}'.format(camt))
            except Exception:
                pass
                
            frappe.db.commit()
            _status_speichern(camt, {'status': 'failed', 'token': token, 'error': details})
        
        return {'status': 'failed'}
    
    state = {
        'status': 'done',
        'token': token,
        'percent': 100,
        'result': result
    }
    _status_speichern(camt, state)
    
    return state
