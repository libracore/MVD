# -*- coding: utf-8 -*-
# Copyright (c) 2021-2026, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime


def draft_name(doctype_reference, docname, user):
    """
        Diese Methode erstellt einen Primärschlüssel, welcher mehrere neue Entwürfe pro Benutzer/Dokument verhindert
    """
    key = json.dumps([user, doctype_reference, docname], ensure_ascii=True)
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

def _reference(doctype_reference, docname, user=None):
    session_user = frappe.session.user
    if session_user == 'Guest' or (user and user != session_user):
        frappe.throw(_('Keine Berechtigung für diesen E-Mail-Entwurf.'), frappe.PermissionError)
    
    if not doctype_reference or not docname or doctype_reference == 'Email Drafts':
        frappe.throw(_('Ein gespeichertes Referenzdokument ist erforderlich.'))
    
    doc = frappe.get_doc(doctype_reference, docname)
    doc.check_permission('read')
    doc.check_permission('email')

    return {
        'doctype_reference': doctype_reference,
        'docname': docname,
        'user': session_user
    }

def _find_draft(reference):
    name = draft_name(reference['doctype_reference'], reference['docname'], reference['user'])
    if frappe.db.exists('Email Drafts', name):
        return name
    
    return frappe.db.get_value('Email Drafts', reference, 'name', order_by='modified desc')

def _state(mail, legacy=False):
    try:
        state = json.loads(mail) if isinstance(mail, str) else mail
    except (TypeError, ValueError):
        if legacy:
            return {'version': 1, 'fields': {'content': mail or ''}}
        frappe.throw(_('Der E-Mail-Entwurf enthält ungültige Daten.'))
    if not isinstance(state, dict) or state.get('version') != 1 or not isinstance(state.get('fields'), dict):
        # Die vorherige Version des Email Drafts enthielt nur den HTML-Nachrichtentext
        if legacy:
            return {'version': 1, 'fields': {'content': mail or ''}}
        frappe.throw(_('Der E-Mail-Entwurf enthält ungültige Daten.'))
    
    return state

@frappe.whitelist()
def save_draft_mail(doctype_reference=None, docname=None, mail=None, user=None):
    reference = _reference(doctype_reference, docname, user)
    payload = json.dumps(_state(mail), ensure_ascii=False)
    name = _find_draft(reference)
    if name:
        draft = frappe.get_doc('Email Drafts', name)
        draft.mail = payload
        draft.save(ignore_permissions=True)
    else:
        draft = frappe.get_doc(dict(reference, doctype='Email Drafts', mail=payload))
        draft.insert(ignore_permissions=True)
    return {
        'name': draft.name,
        'modified': str(draft.modified)
    }

@frappe.whitelist()
def load_draft_mail(doctype_reference=None, docname=None, user=None):
    reference = _reference(doctype_reference, docname, user)
    name = _find_draft(reference)
    if name:
        draft = frappe.get_doc('Email Drafts', name)
        return {
            'name': draft.name,
            'modified': str(draft.modified),
            'state': _state(draft.mail, legacy=True)
        }

@frappe.whitelist()
def delete_draft_mail(doctype_reference=None, docname=None, user=None, modified=None):
    reference = _reference(doctype_reference, docname, user)
    _delete_draft(reference, modified)


def _delete_draft(reference, modified=None):
    condition = ' AND `modified` = %(modified)s' if modified else ''
    frappe.db.sql('''
        DELETE FROM `tabEmail Drafts`
        WHERE `doctype_reference` = %(doctype_reference)s
        AND `docname` = %(docname)s
        AND `user` = %(user)s
    ''' + condition, dict(reference, modified=modified))

@frappe.whitelist()
def send_mail(doctype=None, name=None, content=None, subject=None, sender=None,
              sender_full_name=None, recipients=None, print_html=None, print_format=None,
              attachments='[]', send_me_a_copy=False, cc=None, bcc=None, read_receipt=None,
              print_letterhead=True, email_template=None, draft_modified=None, send_context=None):
    from frappe.core.doctype.communication.email import make

    reference = _reference(doctype, name)
    if send_context:
        if send_context != 'coop' or doctype != 'RSVMitglied':
            frappe.throw(_('Ungültiger E-Mail-Versandkontext.'))
        frappe.get_doc(doctype, name).check_permission('write')
    
    result = make(doctype=doctype, name=name, content=content, subject=subject,
                  sender=sender, sender_full_name=sender_full_name, recipients=recipients,
                  print_html=print_html, print_format=print_format, attachments=attachments,
                  send_me_a_copy=send_me_a_copy, cc=cc, bcc=bcc, read_receipt=read_receipt,
                  print_letterhead=print_letterhead, email_template=email_template, send_email=True)
    
    if not result.get('emails_not_sent_to'):
        if send_context == 'coop':
            from mvd.mvd.doctype.rsvmitglied.rsvmitglied import mark_coop_email_sent
            mark_coop_email_sent(name)
        
        if draft_modified:
            # Nur exakt diesen Draft löschen, wurde paralell in einem anderen Tab der Draft verändert, bleibt dieser bestehen
            _delete_draft(reference, draft_modified)
    
    return result


def cleanup_old_drafts():
    """
        Clean-Up Job; alle seit mehr als 14 Tagen unveränderte Entwürfe löschen
    """
    frappe.db.sql('DELETE FROM `tabEmail Drafts` WHERE `modified` < %s', (add_days(now_datetime(), -14),))
