# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft import mvm_mitglieder, mvm_kuendigung, mvm_sektionswechsel
import json
import requests
from frappe.utils.background_jobs import enqueue

# for test
# ---------------------------------------------------
@frappe.whitelist()
def whoami(type='light'):
    user = frappe.session.user
    if type == 'full':
        user = frappe.get_doc("User", user)
        return user
    else:
        return user

# live functions
# ---------------------------------------------------
# ausgehend
# ---------------------------------------------------
def neue_mitglieder_nummer(sektion_code):
    if not int(frappe.db.get_single_value('Service Plattform API', 'not_get_number_and_id')) == 1:
        if auth_check():
            sub_url = frappe.db.get_single_value('Service Plattform API', 'api_url')
            endpoint = frappe.db.get_single_value('Service Plattform API', 'neue_mitglieder_nummer')
            url = sub_url + endpoint + '/{sektion_code}'.format(sektion_code=sektion_code)
            token = frappe.db.get_single_value('Service Plattform API', 'api_token')
            headers = {"authorization": "Bearer {token}".format(token=token)}
            
            try:
                mitglied_nr_obj = requests.post(url, headers = headers)
                mitglied_nr_obj = mitglied_nr_obj.json()
                if 'mitgliedNummer' not in mitglied_nr_obj:
                    frappe.log_error("{0}".format(mitglied_nr_obj), 'neue_mitglieder_nummer failed')
                    frappe.throw("Zur Zeit können keine Daten von der Serviceplatform bezogen werden.")
                
                return mitglied_nr_obj
            except Exception as err:
                frappe.log_error("{0}".format(err), 'neue_mitglieder_nummer failed')
                frappe.db.commit()
    else:
        frappe.log_error("SektionsCode: {0}".format(sektion_code), 'neue_mitglieder_nummer deaktiviert: manuelle vergabe')
        return {
            'mitgliedNummer': '13467985',
            'mitgliedId': '97624986'
        }

def update_mvm(mvm, update):
    if not int(frappe.db.get_single_value('Service Plattform API', 'no_sp_update')) == 1:
        if auth_check():
            sub_url = str(frappe.db.get_single_value('Service Plattform API', 'api_url'))
            endpoint = str(frappe.db.get_single_value('Service Plattform API', 'mitglieder'))
            url = sub_url + endpoint
            token = frappe.db.get_single_value('Service Plattform API', 'api_token')
            headers = {"authorization": "Bearer {token}".format(token=token)}
            
            if update:
                sp_connection = requests.put(url, json = mvm, headers = headers)
            else:
                sp_connection = requests.post(url, json = mvm, headers = headers)
            
            try:
                if sp_connection.status_code != 204:
                    frappe.log_error("{0}\n\n{1}\n\n{2}".format(sp_connection.status_code, sp_connection.text, mvm), 'update_mvm failed')
                    frappe.db.commit()
                    return
                else:
                    return
            except Exception as err:
                frappe.log_error("{0}\n\n{1}".format(err, mvm), 'update_mvm failed')
                frappe.db.commit()
                return
    else:
        frappe.log_error("{0}".format(mvm), 'update_mvm deaktiviert')
        return

def auth_check():
    sub_url = str(frappe.db.get_single_value('Service Plattform API', 'api_url'))
    endpoint = str(frappe.db.get_single_value('Service Plattform API', 'auth_check'))
    url = sub_url + endpoint
    token = frappe.db.get_single_value('Service Plattform API', 'api_token')
    
    headers = {"authorization": "Bearer {token}".format(token=token)}
    response = requests.get(url, headers = headers)
    
    try:
        response = response.json()
        
        if response["status"] == 'Ok':
            return True
    except:
        frappe.log_error("{0}".format(response), 'auth_check failed, get new token')
        # get new token and try again
        get_token()
        token = frappe.db.get_single_value('Service Plattform API', 'api_token')
        headers = {"authorization": "Bearer {token}".format(token=token)}
        response = requests.get(url, headers = headers)
        response = response.json()
        
        try:
            if response["status"] == 'Ok':
                return True
        except:
            frappe.log_error("{0}".format(response), 'auth_check failed')
            frappe.db.commit()
            return False

def get_token():
    url = frappe.db.get_single_value('Service Plattform API', 'api_token_url')
    client_id = frappe.db.get_single_value('Service Plattform API', 'client_id')
    client_secret = frappe.db.get_single_value('Service Plattform API', 'api_secret')
    audience = frappe.db.get_single_value('Service Plattform API', 'api_url')
    
    headers = {"content-type": "application/json"}
    data = {"client_id": "{0}".format(client_id), "client_secret":"{0}".format(client_secret), "audience":"{0}".format(audience), "grant_type":"client_credentials"}
    
    response = requests.post(url, json = data, headers = headers)
    
    try:
        response = response.json()
        token = response["access_token"]
        frappe.db.set_value('Service Plattform API', 'Service Plattform API', 'api_token', token)
        frappe.db.commit()
    except Exception as err:
        frappe.log_error("{0}\n\n{1}".format(err, response), 'get_token failed')
    return

# eingehend
# ---------------------------------------------------
# create/update existing MV Mitgliedschaft
@frappe.whitelist()
def mitglieder(**mitgliedschaft):
    return mvm_mitglieder(mitgliedschaft)

# @frappe.whitelist()
# def kuendigung(**mitgliedschaft):
    # return mvm_kuendigung(**mitgliedschaft)

# @frappe.whitelist()
# def sektionswechsel(sektion_code):
    # return mvm_sektionswechsel(sektion_code)
