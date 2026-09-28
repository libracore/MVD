# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import frappe
from frappe.www.login import login_via_auth0 as frappe_login_via_auth0

VA_REDIRECT_TARGETS = ('/va/vergabeliste', '/va/meine-mandate')

def get_context(context):
    target = frappe.form_dict.get('redirect-to')
    if target not in VA_REDIRECT_TARGETS:
        return

    for provider in context.get('provider_logins', []):
        if provider.get('name') != 'auth0':
            continue
        url = urlsplit(provider['auth_url'])
        query = []
        for key, value in parse_qsl(url.query, keep_blank_values=True):
            if key == 'state':
                state = json.loads(value)
                state['va_redirect_to'] = target
                value = json.dumps(state)
            query.append((key, value))
        provider['auth_url'] = urlunsplit((
            url.scheme, url.netloc, url.path, urlencode(query), url.fragment
        ))


@frappe.whitelist(allow_guest=True)
def login_via_auth0(code=None, state=None, error=None):
    # Frappe OAuth token validierung
    result = frappe_login_via_auth0(code=code, state=state, error=error)
    # Redirect
    if (frappe.session.user != 'Guest'
            and frappe.local.response.get('type') == 'redirect'):
        target = json.loads(state).get('va_redirect_to')
        if target in VA_REDIRECT_TARGETS:
            frappe.local.response['location'] = target
    return result
