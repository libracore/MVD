# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore AG and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.password import get_decrypted_password
from frappe.utils import cint
import urllib.parse as urlparse
import requests
import posixpath
import mimetypes

# -----------------------------------
# ---------- Hilfsmethoden ----------
# -----------------------------------
class NCSettings():
    def __init__(self, sektion=None):
        '''
        Alle Einstellungen rundum die Nextcloud Anbindung als Klassenobjekt
        '''
        if not sektion:
            frappe.throw("Keine Sektion zur Initialisierung von NCSettings", title="NCSettings: __init__")
        
        mvd_settings    = frappe.get_doc("MVD Settings", "MVD Settings")
        sektion_settings = frappe.get_doc("Sektion", sektion)
        self.IS_ENABLED = True if cint(sektion_settings.nc_enabled) == 1 else False
        self.BASE_SEKTION = sektion_settings.nc_base_folder or sektion_settings.name
        self.BASE_MITGLIED = "{0}/{1}".format(self.BASE_SEKTION, sektion_settings.nc_mitglied_base_folder or "Mitglieder")
        self.BASE_BERATUNG = "{0}/{1}".format(self.BASE_SEKTION, sektion_settings.nc_beratung_base_folder or "Beratungen")

        self.BASE_ORIGIN = mvd_settings.nc_host
        self.USERNAME    = mvd_settings.nc_user
        self.WEBDAV_BASE = "{0}/remote.php/dav/files/{1}".format(self.BASE_ORIGIN, urlparse.quote(self.USERNAME))
        self.APP_PASS    = get_decrypted_password("MVD Settings", "MVD Settings", 'nc_password', False)
        self.VERIFY_TLS  = True if cint(mvd_settings.nc_verify_ssl) else False

def ensure_folder(folder_path):
    '''
    Hilfsfunktion zur sicherstellung dass der Zielordner in der Nextcloud existiert.
    Sollte er fehlen, wird er hiermit erstellt.
    '''
    parts = [p for p in folder_path.split("/") if p]
    current = "/"
    with requests.Session() as s:
        s.auth = (ncs.USERNAME, ncs.APP_PASS)
        for p in parts:
            current = posixpath.join(current, p)
            url = join_webdav_path(current)
            # Existenz per PROPFIND Depth:0 prüfen
            head = s.request("PROPFIND", url, headers={"Depth": "0"}, verify=ncs.VERIFY_TLS)
            if head.status_code == 404:
                mk = s.request("MKCOL", url, verify=ncs.VERIFY_TLS)
                if mk.status_code not in (201, 405):
                    # 201=created, 405=already exists (je nach Setup)
                    mk.raise_for_status()

def join_webdav_path(*parts):
    '''
    Hilfsfunktion zum zusammensetzen des Pfads als korrekte WebDAV-URL (posix, ohne doppelte //)
    '''
    path = posixpath.join(*parts)
    if not path.startswith("/"):
        path = "/" + path
    return ncs.WEBDAV_BASE + path

def move_folder(src_folder_path, dst_folder_path):
    """
    Verschiebt einen Ordner (inkl. aller enthaltenen Dateien/Unterordner)
    von src_folder_path nach dst_folder_path in der Nextcloud

    Pfade sind relativ zum Nextcloud-Root des Users, z.B.:
    src_folder_path = "Sektion1/Mitglieder/1234"
    dst_folder_path = "Sektion1/Mitglieder_alt/1234"
    """
    # Source- und Destination-Pfade „säubern“
    src_folder_path = src_folder_path.strip("/")
    dst_folder_path = dst_folder_path.strip("/")

    # Ziel-Elternordner sicherstellen (damit MOVE nicht scheitert)
    dst_parent = posixpath.dirname("/" + dst_folder_path)
    if dst_parent not in ("/", "", "."):
        ensure_folder(dst_parent)

    # Vollständige WebDAV-URLs aufbauen
    src_url = join_webdav_path("/" + src_folder_path)
    dst_url = join_webdav_path("/" + dst_folder_path)

    # MOVE per WebDAV
    with requests.Session() as s:
        s.auth = (ncs.USERNAME, ncs.APP_PASS)
        headers = {
            "Destination": dst_url,
            "Overwrite": "T" # überschreiben, falls Ziel schon existiert
        }
        resp = s.request("MOVE", src_url, headers=headers, verify=ncs.VERIFY_TLS)

        # Gängige "OK"-Statuscodes: 201 Created, 204 No Content
        if resp.status_code not in (201, 204):
            frappe.log_error("status_code: {0}\nError: {1}\nsrc_url: {2}\ndst_url: {3}".format(resp.status_code, resp.text, src_url, dst_url))
            resp.raise_for_status()

def upload_files(folder_path, files):
    """
    Lädt Dateien in den angegebenen Nextcloud-Ordner hoch.
    files = Liste von (filename, bytes)

    Beispiele:
    1. Upload einer lokalen Datei:
    with open("/tmp/vertrag.pdf", "rb") as f:
        upload_files(
            f"{ncs.BASE_MITGLIED}/{mitglied.mitglied_nr}",
            [("vertrag.pdf", f.read())]
        )
    
    2. Upload ein Frappe-File-Doc:
    file_doc = frappe.get_doc("File", file_id)
    content = file_doc.get_content()   # liefert Bytes
    upload_files(
        f"{ncs.BASE_MITGLIED}/{mitglied.mitglied_nr}",
        [(file_doc.file_name, content)]
    )
    """
    folder_path = folder_path.strip("/")
    ensure_folder(folder_path)

    with requests.Session() as s:
        s.auth = (ncs.USERNAME, ncs.APP_PASS)

        for filename, file_bytes in files:
            mime_type, _ = mimetypes.guess_type(filename)
            mime_type = mime_type or "application/octet-stream"

            remote_path = posixpath.join("/", folder_path, filename)
            url = join_webdav_path(remote_path)

            resp = s.put(
                url,
                data=file_bytes,
                headers={"Content-Type": mime_type},
                verify=ncs.VERIFY_TLS
            )

            if resp.status_code not in (200, 201, 204):
                resp.raise_for_status()

# ----------------------------------------
# ---------- Funktions-Methoden ----------
# ----------------------------------------
def new_mitgliedschaft(mitglied):
    # Initialisiere globale Settings-Klasse
    sektion = mitglied.sektion_id
    global ncs
    ncs = NCSettings(sektion)

    # DoNothing wenn NextCloud in der Sektion deaktiviert
    if not ncs.IS_ENABLED:
        return
    
    # Erstelle Sektions-Mitgliedschafts-Oder falls nicht vorhanden
    if mitglied.mitglied_nr and mitglied.mitglied_nr != "MV":
        try:
            ensure_folder("{0}/{1}".format(ncs.BASE_MITGLIED, mitglied.mitglied_nr))
        except Exception as err:
            frappe.log_error(str(err), "NextCloud: new_mitgliedschaft > ensure_folder")

def new_beratung(beratung):
    # Initialisiere globale Settings-Klasse
    sektion = beratung.sektion_id
    global ncs
    ncs = NCSettings(sektion)

    # DoNothing wenn NextCloud in der Sektion deaktiviert
    if not ncs.IS_ENABLED:
        return
    
    mitglied_nr = None
    if beratung.mv_mitgliedschaft:
        mitglied_nr = frappe.db.get_value("Mitgliedschaft", beratung.mv_mitgliedschaf, "mitglied_nr")
    
    if mitglied_nr and mitglied_nr != "MV":
        # Erstelle Sektions-Mitgliedschafts-Beratungs-Oder falls nicht vorhanden
        try:
            ensure_folder("{0}/{1}/{2}".format(ncs.BASE_MITGLIED, mitglied_nr, beratung.name))
        except Exception as err:
            frappe.log_error(str(err), "NextCloud: new_beratung > ensure_folder (mit Mitglied)")
    else:
        # Erstelle Sektions-Beratungs-Oder falls nicht vorhanden
        try:
            ensure_folder("{0}/{1}".format(ncs.BASE_BERATUNG, beratung.name))
        except Exception as err:
            frappe.log_error(str(err), "NextCloud: new_beratung > ensure_folder (ohne Mitglied)")

def added_mitglied_to_beratung(beratung):
    # Initialisiere globale Settings-Klasse
    sektion = beratung.sektion_id
    global ncs
    ncs = NCSettings(sektion)

    # DoNothing wenn NextCloud in der Sektion deaktiviert
    if not ncs.IS_ENABLED:
        return
    
    if beratung.mv_mitgliedschaft:
        mitglied_nr = frappe.db.get_value("Mitgliedschaft", beratung.mv_mitgliedschaf, "mitglied_nr")
        if mitglied_nr and mitglied_nr != "MV":
            # Verschiebe Sektions-Beratungs-Oder zu Sektions-Mitgliedschafts-Beratungs-Oder (wird erstellt wenn nicht vorhanden)
            try:
                move_folder("{0}/{1}".format(ncs.BASE_BERATUNG, beratung.name), "{0}/{1}/{2}".format(ncs.BASE_MITGLIED, mitglied_nr, beratung.name))
            except Exception as err:
                frappe.log_error(str(err), "NextCloud: added_mitglied_to_beratung > move_folder")
