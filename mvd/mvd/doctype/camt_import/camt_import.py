# -*- coding: utf-8 -*-
# Copyright (c) 2022-2026, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint
from frappe.utils.background_jobs import enqueue
from mvd.mvd.doctype.camt_import.helpers import *
from mvd.mvd.doctype.camt_import.utils import *
from mvd.mvd.doctype.camt_import.reset_protokoll import generation_fuer_verarbeitung as generation, ist_aktuell
from mvd.mvd.doctype.camt_import.fortschritt import (beginnen as fortschritt_beginnen,
    erfassen as fortschritt_erfassen, abschliessen as fortschritt_abschliessen,
    beim_laden as fortschritt_beim_laden, uebersicht as fortschritt_uebersicht,
    pruefe_start as fortschritt_pruefe_start)

class CAMTImport(Document):
    def onload(self):
        bearbeiten = not self.version_1 and self.has_permission('write')

        self.set_onload('hat_zahlungen_zum_matchen', bool(
            bearbeiten and self.status in ('Zahlungen eingelesen', 'Zahlungen zugeordnet')
            and get_zahlungen_zum_matchen(self.name, nur_erster=True)))
        
        self.set_onload('hat_offene_rechnungs_matches', bool(
            bearbeiten and self.status in ('Zahlungen zugeordnet', 'Verarbeitet')
            and get_rechnungs_matches_zum_verbuchen(self.name, nur_erster=True)))
        
        self.set_onload('verarbeitung_auftrag', fortschritt_beim_laden(self) if bearbeiten else None)

    def validate(self):
        if self.name and not self.get('__islocal') and not frappe.flags.get('camt_reset_in_arbeit'):
            self.reset_protokoll = frappe.db.get_value('CAMT Import', self.name, 'reset_protokoll')
        
        if not self.sektion_id:
            sektionen = frappe.db.sql("""SELECT `for_value` FROM `tabUser Permission` WHERE `allow` = 'Sektion' AND `is_default` = 1 AND `user` = '{user}'""".format(user=frappe.session.user), as_dict=True)
            if len(sektionen) > 0:
                self.sektion_id = sektionen[0].for_value
                sektion = frappe.get_doc("Sektion", sektionen[0].for_value)
                self.company = sektion.company
                self.account = sektion.account

@frappe.whitelist()
def hat_offene_rechnungs_matches(camt_import):
    doc = frappe.get_doc('CAMT Import', camt_import)
    doc.check_permission('read')
    if doc.status != 'Verarbeitet' or not doc.has_permission('write'):
        return False
    
    return bool(get_rechnungs_matches_zum_verbuchen(camt_import, nur_erster=True))

def _registriere_fehler(camt_import, schritt, err):
    message = '{0}: {1}'.format(schritt, str(err) or type(err).__name__)
    details = message + '\n\n' + frappe.get_traceback()

    try:
        frappe.log_error(details, 'CAMT-Import {0}: {1}'.format(camt_import, schritt))
    except Exception:
        details += '\n\nDer Error-Log-Eintrag konnte nicht angelegt werden. Die Fehlerdetails sind hier im CAMT-Import gespeichert.'
    
    frappe.db.set_value('CAMT Import', camt_import, {'status': 'Failed', 'errors': details})

    return {
        'status': 'Failed',
        'message': message
    }

@frappe.whitelist()
def lese_camt_file(camt_import, file_path, einlesen, matchen, verbuchen, all_in_one, nachladen=0):
    laufender_auftrag = fortschritt_pruefe_start(camt_import)

    if laufender_auftrag:
        return laufender_auftrag

    def get_camt_step(einlesen, matchen, verbuchen, all_in_one, nachladen):
        if cint(all_in_one) == 1:
            return 'All in one'
        if cint(einlesen) == 1:
            return 'Einlesen'
        if cint(matchen) == 1:
            return 'Zuweisen'
        if cint(verbuchen) == 1:
            return 'Verbuchen'
        if cint(nachladen) == 1:
            return 'Nachladen von Zahlungen'
    
    # lese und prüfe camt file
    try:
        camt_file = get_camt_file(file_path)
        if not camt_file:
            raise frappe.ValidationError('Die CAMT-Datei konnte nicht gelesen werden.')
    except Exception as err:
        return _registriere_fehler(camt_import, 'Datei lesen', err)

    if cint(einlesen) == 1 or cint(nachladen) == 1:
        pruefe_camt_iban(camt_file, frappe.get_doc("CAMT Import", camt_import))
    
    progress_token = None
    try:
        args = {
            'camt_file': file_path,
            'camt_import': camt_import,
            'einlesen': einlesen,
            'matchen': matchen,
            'verbuchen': verbuchen,
            'all_in_one': all_in_one,
            'nachladen': nachladen,
            'reset_generation': generation(camt_import)
        }

        progress_token = fortschritt_beginnen(camt_import, args['reset_generation'], _verarbeitungs_schritt(einlesen, matchen, verbuchen, nachladen))
        args['progress_token'] = progress_token
        sektion = frappe.db.get_value("CAMT Import", camt_import, "sektion_id")

        frappe.db.set_value('CAMT Import', camt_import, {'status': 'In Verarbeitung', 'errors': None})

        enqueue("mvd.mvd.doctype.camt_import.camt_import.verarbeite_camt_file", queue='long', job_name='Verarbeite {0} CAMT Import {1} ({2})'.format(sektion, camt_import, get_camt_step(einlesen, matchen, verbuchen, all_in_one, nachladen)), timeout=5000, **args)
    except Exception as err:
        result = _registriere_fehler(camt_import, 'Verarbeitung starten', err)
        if progress_token:
            result['progress_token'] = progress_token
            fortschritt_abschliessen(camt_import, progress_token, result)
        return result
    
    return {
        'status': 'In Verarbeitung',
        'progress_token': progress_token
    }

def _verarbeitungs_schritt(einlesen, matchen, verbuchen, nachladen):
    if cint(einlesen):
        return 'Einlesen'
    if cint(matchen):
        return 'Matchen'
    if cint(verbuchen):
        return 'Verbuchen'
    return 'Nachladen' if cint(nachladen) else 'Übersicht'

def verarbeite_camt_file(camt_file, camt_import, einlesen, matchen, verbuchen, all_in_one, nachladen, reset_generation=None, progress_token=None):
    if not progress_token:
        return _verarbeite_camt_file(camt_file, camt_import, einlesen, matchen, verbuchen, all_in_one, nachladen, reset_generation)
    
    with fortschritt_erfassen(camt_import, progress_token, reset_generation, _verarbeitungs_schritt(einlesen, matchen, verbuchen, nachladen)) as aktiv:
        if not aktiv:
            return
        try:
            result = _verarbeite_camt_file(camt_file, camt_import, einlesen, matchen, verbuchen, all_in_one, nachladen, reset_generation)
        except Exception as err:
            result = _registriere_fehler(camt_import, 'Verarbeitung', err)

        fortschritt_abschliessen(camt_import, progress_token, result)

        return result

def _verarbeite_camt_file(camt_file, camt_import, einlesen, matchen, verbuchen, all_in_one, nachladen, reset_generation=None):
    try:
        if not ist_aktuell(camt_import, reset_generation):
            return
    except Exception as err:
        return _registriere_fehler(camt_import, 'Verarbeitung prüfen', err)
    
    def get_next_step(einlesen, matchen, verbuchen):
        if cint(einlesen) == 1:
            return 0, 1, 0
        if cint(matchen) == 1:
            return 0, 0, 1
        if cint(verbuchen) == 1:
            return 0, 0, 0

    # lese und prüfe camt file
    file_path = camt_file
    try:
        camt_file = get_camt_file(camt_file)
        if not camt_file:
            raise frappe.ValidationError('Die CAMT-Datei konnte nicht gelesen werden.')
    except Exception as err:
        return _registriere_fehler(camt_import, 'Datei lesen', err)
    
    if cint(einlesen) == 1:
        try:
            zahlungen_einlesen(camt_file, camt_import)
            # Aktualisiere CAMT Übersicht
            fortschritt_uebersicht(camt_import)
            aktualisiere_camt_uebersicht(camt_import)
            camt_status_update(camt_import, 'Zahlungen eingelesen')
            einlesefehler = get_offene_einlesefehler(camt_import)
            if cint(all_in_one) and einlesefehler:
                return {
                    'status': 'paused',
                    'message': '{0} Zahlung(en) konnten nicht eingelesen werden. Die automatische Verarbeitung wurde angehalten. Bitte prüfen Sie den Bericht und laden Sie die fehlenden Zahlungen nach.'.format(einlesefehler)
                }
        except Exception as err:
            return _registriere_fehler(camt_import, 'Zahlungen einlesen', err)
    elif cint(matchen) == 1:
        # Matchen von Zahlungen
        try:
            abweichungen = zahlungen_matchen(camt_import)
            # Aktualisiere CAMT Übersicht
            fortschritt_uebersicht(camt_import)
            aktualisiere_camt_uebersicht(camt_import)
            camt_status_update(camt_import, 'Zahlungen zugeordnet')
            if abweichungen:
                # Gesamtlauf wartet auf Entscheidung des Benutzers
                return
        except Exception as err:
            return _registriere_fehler(camt_import, 'Zahlungen zuordnen', err)
    elif  cint(verbuchen) == 1:
        # Verbuche Matches
        try:
            verbuche_matches(camt_import)
            # Aktualisiere CAMT Übersicht
            fortschritt_uebersicht(camt_import)
            aktualisiere_camt_uebersicht(camt_import)
        except Exception as err:
            return _registriere_fehler(camt_import, 'Zahlungen verbuchen', err)
    elif cint(nachladen) == 1:
        try:
            zahlungen_einlesen(camt_file, camt_import, nachladen=True)
            # Aktualisiere CAMT Übersicht
            fortschritt_uebersicht(camt_import)
            aktualisiere_camt_uebersicht(camt_import)
            camt_status_update(camt_import, 'Zahlungen eingelesen')
        except Exception as err:
            return _registriere_fehler(camt_import, 'Zahlungen nachladen', err)
    else:
        # Aktualisiere CAMT Übersicht
        try:
            aktualisiere_camt_uebersicht(camt_import)
        except Exception as err:
            return _registriere_fehler(camt_import, 'Übersicht aktualisieren', err)
    
    if cint(all_in_one) == 1:
        try:
            einlesen, matchen, verbuchen = get_next_step(einlesen, matchen, verbuchen)
            if cint(einlesen) != 0 or cint(matchen) != 0 or cint(verbuchen) != 0:
                return lese_camt_file(camt_import, file_path, einlesen, matchen, verbuchen, all_in_one)
        except Exception as err:
            return _registriere_fehler(camt_import, 'Nächsten Verarbeitungsschritt starten', err)
    
    return
