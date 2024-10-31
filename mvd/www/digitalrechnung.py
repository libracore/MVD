from __future__ import unicode_literals
import frappe
from urllib.parse import urlparse
from urllib.parse import parse_qs
from frappe.utils.data import today
from frappe.utils import cint

no_cache = 1

def get_context(context):
    try:
        url = frappe.request.url
        parsed_url = urlparse(url)
        hash = parse_qs(parsed_url.query)['hash'][0]
        hash_check = check_hash(hash)
        context['language'] = 'de'
        if hash_check:
            if hash_check['stage'] == 'opt_in':
                context['hash_check'] = 'bestätigung'
                context['email'] = hash_check['email']
                context['opt_in'] = hash_check['opt_in']
                context['opt_out'] = hash_check['opt_out']
                context['digitalrechnung'] = hash_check['digitalrechnung']
            elif hash_check['stage'] == 'no_mail':
                context['hash_check'] =  'add mail'
                context['email'] = hash_check['email']
                context['opt_in'] = hash_check['opt_in']
                context['opt_out'] = hash_check['opt_out']
                context['digitalrechnung'] = hash_check['digitalrechnung']
            elif hash_check['stage'] == 'opt_out':
                context['hash_check'] =  'show opt out'
                context['email'] = hash_check['email']
                context['opt_in'] = hash_check['opt_in']
                context['opt_out'] = hash_check['opt_out']
                context['digitalrechnung'] = hash_check['digitalrechnung']
            elif hash_check['stage'] == 'opt_out_reload':
                context['hash_check'] =  'show opt out bestätigung'
                context['email'] = hash_check['email']
                context['opt_in'] = hash_check['opt_in']
                context['opt_out'] = hash_check['opt_out']
                context['digitalrechnung'] = hash_check['digitalrechnung']
            else:
                context['hash_check'] = "unknown_error"
        else:
            context['hash_check'] = "unknown_error"
    except:
        context['hash_check'] = "unknown_error"

def check_hash(hash):
    try:
        if hash:
            existing_digitalrechnung = frappe.db.exists("Digitalrechnung", {'hash': hash})
            if existing_digitalrechnung:
                return handle_digitalrechnung_onload(existing_digitalrechnung)
            else:
                # wrong hash
                return False
        else:
            # no hash
            return False
    except:
        return False

def handle_digitalrechnung_onload(digitalrechnung):
    dr = frappe.get_doc("Digitalrechnung", digitalrechnung)
    if not dr.opt_in:
        if dr.email:
            if not cint(dr.no_auto_opt_in) == 1:
                dr.set_opt_in()
                dr.save(ignore_permissions=True)
                frappe.db.commit()
                return {
                    'stage': 'opt_in',
                    'email': dr.email,
                    'opt_in': frappe.utils.get_datetime(today()).strftime('%d.%m.%Y'),
                    'opt_out': '-',
                    'digitalrechnung': digitalrechnung
                }
            else:
                dr.no_auto_opt_in = 0
                dr.save(ignore_permissions=True)
                frappe.db.commit()
                return {
                    'stage': 'opt_out_reload',
                    'email': dr.email,
                    'opt_in': '-',
                    'opt_out': frappe.utils.get_datetime(dr.opt_out).strftime('%d.%m.%Y'),
                    'digitalrechnung': digitalrechnung
                }
        else:
            return {
                'stage': 'no_mail',
                'email': '',
                'opt_in': '-',
                'opt_out': '-',
                'digitalrechnung': digitalrechnung
            }
    else:
        return {
                'stage': 'opt_out',
                'email': dr.email,
                'opt_in': frappe.utils.get_datetime(dr.opt_in).strftime('%d.%m.%Y'),
                'opt_out': '-',
                'digitalrechnung': digitalrechnung
            }

@frappe.whitelist()
def handle_digitalrechnung_optout(digitalrechnung):
    dr = frappe.get_doc("Digitalrechnung", digitalrechnung)
    dr.set_opt_out()
    dr.save(ignore_permissions=True)
    frappe.db.commit()
    return

@frappe.whitelist()
def handle_digitalrechnung_email(digitalrechnung, email):
    dr = frappe.get_doc("Digitalrechnung", digitalrechnung)
    dr.email = email
    dr.email_changed = 1
    dr.save(ignore_permissions=True)
    frappe.db.commit()
    return {
        'stage': 'opt_out',
        'email': dr.email,
        'opt_in': frappe.utils.get_datetime(today()).strftime('%d.%m.%Y'),
        'opt_out': '-',
        'digitalrechnung': digitalrechnung
    }