from __future__ import unicode_literals
import frappe
from urllib.parse import urlparse
from urllib.parse import parse_qs
from frappe.utils.data import today
from frappe.utils import cint

no_cache = 1

def sektion_web(sektion_id):
    section_to_url = {
        'MVLU': 'mv-lu',
        'MVZG': 'mv-zg',
        'MVBS': 'mv-bs',
        'MVSZ': 'mv-sz',
        'MVSH': 'mv-sh',
        'MVDF': 'mv-fr', # das ist die Ausnahme
        'MVSO': 'mv-so',
        'MVOS': 'mv-os',
        'MVGR': 'mv-gr',
        'MVBE': 'mv-be',
        'MVAG': 'mv-ag',
        'MVZH': 'mv-zh',
        'MVBL': 'mv-bl'
    }
    return section_to_url.get(sektion_id)

def get_context(context):
    try:
        url = frappe.request.url
        parsed_url = urlparse(url)
        hash = parse_qs(parsed_url.query)['hash'][0]
        hash_check = check_hash(hash)
        if hash_check:
            if hash_check['stage'] == 'opt_in':
                context['hash_check'] = 'bestätigung'
                context['email'] = hash_check['email']
                context['opt_in'] = hash_check['opt_in']
                context['opt_out'] = hash_check['opt_out']
                context['digitalrechnung'] = hash_check['digitalrechnung']
                context['sektion_web'] = sektion_web(hash_check['sektion_id'])
                context['language'] = hash_check['language'] or 'de'
            elif hash_check['stage'] == 'no_mail':
                context['hash_check'] =  'add mail'
                context['email'] = hash_check['email']
                context['opt_in'] = hash_check['opt_in']
                context['opt_out'] = hash_check['opt_out']
                context['digitalrechnung'] = hash_check['digitalrechnung']
                context['sektion_web'] = sektion_web(hash_check['sektion_id'])
                context['language'] = hash_check['language'] or 'de'
            elif hash_check['stage'] == 'opt_out':
                context['hash_check'] =  'show opt out'
                context['email'] = hash_check['email']
                context['opt_in'] = hash_check['opt_in']
                context['opt_out'] = hash_check['opt_out']
                context['digitalrechnung'] = hash_check['digitalrechnung']
                context['sektion_web'] = sektion_web(hash_check['sektion_id'])
                context['language'] = hash_check['language'] or 'de'
            elif hash_check['stage'] == 'opt_out_reload':
                context['hash_check'] =  'show opt out bestätigung'
                context['email'] = hash_check['email']
                context['opt_in'] = hash_check['opt_in']
                context['opt_out'] = hash_check['opt_out']
                context['digitalrechnung'] = hash_check['digitalrechnung']
                context['sektion_web'] = sektion_web(hash_check['sektion_id'])
                context['language'] = hash_check['language'] or 'de'
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
                # Digitalrechnung anhand Hash nicht gefunden, suche nach Mitglied basierend auf Hash
                existing_mitglied_based_on_hash = frappe.db.exists("Mitgliedschaft", {'mitglied_hash': hash})
                if existing_mitglied_based_on_hash:
                    # Mitglied auf Basis Hash gefunden, suche nach Digitalrechnung anhand Mitglied
                    existing_digital_rg_based_on_mitglied = frappe.db.exists("Digitalrechnung", {'mitglied_id': existing_mitglied_based_on_hash})
                    if existing_digital_rg_based_on_mitglied:
                        # Digitalrechnung anhand Mitglied gefunden, Update Hash in Digitalrechnung
                        frappe.db.set_value("Digitalrechnung", existing_digital_rg_based_on_mitglied, 'hash', hash)
                        return handle_digitalrechnung_onload(existing_digital_rg_based_on_mitglied)
                    else:
                        # Digitalrechnung anhand Mitglied nicht gefunden, lege neue Digitalrechnung an
                        from mvd.mvd.doctype.digitalrechnung.digitalrechnung import digitalrechnung_mapper
                        m = frappe.get_doc("Mitgliedschaft", existing_mitglied_based_on_hash)
                        mitglied_hash = digitalrechnung_mapper(mitglied=m)
                        # Suche nach neu erzeugter digitalrechnung
                        existing_digitalrechnung = frappe.db.exists("Digitalrechnung", {'hash': hash})
                        if existing_digitalrechnung:
                            # Neue Digitalrechnung gefunden
                            return handle_digitalrechnung_onload(existing_digitalrechnung)
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
                    'sektion_id': dr.sektion_id,
                    'language' : dr.language,
                    'digitalrechnung': digitalrechnung,
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
                    'sektion_id': dr.sektion_id,
                    'language' : dr.language,
                    'digitalrechnung': digitalrechnung
                }
        else:
            return {
                'stage': 'no_mail',
                'email': '',
                'opt_in': '-',
                'opt_out': '-',
                'sektion_id': dr.sektion_id,
                'language' : dr.language,
                'digitalrechnung': digitalrechnung
            }
    else:
        return {
                'stage': 'opt_out',
                'email': dr.email,
                'opt_in': frappe.utils.get_datetime(dr.opt_in).strftime('%d.%m.%Y'),
                'opt_out': '-',
                'sektion_id': dr.sektion_id,
                'language' : dr.language,
                'digitalrechnung': digitalrechnung
            }

@frappe.whitelist(allow_guest=True)
def handle_digitalrechnung_optout(digitalrechnung):
    dr = frappe.get_doc("Digitalrechnung", digitalrechnung)
    dr.set_opt_out()
    dr.save(ignore_permissions=True)
    frappe.db.commit()
    return

@frappe.whitelist(allow_guest=True)
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