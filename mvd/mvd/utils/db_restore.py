# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

'''
Beispiel für site_config:

 "mvd": {
  "api_url": "https:...",
  "access_token_url": "https:...",
  "client_id": "xxx",
  "client_secret": "xxx",
  "emailberatung_test_token": "xxx",
  "post_url": "https:...",
  "post_username": "xxx",
  "post_password": "xxx",
  "post_host": "fdsbc.post.ch",
  "post_port": "22",
  "post_target_path": "dfu-inbox",
  "post_user": "xxx",
  "service_plattform_api_connections": ["ServicePF", "Auth0", "PostNotiz"],
  "email_accounts": [
   ["x@y.ch", "Titel", "xxx"]
  ]
 }
'''

def run():
    print("Lade Keys...")
    keys = keys_object()

    print("Starte Löschvorgang...")
    delete_email_accounts()
    delete_notifications()
    delete_auto_email_reports()
    delete_service_plattform_api_connections()

    print("Starte Datenanlage...")
    create_service_plattform_api(keys)
    create_postretouren_einstellungen(keys)
    create_email_accounts(keys)

    print("Der Prozess ist beendet, vergessen Sie nicht das Post Key-File manuell zu prüfen sowie die E-Mail-Account Settings vorzunehmen!")

def delete_email_accounts():
    print("Lösche Email Accounts...")
    frappe.db.sql("""DELETE FROM `tabEmail Account`""", as_list=True)
    frappe.db.commit()

def delete_notifications():
    print("Lösche Notifications...")
    frappe.db.sql("""DELETE FROM `tabNotification`""", as_list=True)
    frappe.db.commit()

def delete_auto_email_reports():
    print("Lösche Auto Email Reports...")
    frappe.db.sql("""DELETE FROM `tabAuto Email Report`""", as_list=True)
    frappe.db.commit()

def delete_service_plattform_api_connections():
    print("Lösche Service Plattform API Connection...")
    frappe.db.sql("""DELETE FROM `tabService Plattform API Connection`""", as_list=True)
    frappe.db.commit()

def create_service_plattform_api(keys):
    connections = keys.service_plattform_api_connections
    for connection in connections:
        print("{0} Anlage...".format(connection))
        service_plattform_api = frappe.get_doc("Service Plattform API", "Service Plattform API")
        row = service_plattform_api.append('connections', {})
        row.connection = connection
        row.api_url = keys.api_url
        row.api_token_url = keys.access_token_url
        row.client_id = keys.client_id
        row.api_secret = keys.client_secret
        service_plattform_api.save()
        frappe.db.commit()
    
    print("Anlage E-Mailberatung Testtoken...")
    service_plattform_api = frappe.get_doc("Service Plattform API", "Service Plattform API")
    service_plattform_api.emailberatung_testtoken = keys.emailberatung_test_token

def create_postretouren_einstellungen(keys):
    print("Anlage Postretouren Einstellungen...")
    postretouren_einstellungen = frappe.get_doc("Postretouren Einstellungen", "Postretouren Einstellungen")
    postretouren_einstellungen.url = keys.post_url
    postretouren_einstellungen.basic_auth_username = keys.post_username
    postretouren_einstellungen.basic_auth_password = keys.post_password
    postretouren_einstellungen.host = keys.post_host
    postretouren_einstellungen.port = keys.post_port
    postretouren_einstellungen.target_path = keys.post_target_path
    postretouren_einstellungen.user = keys.post_user
    postretouren_einstellungen.save()
    frappe.db.commit()

def create_email_accounts(keys):
    for email_account in keys.email_accounts:
        new_account = frappe.get_doc({
            'doctype': 'Email Account',
            'email_id': email_account[0],
            'email_account_name': email_account[1],
            'password': email_account[2]
        }).insert()
        frappe.db.commit()

class keys_object:
    status = 0
    # Service Plattform API
    service_plattform_api_connections = frappe.get_site_config().mvd['service_plattform_api_connections']
    api_url = frappe.get_site_config().mvd['api_url']
    access_token_url = frappe.get_site_config().mvd['access_token_url']
    client_id = frappe.get_site_config().mvd['client_id']
    client_secret = frappe.get_site_config().mvd['client_secret']
    emailberatung_test_token = frappe.get_site_config().mvd['emailberatung_test_token']
    
    # Postretouren Einstellungen
    post_url = frappe.get_site_config().mvd['post_url']
    post_username = frappe.get_site_config().mvd['post_username']
    post_password = frappe.get_site_config().mvd['post_password']
    post_host = frappe.get_site_config().mvd['post_host']
    post_port = frappe.get_site_config().mvd['post_port']
    post_target_path = frappe.get_site_config().mvd['post_target_path']
    post_user = frappe.get_site_config().mvd['post_user']

    # E-Mail Accounts
    email_accounts = frappe.get_site_config().mvd['email_accounts']