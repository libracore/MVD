from __future__ import unicode_literals
import frappe
import jwt
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_mitglied_id_from_nr

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
    else:
        context.test_status = 'no authorization_header found'

    if jwt_token:
        try:
            public_key = frappe.db.get_single_value('JWT', 'public_key')
            algorythmus = frappe.db.get_single_value('JWT', 'algorythmus')
            decoded_jwt_token = jwt.decode(jwt_token, public_key, algorithms=[algorythmus])
            context.jwt_token = decoded_jwt_token
        except Exception as err:
            context.test_status = 'Exception in JWT decode:<br>{0}'.format(str(err))
        
        if 'mitglied_nr' in decoded_jwt_token:
            mitglied_id = get_mitglied_id_from_nr(decoded_jwt_token["mitglied_nr"])
            if mitglied_id:
                if frappe.db.exists("Mitgliedschaft", mitglied_id):
                    context.test_status = 'All good!'
                else:
                    context.test_status = 'no existing Mitgliedschaft based on jwt-token found'
            else:
                context.test_status = 'no mitglied_id based on jwt-token found'
        else:
            context.test_status = 'no mitglied_nr in jwt-token found'
    else:
        context.test_status = 'no jwt-token found'
    
    return context