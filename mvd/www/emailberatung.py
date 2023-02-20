from __future__ import unicode_literals
import frappe
import json
import jwt
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr
from frappe.core.doctype.communication.email import make

no_cache = 1

def get_context(context):
    authorization_header = frappe.get_request_header("Cookie", None)
    jwt_token = None
    
    if authorization_header:
        for cookie in authorization_header.split(";"):
            if cookie.startswith(" jwt_auth="):
                jwt_token = cookie.split(" jwt_auth=")[1]
            elif cookie.startswith("jwt_auth="):
                jwt_token = cookie.split("jwt_auth=")[1]
    
    if jwt_token:
        public_key = frappe.db.get_single_value('JWT', 'public_key')
        algorythmus = frappe.db.get_single_value('JWT', 'algorythmus')
        decoded_jwt_token = jwt.decode(jwt_token, public_key, algorithms=[algorythmus])
        context.jwt_token = decoded_jwt_token
        if 'mitglied_nr' in decoded_jwt_token:
            mitglied_id = get_mitglied_id_from_nr(decoded_jwt_token["mitglied_nr"])
            if mitglied_id:
                if frappe.db.exists("Mitgliedschaft", mitglied_id):
                    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitglied_id)
                    context = context_erweiterung(context, mitgliedschaft)
                else:
                    # Mitglied-ID in ERPNext unbekannt
                    frappe.log_error("{0}\n\n{1}".format(str(mitglied_id), str(authorization_header)), 'E-Mail Beratung (500)')
                    raise_redirect(typ='500')
            else:
                # Mitglied-ID in ERPNext unbekannt
                frappe.log_error("{0}\n\n{1}".format(str(decoded_jwt_token["mitglied_nr"]), str(authorization_header)), 'E-Mail Beratung (500)')
                raise_redirect(typ='500')
        else:
            # ungültiger JWT Token
            frappe.log_error("{0}".format(str(authorization_header)), 'E-Mail Beratung (ungültiger JWT Token)')
            raise_redirect()
    else:
        # KEIN JWT Token
        frappe.log_error("{0}".format(str(authorization_header)), 'E-Mail Beratung (KEIN JWT Token)')
        raise_redirect()

def raise_redirect(typ=None):
    if not typ:
        frappe.local.flags.redirect_location = "/nologin"
        raise frappe.Redirect
    else:
        if typ == '500':
            frappe.local.flags.redirect_location = "/mvd-500"
            raise frappe.Redirect

def context_erweiterung(context, mitgliedschaft):
    context.mitglied_nr = mitgliedschaft.mitglied_nr
    context.mitglied_id = mitgliedschaft.name
    context.anrede = mitgliedschaft.anrede_c
    context.vorname = mitgliedschaft.vorname_1
    context.nachname = mitgliedschaft.nachname_1
    context.telefon = mitgliedschaft.tel_m_1 if mitgliedschaft.tel_m_1 else mitgliedschaft.tel_p_1 if mitgliedschaft.tel_p_1 else mitgliedschaft.tel_g_1 if mitgliedschaft.tel_g_1 else ''
    context.email = mitgliedschaft.e_mail_1 if mitgliedschaft.e_mail_1 else ''
    
    if mitgliedschaft.abweichende_objektadresse:
        context.strasse = mitgliedschaft.objekt_strasse
        context.nummer = mitgliedschaft.objekt_hausnummer
        context.nummer_zu = mitgliedschaft.objekt_nummer_zu
        context.plz = mitgliedschaft.objekt_plz
        context.ort = mitgliedschaft.objekt_ort
    else:
        context.strasse = mitgliedschaft.strasse
        context.nummer = mitgliedschaft.nummer
        context.nummer_zu = mitgliedschaft.nummer_zu
        context.plz = mitgliedschaft.plz
        context.ort = mitgliedschaft.ort
    
    return context

@frappe.whitelist(allow_guest=True)
def new_beratung(**kwargs):
    args = json.loads(kwargs['kwargs'])
    if frappe.db.exists("Mitgliedschaft", args['mv_mitgliedschaft']):
        if args['telefon']:
            telefon = """<b>Telefon:</b> {0}<br>""".format(args['telefon'])
        else:
            telefon = ''
        if args['email']:
            email = """<b>E-Mail:</b> {0}<br>""".format(args['email'])
        else:
            email = ''
        if args['anderes_mietobjekt']:
            anderes_mietobjekt = """<b>Anderes Mietobjekt:</b><br>{0}<br><br>""".format(args['anderes_mietobjekt'].replace("\n", "<br>"))
        else:
            anderes_mietobjekt = ''
        if args['frage']:
            frage = """<b>Frage:</b><br>{0}<br><br>""".format(args['frage'].replace("\n", "<br>"))
        else:
            frage = ''
        if args['datum_mietzinsanzeige']:
            datum_mietzinsanzeige = """<b>Briefdatum der Mietzinserhöhungsanzeige:</b> {0}""".format(args['datum_mietzinsanzeige'])
        else:
            datum_mietzinsanzeige = ''
        
        notiz = """{0}{1}{2}{3}{4}""".format(telefon, email, anderes_mietobjekt, frage, datum_mietzinsanzeige)
        
        new_ber = frappe.get_doc({
            'doctype': 'Beratung',
            'status': 'Eingang',
            'mv_mitgliedschaft': args['mv_mitgliedschaft'],
            'notiz': notiz,
            'raised_by': args['email'] if args['email'] else None
        })
        new_ber.insert(ignore_permissions=True)
        frappe.db.commit()
        if args['email']:
            send_confirmation_mail(args['mv_mitgliedschaft'], new_ber.name, raised_by=args['email'])
        send_confirmation_mail(args['mv_mitgliedschaft'], new_ber.name, legacy_mail=True)
        return new_ber.name
    else:
        return 'error'

@frappe.whitelist(allow_guest=True)
def new_file_to_beratung(**kwargs):
    args = json.loads(kwargs['kwargs'])
    if frappe.db.exists("Beratung", args['beratung']):
        file_path = '/private/files/{0}'.format(args['filename'])
        new_file = frappe.get_doc({
            'doctype': 'Beratungsdateien',
            'parentfield': 'dokumente',
            'parenttype': 'Beratung',
            'parent': args['beratung'],
            'idx': args['idx'],
            'document_type': args['document_type'] if 'document_type' in args else 'Sonstiges',
            'filename': args['filename'].replace(".pdf", "").replace(".jpg", "").replace(".jpeg", ""),
            'document_date': args['document_date'] if 'document_date' in args else None,
            'file': file_path
        })
        new_file.insert(ignore_permissions=True)
        frappe.db.commit()

@frappe.whitelist(allow_guest=True)
def get_upload_keys():
    return {
        'key': frappe.db.get_value("MVD Settings", "MVD Settings", "upload_key"),
        'secret': frappe.db.get_value("MVD Settings", "MVD Settings", "upload_secret")
    }

def send_confirmation_mail(mitgliedschaft, beratung, raised_by=None, legacy_mail=False):
    if not legacy_mail:
        message = """Guten Tag"""
        if frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "vorname_1"):
            message += " {0}".format(frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "vorname_1"))
        if frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "nachname_1"):
            message += " {0}".format(frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "nachname_1"))
        message += """<br><br>Die untenstehende Frage ist bei uns eingetroffen.
                    <br><br>Mitgliedernummer: {0}<br>{1}""".format(frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "mitglied_nr"), notiz)
        message += """Freundliche Grüsse<br>
                    Ihr Mieterinnen- und Mieterverband"""
        
        make(doctype='Beratung', 
            name=beratung, 
            content=message, 
            subject='Vielen Dank für Ihre Anfrage', 
            sender='mv-test@libracore.io', 
            send_email=True, 
            recipients=[raised_by])
    else:
        # hier folgt das legacy Mail....
        return
    return
