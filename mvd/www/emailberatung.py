from __future__ import unicode_literals
import frappe
import json
import jwt
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr
from mvd.mvd.doctype.mitgliedschaft.utils import prepare_mvm_for_sp
from frappe.core.doctype.communication.email import make
from frappe.desk.form.load import get_attachments
from frappe.utils import get_url, sanitize_html
from frappe import sendmail
from mvd.mvd.service_plattform.api import send_beratung
from frappe.utils.data import get_datetime_str
import random

no_cache = 1

def get_context(context):
    if check_durchlass():
        authorization_header = frappe.get_request_header("Cookie", None)
        jwt_token = None
        testing = check_for_testing()

        if testing:
            mitglied_id = testing
            if mitglied_id:
                if frappe.db.exists("Mitgliedschaft", mitglied_id):
                    mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitglied_id)
                    if mitgliedschaft.sektion_id == 'MVSO':
                        # MVSO führt keine E-Mail Beratung durch
                        create_beratungs_log(error=0, info=1, beratung=None, method='get_context', title='Keine MVSO E-Mail Beratung', json="{0}\n\n{1}".format(str(mitglied_id), str(authorization_header)))
                        raise_redirect(typ='MVSO')
                    else:
                        context = context_erweiterung(context, mitgliedschaft)
                        return context
                else:
                    # Mitglied-ID in ERPNext unbekannt
                    create_beratungs_log(error=0, info=1, beratung=None, method='get_context', title='E-Mail Beratung (500)', json="{0}\n\n{1}".format(str(mitglied_id), str(authorization_header)))
                    raise_redirect(typ='500')
            else:
                # Mitglied-ID in ERPNext unbekannt
                create_beratungs_log(error=0, info=1, beratung=None, method='get_context', title='E-Mail Beratung (500)', json="{0}\n\n{1}".format(str(decoded_jwt_token["mitglied_nr"]), str(authorization_header)))
                raise_redirect(typ='500')

        if authorization_header:
            for cookie in authorization_header.split(";"):
                if cookie.startswith(" jwt_auth="):
                    jwt_token = cookie.split(" jwt_auth=")[1]
                elif cookie.startswith("jwt_auth="):
                    jwt_token = cookie.split("jwt_auth=")[1]
        else:
            create_beratungs_log(error=0, info=1, beratung=None, method='get_context', title='Aufruf ohne Cookies', json=None)
            raise_redirect()

        if jwt_token:
            try:
                public_key = frappe.db.get_single_value('JWT', 'public_key')
                algorythmus = frappe.db.get_single_value('JWT', 'algorythmus')
                decoded_jwt_token = jwt.decode(jwt_token, public_key, algorithms=[algorythmus])
                context.jwt_token = decoded_jwt_token
            except Exception as err:
                create_beratungs_log(error=1, info=0, beratung=None, method='get_context', title='Exception in JWT decode', json="{0}".format(str(err)))
                raise_redirect()
            
            if 'mitglied_nr' in decoded_jwt_token:
                mitglied_id = get_mitglied_id_from_nr(decoded_jwt_token["mitglied_nr"])
                if mitglied_id:
                    if frappe.db.exists("Mitgliedschaft", mitglied_id):
                        mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitglied_id)
                        if mitgliedschaft.sektion_id == 'MVSO':
                            # MVSO führt keine E-Mail Beratung durch
                            create_beratungs_log(error=0, info=1, beratung=None, method='get_context', title='Keine MVSO E-Mail Beratung', json="{0}\n\n{1}".format(str(mitglied_id), str(authorization_header)))
                            raise_redirect(typ='MVSO')
                        else:
                            context = context_erweiterung(context, mitgliedschaft)
                            return context
                    else:
                        # Mitglied-ID in ERPNext unbekannt
                        create_beratungs_log(error=0, info=1, beratung=None, method='get_context', title='E-Mail Beratung (500)', json="{0}\n\n{1}".format(str(mitglied_id), str(authorization_header)))
                        raise_redirect(typ='500')
                else:
                    # Mitglied-ID in ERPNext unbekannt
                    create_beratungs_log(error=0, info=1, beratung=None, method='get_context', title='E-Mail Beratung (500)', json="{0}\n\n{1}".format(str(decoded_jwt_token["mitglied_nr"]), str(authorization_header)))
                    raise_redirect(typ='500')
            else:
                # ungültiger JWT Token
                create_beratungs_log(error=0, info=1, beratung=None, method='get_context', title='ungültiger JWT Token', json="{0}".format(str(authorization_header)))
                raise_redirect()
        else:
            # KEIN JWT Token
            create_beratungs_log(error=0, info=1, beratung=None, method='get_context', title='KEIN JWT Token', json="{0}".format(str(authorization_header)))
            raise_redirect()
    else:
        # Durchlassquote überschritten
        create_beratungs_log(error=0, info=1, beratung=None, method='get_context', title='Durchlassquote überschritten', json=None)
        raise_redirect(typ='durchlassquote')

def raise_redirect(typ=None):
    if not typ:
        frappe.local.flags.redirect_location = "/nologin"
        raise frappe.Redirect
    else:
        if typ == '500':
            frappe.local.flags.redirect_location = "/mvd-500"
            raise frappe.Redirect
        if typ == 'MVSO':
            frappe.local.flags.redirect_location = "/mvd-mvso"
            raise frappe.Redirect
        if typ == 'durchlassquote':
            frappe.local.flags.redirect_location = frappe.db.get_value("MVD Settings", "MVD Settings", 'redirect_url_ablehnung') or '/503'
            raise frappe.Redirect

def context_erweiterung(context, mitgliedschaft):
    try:
        context.mitglied_nr = mitgliedschaft.mitglied_nr
        context.mitglied_id = mitgliedschaft.name
        context.anrede = mitgliedschaft.anrede_c
        context.vorname = mitgliedschaft.vorname_1
        context.nachname = mitgliedschaft.nachname_1
        context.telefon = mitgliedschaft.tel_m_1 if mitgliedschaft.tel_m_1 else mitgliedschaft.tel_p_1 if mitgliedschaft.tel_p_1 else mitgliedschaft.tel_g_1 if mitgliedschaft.tel_g_1 else ''
        context.email = mitgliedschaft.e_mail_1 if mitgliedschaft.e_mail_1 else ''
        context.sektion = mitgliedschaft.sektion_id
        context.mitgliedtyp_c = mitgliedschaft.mitgliedtyp_c
        context.firma = mitgliedschaft.firma
        context.mvb_typ = mitgliedschaft.mvb_typ
        
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
        
        # legacy mode check
        if frappe.db.get_value("Sektion", mitgliedschaft.sektion_id, 'legacy_mode') == '2':
            context.legacy_mode = True
        else:
            context.legacy_mode = False
        
        # Sektionsangaben
        context.sektionsname = frappe.db.get_value("Sektion", mitgliedschaft.sektion_id, 'company') or 'MV'
        
        # Hinweis Mietzinsrechnererhoehung
        context.hinweis_mietzinsrechner_erhoehung = frappe.db.get_value("Sektion", mitgliedschaft.sektion_id, 'hinweis_mietzinsrechner_erhoehung') or ''
        
        # Hinweis Mietzinsrechner_senkung
        context.hinweis_mietzinsrechner_senkung = frappe.db.get_value("Sektion", mitgliedschaft.sektion_id, 'hinweis_mietzinsrechner_senkung') or ''
        # print("Debug: hinweis_mietzinsrechner_senkung =", context.hinweis_mietzinsrechner_senkung)  # Add debug print
        
        return context
    except Exception as err:
        # allgemeiner Fehler
        create_beratungs_log(error=1, info=0, beratung=None, method='context_erweiterung', title='Exception', json="{0}".format(str(err)))
        raise_redirect(typ='500')

@frappe.whitelist(allow_guest=True)
def new_beratung(**kwargs):
    try:
        args = json.loads(kwargs['kwargs'])
        # print("====================================================================","Debug: args =", args,"====================================================================")  # Add debug print
        create_beratungs_log(error=0, info=1, beratung=None, method='new_beratung', title='Neue Beratung wird angelegt', json="{0}".format(str(args)))
        if frappe.db.exists("Mitgliedschaft", args['mv_mitgliedschaft']):
            sektion = frappe.db.get_value("Mitgliedschaft", args['mv_mitgliedschaft'], "sektion_id")
            thema = None
            beratungskategorie = None
            termin_vereinbaren = False
            if args['thema'] != 'anderes':
                if args['thema'] == 'Mietzinserhöhung' or args['thema'] == 'mz_erhoehung':
                    beratungskategorie = '202 - Mietzinserhöhung'
                if args['thema'] == 'Mietzinssenkung' or args['thema'] == 'mz_senkung':
                    beratungskategorie = '203 - Mietzinssenkung'
                elif args['thema'] == 'Heiz- und Nebenkosten':
                    beratungskategorie = '300 - Nebenkosten'

            if args['termin_vereinbaren']:
                termin_vereinbaren = True
            
            if args['telefon']:
                telefon = """<b>Telefon:</b> {0}<br>""".format(args['telefon'])
            else:
                telefon = ''
            if args['email']:
                email = """<b>E-Mail:</b> <a href="mailto:{0}">{0}</a><br>""".format(args['email'])
            else:
                email = ''
            if args['anderes_mietobjekt']:
                anderes_mietobjekt = """<b>Anderes Mietobjekt:</b><br>{0}<br><br>""".format(sanitize_html(args['anderes_mietobjekt']).replace("\n", "<br>"))
            else:
                anderes_mietobjekt = ''
            if args['frage']:
                frage = """<b>Frage:</b><br>{0}<br><br>""".format(sanitize_html(args['frage']).replace("\n", "<br>"))
            else:
                frage = ''
            if 'datum_mietzinsanzeige' in args and args['datum_mietzinsanzeige']:
                datum_mietzinsanzeige = """<b>Briefdatum der Mietzinserhöhungsanzeige:</b> {0}""".format(args['datum_mietzinsanzeige'])
            else:
                datum_mietzinsanzeige = ''
            
            notiz = """{0}{1}{2}{3}{4}""".format(telefon, email, anderes_mietobjekt, frage, datum_mietzinsanzeige)
            
            new_ber = frappe.get_doc({
                'doctype': 'Beratung',
                'status': 'Rückfrage: Termin vereinbaren' if termin_vereinbaren else 'Eingang',
                'subject': thema,
                'beratungskategorie': beratungskategorie,
                'mv_mitgliedschaft': args['mv_mitgliedschaft'],
                'notiz': notiz,
                'raised_by': args['email'] if args['email'] else None,
                'telefon_privat_mobil': args['telefon'] if args['telefon'] else None,
                'anderes_mietobjekt': args['anderes_mietobjekt'] if args['anderes_mietobjekt'] else None,
                'frage': args['frage'] if args['frage'] else None,
                'datum_mietzinsanzeige': args.get('datum_mietzinsanzeige', None),
                'anlage_durch_web_formular': 1,
                'sektion_id': sektion
            })
            new_ber.insert(ignore_permissions=True)
            frappe.db.commit()
            
            # MVBE Spezial-Hack
            if new_ber.create_be_admin_todo == 1:
                frappe.get_doc({
                    'doctype': 'ToDo',
                    'description': 'Vorprüfung {0}<br>Zuweisung für Beratung {0}'.format(new_ber.beratungskategorie, new_ber.name),
                    'reference_type': 'Beratung',
                    'reference_name': new_ber.name,
                    'assigned_by': 'Administrator',
                    'owner': 'libracore@be.mieterverband.ch'
                }).insert(ignore_permissions=True)
            
            if args['email']:
                send_confirmation_mail(args['mv_mitgliedschaft'], new_ber.name, notiz, raised_by=args['email'], sektion=sektion)
            
            return new_ber.name
        else:
            return 'error'
    except Exception as err:
        # allgemeiner Fehler
        create_beratungs_log(error=1, info=0, beratung=None, method='new_beratung', title='Exception', json="{0}".format(str(err)))
        raise_redirect(typ='500')

@frappe.whitelist(allow_guest=True)
def new_file_to_beratung(**kwargs):
    try:
        args = json.loads(kwargs['kwargs'])
        if frappe.db.exists("Beratung", args['beratung']):
            document_type = 'Sonstiges'
            man_document_type = None
            if args['document_type']:
                if args['document_type'] in [
                            'Mietvertrag',
                            'Mietzinserhöhung',
                            'Mietzinsherabsetzung',
                            'Vergleich/Urteil',
                            'Vereinbarung',
                            'sonstige Vertragsänderung'
                        ]:
                    document_type = args['document_type']
                else:
                    man_document_type = args['document_type']
            try:
                file_path = '/private/files/{0}'.format(args['filename'])
                existing_row = frappe.db.sql("""SELECT `name` FROM `tabBeratungsdateien` WHERE `parent` = '{0}' AND `file` = '{1}'""".format(args['beratung'], file_path), as_dict=True)
                if len(existing_row) > 0:
                    row_to_delete = frappe.get_doc("Beratungsdateien", existing_row[0].name)
                    row_to_delete.delete()
                
                new_file = frappe.get_doc({
                    'doctype': 'Beratungsdateien',
                    'parentfield': 'dokumente',
                    'parenttype': 'Beratung',
                    'parent': args['beratung'],
                    'idx': args['idx'],
                    'document_type': document_type,
                    'man_document_type': man_document_type,
                    'filename': args['filename'].replace(".pdf", "").replace(".jpg", "").replace(".jpeg", ""),
                    'document_date': args['document_date'] if args['document_date'] else None,
                    'file': file_path
                })
                new_file.insert(ignore_permissions=True)
                frappe.db.commit()
            except Exception as e:
                create_beratungs_log(error=1, info=0, beratung=args['beratung'], method='new_file_to_beratung', title='File Upload fehlerhaft', json="{0}".format(str(e)))
        else:
            create_beratungs_log(error=0, info=1, beratung=args['beratung'], method='new_file_to_beratung', title='File Upload unvollständig', json="{0}".format(args['beratung']))
    except Exception as err:
        # allgemeiner Fehler
        create_beratungs_log(error=1, info=0, beratung=None, method='new_file_to_beratung', title='Exception', json="{0}".format(str(err)))
        raise_redirect(typ='500')

@frappe.whitelist(allow_guest=True)
def get_upload_keys():
    try:
        return {
            'key': frappe.db.get_value("MVD Settings", "MVD Settings", "upload_key"),
            'secret': frappe.db.get_value("MVD Settings", "MVD Settings", "upload_secret")
        }
    except Exception as err:
        # allgemeiner Fehler
        create_beratungs_log(error=1, info=0, beratung=None, method='get_upload_keys', title='Exception', json="{0}".format(str(err)))
        raise_redirect(typ='500')

def send_confirmation_mail(mitgliedschaft, beratung, notiz, raised_by=None, legacy_mail=False, sektion=None):
    try:
        mitglied_nr = frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "mitglied_nr")
        link_zur_mitgliedschaft = '<a href="https://libracore.mieterverband.ch/desk#Form/Mitgliedschaft/{0}">{1}</a>'.format(mitgliedschaft, mitglied_nr)
        link_zur_beratung = '<a href="https://libracore.mieterverband.ch/desk#Form/Beratung/{0}">{0}</a>'.format(beratung)
        beratung_email = "mv+Beratung+{0}@libracore.io".format(beratung)

        if not legacy_mail:
            message = """Guten Tag"""
            if frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "vorname_1"):
                message += " {0}".format(frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "vorname_1"))
            if frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "nachname_1"):
                message += " {0}".format(frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "nachname_1"))
            
            if frappe.get_value("Sektion", sektion, "emailberatung_email_text"):
                einleitung = frappe.get_value("Sektion", sektion, "emailberatung_email_text")
            else:
                einleitung = """Die untenstehende Frage ist bei uns eingetroffen."""

            message += """<br><br>{0}<br><br><b>Mitgliedernummer:</b> {1}<br>{2}""".format(einleitung, mitglied_nr, notiz)
            message += """<br><br>Freundliche Grüsse<br>
                        Ihr Mieterinnen- und Mieterverband"""
            
            comm = make(
                recipients=[raised_by],
                sender=frappe.get_value("Sektion", sektion, "legacy_mail_absender_mail"),
                subject='Vielen Dank für Ihre Anfrage', 
                content=message,
                doctype='Beratung',
                name=beratung,
                send_email=False,
                sender_full_name=frappe.get_value("Sektion", sektion, "legacy_mail_absende_name")
            )["name"]
            
            sendmail(
                recipients=[raised_by],
                sender="{0} <{1}>".format(frappe.get_value("Sektion", sektion, "legacy_mail_absende_name"), frappe.get_value("Sektion", sektion, "legacy_mail_absender_mail")),
                subject='Vielen Dank für Ihre Anfrage', 
                message=message,
                as_markdown=False,
                delayed=True,
                reference_doctype='Beratung',
                reference_name=beratung,
                unsubscribe_method=None,
                unsubscribe_params=None,
                unsubscribe_message=None,
                attachments=[],
                content=None,
                doctype='Beratung',
                name=beratung,
                reply_to=frappe.get_value("Sektion", sektion, "legacy_mail_absender_mail"),
                cc=[],
                bcc=[],
                message_id=frappe.get_value("Communication", comm, "message_id"),
                in_reply_to=None,
                send_after=None,
                expose_recipients=None,
                send_priority=1,
                communication=comm,
                retry=1,
                now=None,
                read_receipt=None,
                is_notification=False,
                inline_images=None,
                header=None,
                print_letterhead=False
            )
        else:
            try:
                message = False
                attachments = None
                vorname = frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "vorname_1")
                nachname = frappe.db.get_value("Mitgliedschaft", mitgliedschaft, "nachname_1")
                if legacy_mail == '1':
                    # legacy mail mit links
                    message = """Guten Tag {0}""".format(sektion)
                    message += """<br><br>Die untenstehende Frage ist bei uns eingetroffen.
                            <br><br><b>Mitglied:</b> {0} {1}
                            <br><b>Mitgliedernummer:</b> {2}
                            <br><b>Beratung:</b> {3}
                            <br><b>Beratung Mail-Link:</b> <a href="mailto:{4}">{4}</a>
                            <br>{5}
                            <br><br>Anhänge:<br>""".format(vorname, nachname, link_zur_mitgliedschaft, link_zur_beratung, beratung_email, notiz)
                    for file_data in frappe.get_doc("Beratung", beratung).dokumente:
                        message += """<a href="{0}">{1}</a><br>""".format(get_url(file_data.file), file_data.filename)
                
                elif legacy_mail == '2':
                    # legacy mail mit anhängen
                    message = """Guten Tag {0}""".format(sektion)
                    message += """<br><br>Die untenstehende Frage ist bei uns eingetroffen.
                            <br><br><b>Mitglied:</b> {0} {1}
                            <br><b>Mitgliedernummer:</b> {2}
                            <br><b>Beratung:</b> {3}
                            <br><b>Beratung Mail-Link:</b> <a href="mailto:{4}">{4}</a>
                            <br>{5}""".format(vorname, nachname, link_zur_mitgliedschaft, link_zur_beratung, beratung_email, notiz)
                    
                    attachments = []
                    all_attachments = frappe.db.sql("""SELECT `name` FROM `tabFile` WHERE `attached_to_doctype` = 'Beratung' AND `attached_to_name` = '{0}'""".format(beratung), as_dict=True)
                    for f in all_attachments:
                        attachments.append({'fid': f.name})
                
                if message:
                    recipient = frappe.db.get_value("Sektion", sektion, 'legacy_email')
                    
                    comm = make(
                        recipients=[recipient],
                        sender=frappe.get_value("Sektion", sektion, "legacy_mail_absender_mail"),
                        subject='Neue E-Mail Beratung', 
                        content=message,
                        doctype='Beratung',
                        name=beratung,
                        send_email=False,
                        sender_full_name=frappe.get_value("Sektion", sektion, "legacy_mail_absende_name"),
                        attachments=attachments
                    )["name"]
                    
                    sendmail(
                        recipients=[recipient],
                        sender="{0} <{1}>".format(frappe.get_value("Sektion", sektion, "legacy_mail_absende_name"), frappe.get_value("Sektion", sektion, "legacy_mail_absender_mail")),
                        subject='Neue E-Mail Beratung', 
                        message=message,
                        as_markdown=False,
                        delayed=True,
                        reference_doctype='Beratung',
                        reference_name=beratung,
                        unsubscribe_method=None,
                        unsubscribe_params=None,
                        unsubscribe_message=None,
                        attachments=attachments,
                        content=None,
                        doctype='Beratung',
                        name=beratung,
                        reply_to=raised_by,
                        cc=[],
                        bcc=[],
                        message_id=frappe.get_value("Communication", comm, "message_id"),
                        in_reply_to=None,
                        send_after=None,
                        expose_recipients=None,
                        send_priority=1,
                        communication=comm,
                        retry=1,
                        now=None,
                        read_receipt=None,
                        is_notification=False,
                        inline_images=None,
                        header=None,
                        print_letterhead=False
                    )
            except Exception as e:
                create_beratungs_log(error=1, info=0, beratung=beratung, method='send_confirmation_mail', title='Legacy Mail failed', json="{0}".format(str(e)))
                raise_redirect(typ='500')
            
        return
    except Exception as err:
        # allgemeiner Fehler
        create_beratungs_log(error=1, info=0, beratung=beratung, method='send_confirmation_mail', title='Exception', json="{0}".format(str(err)))
        raise_redirect(typ='500')

@frappe.whitelist(allow_guest=True)
def check_legacy_mode(**kwargs):
    try:
        args = json.loads(kwargs['kwargs'])
        mitgliedschaft_id = args['mv_mitgliedschaft']
        sektion = frappe.db.get_value("Mitgliedschaft", mitgliedschaft_id, 'sektion_id')
        if frappe.db.get_value("Sektion", sektion, 'legacy_mode') == '2':
            return True
        else:
            return False
    except Exception as err:
        # allgemeiner Fehler
        create_beratungs_log(error=1, info=0, beratung=None, method='check_legacy_mode', title='Exception', json="{0}".format(str(err)))
        raise_redirect(typ='500')

@frappe.whitelist(allow_guest=True)
def send_legacy_mail(**kwargs):
    try:
        # legacy mail
        args = json.loads(kwargs['kwargs'])
        beratung = args['beratung']
        raised_by = args['raised_by']
        
        # mark for SP API
        frappe.db.set_value("Beratung", beratung, 'trigger_api', 1, update_modified=False)
        
        mitgliedschaft_id = frappe.db.get_value("Beratung", beratung, 'mv_mitgliedschaft')
        sektion = frappe.db.get_value("Mitgliedschaft", mitgliedschaft_id, 'sektion_id')
        notiz = frappe.db.get_value("Beratung", beratung, 'notiz')
        
        create_beratungs_log(error=0, info=1, beratung=beratung, method='send_legacy_mail', title='Trigger Legacy Mail', json="{0},\n{1},\n{2},\n{3},\n{4}".format(beratung, raised_by, mitgliedschaft_id, sektion, notiz))
        
        if frappe.db.get_value("Sektion", sektion, 'legacy_mode') != '0':
            send_confirmation_mail(mitgliedschaft_id, beratung, notiz, legacy_mail=frappe.db.get_value("Sektion", sektion, 'legacy_mode'), sektion=sektion, raised_by=raised_by)
            return
    except Exception as err:
        # allgemeiner Fehler
        create_beratungs_log(error=1, info=0, beratung=None, method='send_legacy_mail', title='Exception', json="{0}".format(str(err)))
        raise_redirect(typ='500')

def send_to_sp():
    if not int(frappe.db.get_single_value('Service Plattform API', 'send_beratung_to_sp_unterbrechen')) == 1:
        try:
            beratungen = frappe.db.sql("""SELECT `name` FROM `tabBeratung` WHERE `trigger_api` = 1""", as_dict=True)
            for ber in beratungen:
                beratung = frappe.get_doc("Beratung", ber.name)
                if beratung.sektion_id == 'MVZH':
                    mitgliedschaft = frappe.get_doc("Mitgliedschaft", beratung.mv_mitgliedschaft)
                    prepared_mvm = prepare_mvm_for_sp(mitgliedschaft)
                    dokumente = []
                    files = frappe.db.sql("""SELECT `name`, `file_name` FROM `tabFile` WHERE `attached_to_name` = '{0}'""".format(beratung.name), as_dict=True)
                    for dok in files:
                        dok_data = {
                            "beratungDokumentId": dok.name,
                            "name": dok.file_name,
                            "datum": get_datetime_str(beratung.start_date).replace(" ", "T"),
                            "typ": str(dok.file_name.split(".")[len(dok.file_name.split(".")) - 1])
                        }
                        dokumente.append(dok_data)
                        
                    json_to_send = {
                        "beratungId": beratung.name,
                        "mitglied": prepared_mvm,
                        "datumEingang": get_datetime_str(beratung.start_date).replace(" ", "T"),
                        "beratungskategorie": 'Mietzinserhöhung' if beratung.beratungskategorie == '202 - Mietzinserhöhung' else 'Mietzinssenkung' if beratung.beratungskategorie == '203 - Mietzinssenkung' else 'Allgemeine Anfrage',
                        "telefonPrivatMobil": beratung.telefon_privat_mobil,
                        "email": beratung.raised_by,
                        "anderesMietobjekt": beratung.anderes_mietobjekt,
                        "frage": beratung.frage,
                        "datumBeginnFrist": get_datetime_str(beratung.datum_mietzinsanzeige).replace(" ", "T") if beratung.datum_mietzinsanzeige else get_datetime_str(beratung.start_date).replace(" ", "T"),
                        "dokumente": dokumente
                    }
                    
                    create_beratungs_log(error=0, info=1, beratung=beratung.name, method='send_to_sp', title='Beratung an SP gesendet', json="{0}".format(str(json_to_send)))
                    send_beratung(json_to_send, beratung.name)
                
                # remove mark for SP API
                frappe.db.set_value("Beratung", beratung.name, 'trigger_api', 0, update_modified=False)
        except Exception as err:
            # allgemeiner Fehler
            create_beratungs_log(error=1, info=0, beratung=None, method='send_to_sp', title='Exception', json="{0}".format(str(err)))

def create_beratungs_log(error=0, info=0, beratung=None, method=None, title=None, json=None):
    frappe.get_doc({
        'doctype': 'Beratungs Log',
        'error': error,
        'info': info,
        'beratung': beratung,
        'method': method,
        'title': title,
        'json': json
    }).insert(ignore_permissions=True)
    frappe.db.commit()

def check_durchlass():
    durchlassquote = int(frappe.db.get_value("MVD Settings", "MVD Settings", 'durchlassquote'))
    if durchlassquote >= 100:
        return True
    ticket = random.randint(1, 100)
    if ticket <= durchlassquote:
        return True
    else:
        return False

def check_for_testing():
    from frappe.utils import cint
    # check if testing is enabled
    if cint(frappe.db.get_value("Service Plattform API", "Service Plattform API", "emailberatung_test")) == 1:
        from urllib.parse import urlparse
        from urllib.parse import parse_qs
        try:
            url = frappe.request.url
            parsed_url = urlparse(url)
            test_token = parse_qs(parsed_url.query)['test'][0]
            if test_token == frappe.db.get_value("Service Plattform API", "Service Plattform API", "emailberatung_testtoken"):
                mitglied_id = parse_qs(parsed_url.query)['mitglied_id'][0]
                return mitglied_id
            else:
                # invalid token
                return False
        except:
            return False
    else:
        # testing is disabled
        return False
