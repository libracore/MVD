# -*- coding: utf-8 -*-
# Copyright (c) 2021-2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.service_plattform.request_worker import api_request_check, raise_200, raise_xxx
import json
import requests
from frappe.utils.background_jobs import enqueue
from datetime import datetime
import random
import string
from frappe import _
from mvd.mvd.utils.post import _post_retouren
from mvd.mvd.utils.post import _post_responses
from mvd.mvd.doctype.beratung.beratung import _get_beratungs_dokument
from mvd.mvd.doctype.webshop_order.webshop_order import create_order_from_api
from mvd.mvd.doctype.mitgliedschaft.utils import prepare_mvm_for_sp
from mvd.mvd.doctype.mitglied_main_naming.mitglied_main_naming import create_new_id, create_new_number

AUTH0_SCOPE = "Auth0"
SVCPF_SCOPE = "ServicePF"
POST_SCOPE = "PostNotiz"

# ---------------------------------------------------
# ---------------------------------------------------
# Test Methoden
# ---------------------------------------------------
# ---------------------------------------------------

@frappe.whitelist()
def whoami(type='light'):
    user = frappe.session.user
    if type == 'full':
        user = frappe.get_doc("User", user)
        return user
    else:
        return user

# ---------------------------------------------------
# ---------------------------------------------------

'''
Dieser Code ist mit SP4 obsolet da ERPNext die ID/Nr Vergabe selbständig durchführt.
'''
# def neue_mitglieder_nummer(sektion_code, sprache='Deutsch', typ='Privat', needsMitgliedNummer=True):
#     if not int(frappe.db.get_single_value('Service Plattform API', 'not_get_number_and_id')) == 1:
#         if auth_check(SVCPF_SCOPE):
#             config = frappe.get_doc("Service Plattform API", "Service Plattform API")
#             sub_url = config.get_value(SVCPF_SCOPE, "api_url")
#             endpoint = config.get('neue_mitglieder_nummer')
#             url = sub_url + endpoint
#             json = {
#                 "sektionCode": sektion_code,
#                 "sprache": sprache,
#                 "typ": typ,
#                 "needsMitgliedNummer": needsMitgliedNummer
#             }
#             token = config.get_value(SVCPF_SCOPE, 'api_token')
#             headers = {"authorization": "Bearer {token}".format(token=token)}
            
#             try:
#                 mitglied_nr_obj = requests.post(url, json = json, headers = headers)
#                 mitglied_nr_obj = mitglied_nr_obj.json()
#                 if 'mitgliedNummer' not in mitglied_nr_obj:
#                     frappe.log_error("{0}".format(mitglied_nr_obj), 'neue_mitglieder_nummer failed')
#                     frappe.throw("Zur Zeit können keine Daten von der Serviceplatform bezogen werden.")
                
#                 return mitglied_nr_obj
#             except Exception as err:
#                 frappe.log_error("{0}".format(err), 'neue_mitglieder_nummer failed')
#                 frappe.db.commit()
#     else:
#         frappe.log_error("SektionsCode: {0}".format(sektion_code), 'neue_mitglieder_nummer deaktiviert: manuelle vergabe')
#         return {
#             'mitgliedNummer': '00000000',
#             'mitgliedId': int("9{0}".format(frappe.db.count('Mitgliedschaft'))) + 1
#         }

'''
    Mit dieser Methode können Mitgliedschaften an die SP gesendet werden.
    Wenn es sich um Updates von bestehenden Mitgliedschaften handelt:
        update = True --> es wird ein PUT Request gesendet
    Wenn es sich um eine Neuanlage handelt:
        update = False (oder weglassen) --> es wird ein POST Request gesendet
'''
def update_mvm(mvm, update):
    if not int(frappe.db.get_single_value('Service Plattform API', 'no_sp_update')) == 1:
        if auth_check(SVCPF_SCOPE):
            config = frappe.get_doc("Service Plattform API", "Service Plattform API")
            sub_url = str(config.get_value(SVCPF_SCOPE, "api_url"))
            endpoint = str(config.get('mitglieder'))
            url = sub_url + endpoint
            token = config.get_value(SVCPF_SCOPE, 'api_token')
            headers = {"authorization": "Bearer {token}".format(token=token)}
            
            if int(frappe.db.get_single_value('Service Plattform API', 'json_error_log')) == 1:
                frappe.log_error("{0}".format(json.dumps(mvm)), 'json for ChLa')
            
            if update:
                sp_connection = requests.put(url, json = mvm, headers = headers)
            else:
                sp_connection = requests.post(url, json = mvm, headers = headers)
            
            try:
                if sp_connection.status_code != 204:
                    frappe.log_error("{0}\n\n{1}\n\n{2}".format(sp_connection.status_code, sp_connection.text, mvm), 'update_mvm failed')
                    frappe.db.commit()
                    return 0
                else:
                    return 1
            except Exception as err:
                frappe.log_error("{0}\n\n{1}".format(err, mvm), 'update_mvm failed')
                frappe.db.commit()
                return 0
    else:
        frappe.log_error("{0}".format(mvm), 'update_mvm deaktiviert')
        return 0

'''
    Mit dieser Methode können Beratungen an die SP gesendet werden.
'''
def send_beratung(beratungs_data, beratung):
    if auth_check(SVCPF_SCOPE):
        config = frappe.get_doc("Service Plattform API", "Service Plattform API")
        sub_url = str(config.get_value(SVCPF_SCOPE, "api_url"))
        endpoint = str(config.get('beratung'))
        url = sub_url + endpoint
        token = config.get_value(SVCPF_SCOPE, 'api_token')
        headers = {"authorization": "Bearer {token}".format(token=token)}
        
        if int(frappe.db.get_single_value('Service Plattform API', 'json_error_log')) == 1:
            frappe.log_error("{0}".format(json.dumps(beratungs_data)), 'json for ChLa')
        
        sp_connection = requests.post(url, json = beratungs_data, headers = headers)
        
        try:
            if sp_connection.status_code != 204:
                frappe.get_doc({
                    'doctype': 'Beratungs Log',
                    'error': 1,
                    'info': 0,
                    'beratung': beratung,
                    'method': 'send_beratung_failed',
                    'title': 'SP-übermittlung fehlgeschlagen',
                    'json': "{0}\n\n{1}\n\n{2}".format(sp_connection.status_code, sp_connection.text, beratungs_data)
                }).insert(ignore_permissions=True)

                frappe.log_error("{0}\n\n{1}\n\n{2}".format(sp_connection.status_code, sp_connection.text, beratungs_data), 'send beratung failed')
                frappe.db.commit()
                return
            else:
                frappe.get_doc({
                    'doctype': 'Beratungs Log',
                    'error': 0,
                    'info': 1,
                    'beratung': beratung,
                    'method': 'send_beratung',
                    'title': 'Beratung an SP übermittelt',
                    'json': "{0}".format(sp_connection.status_code)
                }).insert(ignore_permissions=True)
                frappe.db.commit()
                return
        except Exception as err:
            frappe.get_doc({
                    'doctype': 'Beratungs Log',
                    'error': 1,
                    'info': 0,
                    'beratung': beratung,
                    'method': 'send_beratung_failed',
                    'title': 'SP-übermittlung fehlgeschlagen',
                    'json': "{0}\n\n{1}".format(err, beratungs_data)
                }).insert(ignore_permissions=True)
            
            frappe.log_error("{0}\n\n{1}".format(err, beratungs_data), 'send beratung failed')
            frappe.db.commit()

def send_postnotiz_to_sp(postnotiz_for_sp):
    if not int(frappe.db.get_single_value('Service Plattform API', 'no_postnotiz_to_sp')) == 1:
        if auth_check(POST_SCOPE):
            config = frappe.get_doc("Service Plattform API", "Service Plattform API")
            sub_url = config.get_value(POST_SCOPE, "api_url")
            endpoint = str(config.get('retouren_mvz'))
            url = sub_url + endpoint
            token = config.get_value(POST_SCOPE, 'api_token')
            headers = {"authorization": "Bearer {token}".format(token=token)}
            
            try:
                requests.post(url, json = json.dumps(postnotiz_for_sp.__dict__), headers = headers)
                return
            except Exception as err:
                frappe.log_error("{0}".format(err), 'send_postnotiz_to_sp failed')
                frappe.db.commit()
    else:
        frappe.log_error("{0}".format(json.dumps(postnotiz_for_sp.__dict__)), 'send_postnotiz_to_sp deaktiviert')
        return

'''
    Damit Requests an die SP gesendet werden können, wird ein API Token benötigt, welcher i.d.R. nach 24h abläuft.
    Mit dieser Methode kann der aktuell hinterlegte API Token auf seine Gültigkeit geprüft werden.
'''
def auth_check(scope=SVCPF_SCOPE):
    config = frappe.get_doc("Service Plattform API", "Service Plattform API")
    sub_url = str(config.get_value(scope, "api_url"))
    endpoint = str(config.get('auth_check'))
    url = sub_url + endpoint
    token = config.get_value(scope, 'api_token')
    
    headers = {"authorization": "Bearer {token}".format(token=token)}
    response = requests.get(url, headers = headers)
    
    try:
        response = response.json()
        
        if response["status"] == 'Ok':
            return True
    except:
        frappe.log_error("{0}".format(response), 'auth_check failed, get new token')
        # get new token and try again
        get_token(scope)
        token = config.get_value(scope, 'api_token')
        headers = {"authorization": "Bearer {token}".format(token=token)}
        response = requests.get(url, headers = headers)
        
        try:
            response = response.json()
            if response["status"] == 'Ok':
                return True
        except:
            frappe.log_error("{0}".format(response), 'auth_check failed')
            frappe.db.commit()
            return False

'''
    Damit Requests an die SP gesendet werden können, wird ein API Token benötigt, welcher i.d.R. nach 24h abläuft.
    Mit dieser Methode kann der aktuell hinterlegte API Token auf sein Alter geprüft werden.
    Ist er älter als 24h, wird ein neuer API Token bezogen.
'''
def token_check(scope):
    config = frappe.get_doc("Service Plattform API", "Service Plattform API")
    token_date = config.get_value(scope, "token_date")
    if (datetime.now() - token_date).total_seconds() > 86400:
        # more than 86400 sec = 24 h ago
        get_token(scope)

'''
    Damit Requests an die SP gesendet werden können, wird ein API Token benötigt, welcher i.d.R. nach 24h abläuft.
    Mit dieser Methode kann ein neuer API Token bezogen und gespeichert werden.
'''
@frappe.whitelist()
def get_token(scope=SVCPF_SCOPE):
    config = frappe.get_doc("Service Plattform API", "Service Plattform API")
    url = config.get_value(scope, 'api_token_url')
    client_id = config.get_value(scope, 'client_id')
    client_secret = config.get_value(scope, 'api_secret')
    audience = config.get_value(scope, 'api_url')
    
    headers = {
        "content-type": "application/json"
    }
    data = {
        "client_id": "{0}".format(client_id), 
        "client_secret":"{0}".format(client_secret), 
        "audience":"{0}".format(audience), 
        "grant_type":"client_credentials"
    }
    
    response = requests.post(url, json = data, headers = headers)
    
    try:
        response = response.json()
        token = response["access_token"]
        config.set_value(scope, 'api_token', token)
        config.set_value(scope, 'token_date', datetime.now())
    except Exception as err:
        frappe.log_error("{0}\n\n{1}".format(err, response), 'get_token failed')
    return

# ---------------------------------------------------
# ---------------------------------------------------
# Eingehende Methoden (SP > ERPNext)
# ---------------------------------------------------
# ---------------------------------------------------

'''
    Die SP kann Objekte von Mitgliedschaften an diesen Endpunkt senden.
    Wenn das Mitglied in ERPNext existiert wird es aktualisiert.
    Wenn das Mitglied in ERPNext nicht existiert, wird es neu angelegt.
'''
@frappe.whitelist()
def mitglieder(**api_request):
    return api_request_check(api_request)

'''
    Die SP kann Objekte von Webshop Bestellungen an diesen Endpunkt senden.
    ERPNext legt daraus eine "Webshop Order" an.
'''
@frappe.whitelist()
def shop(**api_request):
    return create_order_from_api(api_request)

'''
    Die Mitglieder können über das Formular "E-Mail Beratung" Anhänge zu Beratungen hochladen.
    Mit diesem Endpunkt kann die SP die entsprechenden Anhänge downloaden.
'''
@frappe.whitelist()
def get_beratungs_dokument(**beratungs_dokument):
    return _get_beratungs_dokument(beratungs_dokument)

'''
    Sektionswechsel innerhalb durch ERPNext gepflegte Sektionen werden vollständig ohne die SP abgewickelt.
    Sektionswechsel von einer durch ERPNext gepflegten Sektion nach MVZH werden bei der SP durch diese Methode getriggert.
    Ablauf:
        1. Status Wegzug auf alten Mitgliedschaft (Sektion durch ERPNext verwaltet)
        2. Aufruf der nachfolgenden Methode
        3. Eingang einer Mitgliedschafts-Neuanlage (mit Sektion MVZH) bei ERPNext durch die SP
        4. Verarbeitung der Neuanlage durch ERPNext
'''
def sektionswechsel(mvm, sektion_code):
    if not int(frappe.db.get_single_value('Service Plattform API', 'no_sp_update')) == 1:
        if auth_check(SVCPF_SCOPE):
            config = frappe.get_doc("Service Plattform API", "Service Plattform API")
            sub_url = str(config.get_value(SVCPF_SCOPE, "api_url"))
            endpoint = '/mitglieder/sektionswechsel/{sektion_code}'.format(sektion_code=sektion_code)
            url = sub_url + endpoint
            token = config.get_value(SVCPF_SCOPE, 'api_token')
            headers = {"authorization": "Bearer {token}".format(token=token)}
            
            sp_connection = requests.post(url, json = mvm, headers = headers)
            
            try:
                if sp_connection.status_code != 204:
                    frappe.log_error("{0}\n\n{1}\n\n{2}".format(sp_connection.status_code, sp_connection.text, mvm), 'sektionswechsel failed')
                    frappe.db.commit()
                    return
                else:
                    return
            except Exception as err:
                frappe.log_error("{0}\n\n{1}".format(err, mvm), 'sektionswechsel failed')
                frappe.db.commit()
                return
    else:
        frappe.log_error("{0}".format(mvm), 'update_mvm deaktiviert')
        return

'''
    Mit diesem Endpunkt kann die SP Mitgliedschafts-Daten einer Mitgliedschaft bei ERPNext abfragen.
'''
@frappe.whitelist()
def get_mitglied_data(**api_request):
    '''
    ISS-2024-00058
    Dieser Endpunkt liefert Mitgliedschaftsdaten als JSON auf Basis einer Mitgliedernummer.
    Folgende Outputs sind nun möglich:
        - 200; Mitgliedschaft als JSON
        - 404 ('Not Found', 'No Activ Mitglied found'); Wenn Mitgliedschaft inaktiv oder nicht vorhanden
        - 400 ('Bad Request', 'MitgliedNummer missing'); Wenn der Parameter MitgliedNummer in der Anfrage fehlt
    Sollte es mehrere aktive Mitgliedschaften zu einer Mitgliednummer geben, werden jene zurückgegeben, welche als letztes in ERPNext angelegt wurden.
    '''
    from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr
    if 'MitgliedNummer' in api_request:
        if "MV" in api_request["MitgliedNummer"]:
            mitglied_nummer = get_mitglied_id_from_nr(api_request["MitgliedNummer"])
            if frappe.db.exists("Mitgliedschaft", mitglied_nummer):
                mitgliedschaft = frappe.get_doc("Mitgliedschaft", mitglied_nummer)
                data =  prepare_mvm_for_sp(mitgliedschaft)
                return data
            else:
                frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(404, 'Not Found', 'No Activ Mitglied found', frappe.utils.get_traceback(), str(api_request)), 'SP API Error!')
                frappe.local.response.http_status_code = 404
                frappe.local.response.message = 'No Activ Mitglied found'
        else:
            frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(400, 'Bad Request', 'MitgliedNummer missing MV', frappe.utils.get_traceback(), str(api_request)), 'SP API Error!')
            frappe.local.response.http_status_code = 400
            frappe.local.response.message = 'MitgliedNummer missing MV'
    else:
        frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(400, 'Bad Request', 'MitgliedNummer missing', frappe.utils.get_traceback(), str(api_request)), 'SP API Error!')
        frappe.local.response.http_status_code = 400
        frappe.local.response.message = 'MitgliedNummer missing'

'''
    Mit dieser Methode kann die SP die zu einer E-Mailadresse zugehörige Mitglieder-Nummer abfragen insofern vorhanden.
'''
@frappe.whitelist()
def get_mitglied_from_mail(**api_request):
    '''
    ISS-2024-00063
    Dieser Endpunkt gibt Mitgliednummern zurück, die zu aktiven Mitgliedschaften gehören.
    Folgende Outputs sind möglich:
        - 200; Mitgliednummer(n) als List/Array
        - 404 ('Not Found', 'No Activ Mitglied found'); Wenn keine aktive Mitgliedschaft vorhanden
        - 400 ('Bad Request', 'Emailadresse missing'); Wenn der Parameter Emailadresse in der Anfrage fehlt
    '''
    if 'Emailadresse' in api_request:
        mitgliedschaften = frappe.db.sql("""
                                        SELECT
                                            `mitglied_nr`
                                        FROM `tabMitgliedschaft`
                                        WHERE `e_mail_1` LIKE '%{0}%'
                                        AND `status_c` != 'Inaktiv'
                                        """.format(api_request['Emailadresse']), as_dict=True)
        if len(mitgliedschaften) >= 1:
            mitgl_list = []
            for mitgl in mitgliedschaften:
                mitgl_list.append(mitgl.mitglied_nr)
            return mitgl_list
        else:
            return raise_xxx(404, 'Not Found', 'No Activ Mitglied found', str(api_request))
    else:
        return raise_xxx(400, 'Bad Request', 'Emailadresse missing', str(api_request))

'''
Endpunkt für den Bezug einer neuen ID:
    - ohne Nummer
    - inkl. einer neuen Nummer
    - zu einer bestehenden Nummer
'''
@frappe.whitelist()
def naming_service_new_id(**api_request):
    '''ISS-2024-00064'''
    if 'new_nr' in api_request:
        new_nr = api_request['new_nr']
    else:
        new_nr = False
    
    if 'existing_nr' in api_request:
        existing_nr = api_request['existing_nr']
    else:
        existing_nr = False
    
    response = create_new_id(new_nr, existing_nr)
    if not 'error' in response:
        frappe.local.response.http_status_code = 200
        frappe.local.response.message = response
        return
    else:
        frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(response['code'], response['title'], response['msg'], frappe.utils.get_traceback(), str(api_request)), 'SP API Error!')
        frappe.local.response.http_status_code = response['code']
        frappe.local.response.message = response['msg']
        return

'''
    Endpunkt für den Bezug einer neuen Mitgliednummer zu einer existierenden ID
'''
@frappe.whitelist()
def naming_service_new_number(**api_request):
    '''ISS-2024-00064'''
    if 'id' in api_request:
        response = create_new_number(api_request['id'])
        if not 'error' in response:
            frappe.local.response.http_status_code = 200
            frappe.local.response.message = response
        else:
            frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(response['code'], response['title'], response['msg'], str(api_request), ''), 'SP API Error!')
            frappe.local.response.http_status_code = response['code']
            frappe.local.response.message = response['msg']
            return
    else:
        frappe.log_error("{0}\n{1}\n{2}\n\n{3}\n\n{4}".format(400, 'Bad Request', 'ID missing', str(api_request), ''), 'SP API Error!')
        frappe.local.response.http_status_code = 400
        frappe.local.response.message = 'ID missing'
        return

'''
    Endpunkt zum Abfragen ob bei einer Kündigung das nächste Jahr geschuldet ist
'''
@frappe.whitelist()
def naechstes_jahr_geschuldet(**api_request):
    '''ISS-2024-00080'''
    from mvd.mvd.doctype.mitgliedschaft.utils import get_naechstes_jahr_geschuldet
    if 'id' in api_request:
        njg = get_naechstes_jahr_geschuldet(api_request['id'])
        frappe.local.response.http_status_code = 200
        frappe.local.response.message = {"naechstesJahrGeschuldet": njg}
        return
    else:
        return raise_xxx(400, 'Bad Request', 'ID missing', str(api_request))

# ---------------------------------------------------
# ---------------------------------------------------
# User and Role Deployment
# ---------------------------------------------------
# ---------------------------------------------------

@frappe.whitelist()
def create_user(email, first_name, last_name, debug=False):
    token_check(AUTH0_SCOPE)
    config = frappe.get_doc("Service Plattform API", "Service Plattform API")
    sub_url = config.get_value(AUTH0_SCOPE, "api_url")
    url = sub_url + "users"
    token = config.get_value(AUTH0_SCOPE, 'api_token')
    headers = {
        "authorization": "Bearer {token}".format(token=token),
        "Content-Type": "application/json"
    }
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for i in range(16))
    payload = json.dumps({
        "email": email,
        "given_name": first_name,
        "family_name": last_name,
        "connection": "Username-Password-Authentication",
        "verify_email": False,
        "password": password
    })
    if debug:
        print("{0}".format(payload))
    try:
        response = requests.post(url, headers=headers, data=payload)

        if debug:
            print("Status code: {0}".format(response.status_code))
            print(response.text)
            
        if response.status_code == 201 or response.status_code == 200:
            # store auth0 key
            data = response.json()
            user_id = data['user_id']
            user_key = frappe.get_doc({
                'doctype': "Auth0 Key",
                'key_type': "User",
                'key_name': email,
                'key': user_id
            })
            user_key.insert(ignore_permissions=True)
            frappe.db.commit()
            
            # successfully created -> trigger pw reset
            url = sub_url + "tickets/password-change"

            payload = json.dumps({
                "result_url": "https://{0}/login".format(frappe.utils.get_host_name()),
                "user_id": user_id
            })
            if debug:
                print("{0}".format(payload))
            response_reset_pw = requests.post(url, headers=headers, data=payload)

            
        return
    except Exception as err:
        if debug:
            print("Error: {0}".format(err))
        frappe.log_error("{0}".format(err), 'update user to auth0 failed')

@frappe.whitelist()
def create_role(role, description, debug=False):
    token_check(AUTH0_SCOPE)
    config = frappe.get_doc("Service Plattform API", "Service Plattform API")
    sub_url = config.get_value(AUTH0_SCOPE, "api_url")
    url = sub_url + "roles"
    token = config.get_value(AUTH0_SCOPE, 'api_token')
    headers = {
        "authorization": "Bearer {token}".format(token=token),
        "Content-Type": "application/json"
    }
    payload = json.dumps({
        "name": role,
        "description": description
    })
    if debug:
        print("{0}".format(payload))
    try:
        response = requests.post(url, headers=headers, data=payload)

        if debug:
            print("Status code: {0}".format(response.status_code))
            print(response.text)
        
        if response.status_code == 201 or response.status_code == 200:
            # store auth0 key
            data = response.json()
            role_id = data['id']
            role_key = frappe.get_doc({
                'doctype': "Auth0 Key",
                'key_type': "Role",
                'key_name': role,
                'key': role_id
            })
            role_key.insert(ignore_permissions=True)
            frappe.db.commit()
        return
    except Exception as err:
        if debug:
            print("Error: {0}".format(err))
        frappe.log_error("{0}".format(err), 'create role to auth0 failed')

@frappe.whitelist()
def assign_roles(user, roles, debug=False):
    # rebuild parameter stack
    user_keys = frappe.db.sql("""
        SELECT `key`
        FROM `tabAuth0 Key`
        WHERE `key_name` = "{user}" and `key_type` = 'User';
    """.format(user=user), as_dict=True)
    if user_keys and len(user_keys) > 0:
        user_id = user_keys[0]['key']
    else:
        frappe.throw( _("User is not in auth0") )
    
    role_ids = []
    if type(roles) == str:
        roles = json.loads(roles)
    for r in roles:
        role_keys = frappe.db.sql("""
            SELECT `key`
            FROM `tabAuth0 Key`
            WHERE `key_name` = "{role}" and `key_type` = 'Role';
        """.format(role=r), as_dict=True)
        if role_keys and len(role_keys) > 0:
            role_ids.append(role_keys[0]['key'])

    token_check(AUTH0_SCOPE)
    config = frappe.get_doc("Service Plattform API", "Service Plattform API")
    sub_url = config.get_value(AUTH0_SCOPE, "api_url")
    url = "{0}users/{1}/roles".format(sub_url, user_id)
    token = config.get_value(AUTH0_SCOPE, 'api_token')
    headers = {
        "authorization": "Bearer {token}".format(token=token),
        "Content-Type": "application/json"
    }
    payload = json.dumps({
        "roles": role_ids
    })
    if debug:
        print("{0}".format(payload))
    try:
        response = requests.post(url, headers=headers, data=payload)

        if debug:
            print("Status code: {0}".format(response.status_code))
            print(response.text)
                    
        return
    except Exception as err:
        if debug:
            print("Error: {0}".format(err))
        frappe.log_error("{0}".format(err), 'assign role to auth0 failed')

# ---------------------------------------------------
# ---------------------------------------------------
# Adressenabgleich
# ---------------------------------------------------
# ---------------------------------------------------

@frappe.whitelist()
def post_retouren(**data):
    return _post_retouren(data)

@frappe.whitelist()
def post_responses(**data):
    return _post_responses(data)
