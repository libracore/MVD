# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def analyse_error_log():
    '''
        Abgefangene Fehler:
        -------------------
        create_kontakt_mitglied
        update_kunde_mitglied
        create_kunde_mitglied
        Sektionswechsel
        SP API Error!
        Fehlerhafte E-Mail
        unbekannter adresstyp
        adress/kontakt anlage: Keine mitglied Adresse
        adress/kontakt anlage: Weder Postfach noch Strasse
        Adresse Typ Objekt: Wurde entfernt; fehlende Strasse
        Adresse Typ Zeitung: Manuelle Verarbeitung
        Adresse Typ Mitbewohner: Manuelle Verarbeitung
        Adresse Typ Filiale: Manuelle Verarbeitung
    '''
    summary = {
        'ec1': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Anlage Kontakt zum Mitglied: Der Vorname war leer oder bestand aus einem Leerschlag'
        },
        'ec2': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Update Kunde vom Mitglied: Der Kundenname war leer oder bestand aus einem Leerschlag obwohl ein Firmenname erfasst war'
        },
        'ec3': {
            'qty': 0,
            'logs': [],
            'beschreibung': '=ec2, aber bei der Anlage eines Kunden zum Mitglied'
        },
        'ec4': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Der Sektionswechsel konnte nicht durchgeführt werden'
        },
        'ec5': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Allgemeiner API Fehler; immer nach raise_xxx'
        },
        'ec6': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Die E-Mail Regex Validierung ist fehlgeschlagen'
        },
        'ec7': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Adressen Handling: Unbekannter Adresstyp'
        },
        'ec8': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Keine Adresse vom Typ "Mitglied" vorhanden'
        },
        'ec9': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Die Adresse vom Typ "Mitglied" besitzt weder ein Postfach noch eine Strasse'
        },
        'ec10': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Die Adresse vom Typ "Objekt" besitzt keine Strasse'
        },
        'ec11': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Adresse vom Typ "Zeitung" muss manuell verarbeitet werden'
        },
        'ec12': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Adresse vom Typ "Mitbewohner" muss manuell verarbeitet werden'
        },
        'ec13': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Adresse vom Typ "Filiale" muss manuell verarbeitet werden'
        },
        'ec14': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Kein Eintrittsdatum'
        },
        'ec15': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Mandatory Error'
        },
        'ec99': {
            'qty': 0,
            'logs': [],
            'beschreibung': 'Noch keine Fehlerspezifische Einzelauswertung oder kein SP API Error'
        }
    }
    
    error_logs = frappe.db.sql("""SELECT * FROM `tabError Log`""", as_dict=True)
    for error_log in error_logs:
        if error_log.method == 'SP API Error!':
            # ec5
            # allgemeiner API Fehler; immer nach raise_xxx
            summary['ec5']['qty'] += 1
            summary['ec5']['logs'].append(error_log.name)
        
        elif error_log.method == 'Fehlerhafte E-Mail':
            # ec6
            # email regex failed
            summary['ec6']['qty'] += 1
            summary['ec6']['logs'].append(error_log.name)
        
        elif error_log.method == 'create_kontakt_mitglied':
            # ec1
            # empty (or just a space) contact first name
            if 'fallback: first_name was' in error_log.error:
                summary['ec1']['qty'] += 1
                summary['ec1']['logs'].append(error_log.name)
        
        elif error_log.method == 'update_kunde_mitglied':
            # ec2
            # empty (or just a space) customer name, but with company
            if 'fallback: customer_name was' in error_log.error:
                summary['ec2']['qty'] += 1
                summary['ec2']['logs'].append(error_log.name)
        
        elif error_log.method == 'create_kunde_mitglied':
            # ec3
            # same as ec2, but in create method
            if 'fallback: customer_name was' in error_log.error:
                summary['ec3']['qty'] += 1
                summary['ec3']['logs'].append(error_log.name)
        
        elif error_log.method == 'Sektionswechsel':
            # ec4
            # sektionswechsel konnte nicht durchgeführt werden
            summary['ec4']['qty'] += 1
            summary['ec4']['logs'].append(error_log.name)
        
        elif error_log.method == 'unbekannter adresstyp':
            # ec7
            # unbekannter adresstyp
            summary['ec7']['qty'] += 1
            summary['ec7']['logs'].append(error_log.name)
        
        elif error_log.method == 'adress/kontakt anlage: Keine mitglied Adresse':
            # ec8
            summary['ec8']['qty'] += 1
            summary['ec8']['logs'].append(error_log.name)
        
        elif error_log.method == 'adress/kontakt anlage: Weder Postfach noch Strasse':
            # ec9
            summary['ec9']['qty'] += 1
            summary['ec9']['logs'].append(error_log.name)
        
        elif error_log.method == 'Adresse Typ Objekt: Wurde entfernt; fehlende Strasse':
            # ec10
            summary['ec10']['qty'] += 1
            summary['ec10']['logs'].append(error_log.name)
        
        elif error_log.method == 'Adresse Typ Zeitung: Manuelle Verarbeitung':
            # ec11
            summary['ec11']['qty'] += 1
            summary['ec11']['logs'].append(error_log.name)
        
        elif error_log.method == 'Adresse Typ Mitbewohner: Manuelle Verarbeitung':
            # ec12
            summary['ec12']['qty'] += 1
            summary['ec12']['logs'].append(error_log.name)
        
        elif error_log.method == 'Adresse Typ Filiale: Manuelle Verarbeitung':
            # ec13
            summary['ec13']['qty'] += 1
            summary['ec13']['logs'].append(error_log.name)
        
        elif 'frappe.exceptions.MandatoryError:' in error_log.error:
            if ': eintritt' in error_log.error:
                # ec14
                summary['ec14']['qty'] += 1
                summary['ec14']['logs'].append(error_log.name)
            else:
                # ec15
                summary['ec15']['qty'] += 1
                summary['ec15']['logs'].append(error_log.name)
        else:
            # ec99
            # noch keine einzelauswertung
            summary['ec99']['qty'] += 1
            summary['ec99']['logs'].append(error_log.name)
    
    return summary
