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
import xml.etree.ElementTree as ET

# ---------------------------------------------
# ---------- NextCloud Klassenobjekt ----------
# ---------------------------------------------
class NCSettings():
    def __init__(self, sektion=None):
        '''
        Alle Einstellungen inkl. Hilfsmethoden rundum die Nextcloud Anbindung als Klassenobjekt
        '''
        if not sektion:
            self.IS_ENABLED = False
            return
        
        mvd_settings                = frappe.get_doc("MVD Settings", "MVD Settings")
        sektion_settings            = frappe.get_doc("Sektion", sektion)
        self.IS_ENABLED             = True if cint(sektion_settings.nc_enabled) == 1 else False
        self.BASE_SEKTION           = sektion_settings.nc_base_folder or sektion_settings.name
        self.BASE_MITGLIED          = "{0}/{1}".format(self.BASE_SEKTION, sektion_settings.nc_mitglied_base_folder or "Mitglieder")
        self.BASE_MITGLIED_BERATUNG = "{0}/{1}/<platzhalter>/{2}".format(self.BASE_SEKTION, sektion_settings.nc_mitglied_base_folder or "Mitglieder", sektion_settings.nc_mitglied_beratung_base_folder or "Beratungen")
        self.BASE_BERATUNG          = "{0}/{1}".format(self.BASE_SEKTION, sektion_settings.nc_beratung_base_folder or "Beratungen")

        self.BASE_ORIGIN            = mvd_settings.nc_host
        self.USERNAME               = mvd_settings.nc_user
        self.WEBDAV_BASE            = "{0}/remote.php/dav/files/{1}".format(self.BASE_ORIGIN, urlparse.quote(self.USERNAME))
        self.APP_PASS               = get_decrypted_password("MVD Settings", "MVD Settings", 'nc_password', False)
        self.VERIFY_TLS             = True if cint(mvd_settings.nc_verify_ssl) else False

        self.DAV_NS                 = {
                                        "d": "DAV:",
                                        "oc": "http://owncloud.org/ns",
                                        "nc": "http://nextcloud.org/ns",
                                    }

    def ensure_folder(self, folder_path):
        '''
        Hilfsfunktion zur sicherstellung dass der Zielordner in der Nextcloud existiert.
        Sollte er fehlen, wird er hiermit erstellt.
        '''
        parts = [p for p in folder_path.split("/") if p]
        current = "/"
        with requests.Session() as s:
            s.auth = (self.USERNAME, self.APP_PASS)
            for p in parts:
                current = posixpath.join(current, p)
                url = self.join_webdav_path(current)
                # Existenz per PROPFIND Depth:0 prüfen
                head = s.request("PROPFIND", url, headers={"Depth": "0"}, verify=self.VERIFY_TLS)
                if head.status_code == 404:
                    mk = s.request("MKCOL", url, verify=self.VERIFY_TLS)
                    if mk.status_code not in (201, 405):
                        # 201=created, 405=already exists (je nach Setup)
                        mk.raise_for_status()

    def join_webdav_path(self, *parts):
        '''
        Hilfsfunktion zum zusammensetzen des Pfads als korrekte WebDAV-URL (posix, ohne doppelte //)
        '''
        path = posixpath.join(*parts)
        if not path.startswith("/"):
            path = "/" + path
        return self.WEBDAV_BASE + path

    def move_folder(self, src_folder_path, dst_folder_path):
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
            self.ensure_folder(dst_parent)

        # Vollständige WebDAV-URLs aufbauen
        src_url = self.join_webdav_path("/" + src_folder_path)
        dst_url = self.join_webdav_path("/" + dst_folder_path)

        # MOVE per WebDAV
        with requests.Session() as s:
            s.auth = (self.USERNAME, self.APP_PASS)
            headers = {
                "Destination": dst_url,
                "Overwrite": "T" # überschreiben, falls Ziel schon existiert
            }
            resp = s.request("MOVE", src_url, headers=headers, verify=self.VERIFY_TLS)

            # Gängige "OK"-Statuscodes: 201 Created, 204 No Content
            if resp.status_code not in (201, 204):
                frappe.log_error("status_code: {0}\nError: {1}\nsrc_url: {2}\ndst_url: {3}".format(resp.status_code, resp.text, src_url, dst_url))
                resp.raise_for_status()

    def upload_files(self, folder_path, files):
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
        self.ensure_folder(folder_path)

        uploaded = []

        with requests.Session() as s:
            s.auth = (self.USERNAME, self.APP_PASS)

            for filename, file_bytes in files:
                mime_type, _ = mimetypes.guess_type(filename)
                mime_type = mime_type or "application/octet-stream"

                remote_path = posixpath.join("/", folder_path, filename)
                url = self.join_webdav_path(remote_path)
                print("URL: ", url)
                resp = s.put(
                    url,
                    data=file_bytes,
                    headers={"Content-Type": mime_type},
                    verify=self.VERIFY_TLS
                )
                print("resp: ", str(resp))
                if resp.status_code not in (200, 201, 204):
                    resp.raise_for_status()
                
                file_id = self.get_nextcloud_file_id(remote_path)
                file_url = self.get_nextcloud_ui_url(file_id) if file_id else None

                uploaded.append({
                    "filename": filename,
                    "remote_path": remote_path,
                    "file_id": file_id,
                    "file_url": file_url,
                })
        return uploaded
    
    def delete_file(self, remote_path):
        remote_path = "/" + remote_path.strip("/")
        url = self.join_webdav_path(remote_path)

        with requests.Session() as s:
            s.auth = (self.USERNAME, self.APP_PASS)

            resp = s.delete(url, verify=self.VERIFY_TLS)

            if resp.status_code not in (204, 200, 404):
                resp.raise_for_status()

        return
    
    def get_nextcloud_file_id(self, remote_path):
        url = self.join_webdav_path(remote_path)

        body = """<?xml version="1.0"?>
<d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
  <d:prop>
    <oc:fileid/>
  </d:prop>
</d:propfind>
"""

        resp = requests.request(
            "PROPFIND",
            url,
            auth=(self.USERNAME, self.APP_PASS),
            headers={
                "Depth": "0",
                "Content-Type": "application/xml",
            },
            data=body,
            verify=self.VERIFY_TLS,
        )
        resp.raise_for_status()

        ns = {
            "d": "DAV:",
            "oc": "http://owncloud.org/ns",
        }

        root = ET.fromstring(resp.text)
        node = root.find(".//oc:fileid", ns)
        return node.text if node is not None else None


    def get_nextcloud_ui_url(self, file_id):
        return "{}/f/{}".format(self.BASE_ORIGIN.rstrip("/"), file_id)
        
    def format_bytes(self, size):
        if not isinstance(size, int):
            return "0 KB"
        
        kb = 1024
        mb = 1024 * 1024
        gb = 1024 * 1024 * 1024

        if size < mb:
            return "{:.2f} KB".format(size / kb)
        elif size < 100 * mb:
            return "{:.2f} MB".format(size / mb)
        else:
            return "{:.2f} GB".format(size / gb)

# ----------------------------------------
# ---------- Funktions-Methoden ----------
# ----------------------------------------
def new_mitgliedschaft(mitglied):
    # Initialisiere globale Settings-Klasse
    sektion = mitglied.sektion_id
    # global ncs
    ncs = NCSettings(sektion)

    # DoNothing wenn NextCloud in der Sektion deaktiviert
    if not ncs.IS_ENABLED:
        return
    
    # Erstelle Sektions-Mitgliedschafts-Oder falls nicht vorhanden
    if mitglied.mitglied_nr and mitglied.mitglied_nr != "MV":
        try:
            ncs.ensure_folder("{0}/{1}".format(ncs.BASE_MITGLIED, mitglied.mitglied_nr))
        except Exception as err:
            frappe.log_error(str(err), "NextCloud: new_mitgliedschaft > ensure_folder")

def new_beratung(beratung):
    # Initialisiere globale Settings-Klasse
    sektion = beratung.sektion_id
    # global ncs
    ncs = NCSettings(sektion)

    # DoNothing wenn NextCloud in der Sektion deaktiviert
    if not ncs.IS_ENABLED:
        return
    
    mitglied_nr = None
    if beratung.mv_mitgliedschaft:
        mitglied_nr = frappe.db.get_value("Mitgliedschaft", beratung.mv_mitgliedschaft, "mitglied_nr")
    
    if mitglied_nr and mitglied_nr != "MV":
        # Erstelle Sektions-Mitgliedschafts-Beratungs-Ordner (& Basis Ordner falls nicht vorhanden)
        try:
            base_mitglied_beratung = ncs.BASE_MITGLIED_BERATUNG.replace("<platzhalter>", mitglied_nr)
            ncs.ensure_folder("{0}/{1}".format(base_mitglied_beratung, beratung.name))
            # ensure_folder("{0}/{1}/{2}".format(ncs.BASE_MITGLIED, mitglied_nr, beratung.name))
        except Exception as err:
            frappe.log_error(str(err), "NextCloud: new_beratung > ensure_folder (mit Mitglied)")
    else:
        # Erstelle Sektions-Beratungs-Ordner (& Basis Ordner falls nicht vorhanden)
        try:
            ncs.ensure_folder("{0}/{1}".format(ncs.BASE_BERATUNG, beratung.name))
        except Exception as err:
            frappe.log_error(str(err), "NextCloud: new_beratung > ensure_folder (ohne Mitglied)")

def added_mitglied_to_beratung(beratung):
    # Initialisiere globale Settings-Klasse
    sektion = beratung.sektion_id
    # global ncs
    ncs = NCSettings(sektion)

    # DoNothing wenn NextCloud in der Sektion deaktiviert
    if not ncs.IS_ENABLED:
        return
    
    if beratung.mv_mitgliedschaft:
        mitglied_nr = frappe.db.get_value("Mitgliedschaft", beratung.mv_mitgliedschaft, "mitglied_nr")
        if mitglied_nr and mitglied_nr != "MV":
            # Verschiebe Sektions-Beratungs-Oder zu Sektions-Mitgliedschafts-Beratungs-Oder (wird erstellt wenn nicht vorhanden)
            try:
                base_mitglied_beratung = ncs.BASE_MITGLIED_BERATUNG.replace("<platzhalter>", mitglied_nr)
                ncs.move_folder("{0}/{1}".format(ncs.BASE_BERATUNG, beratung.name), "{0}/{1}".format(base_mitglied_beratung, beratung.name))
            except Exception as err:
                frappe.log_error(str(err), "NextCloud: added_mitglied_to_beratung > move_folder")

def changed_mitglied_in_beratung(beratung, old_id, new_id):
    # Initialisiere globale Settings-Klasse
    sektion = beratung.sektion_id
    # global ncs
    ncs = NCSettings(sektion)

    # DoNothing wenn NextCloud in der Sektion deaktiviert
    if not ncs.IS_ENABLED:
        return
    
    old_mitglied_nr = frappe.db.get_value("Mitgliedschaft", old_id, "mitglied_nr")
    new_mitglied_nr = frappe.db.get_value("Mitgliedschaft", new_id, "mitglied_nr")
    if new_mitglied_nr and new_mitglied_nr != "MV":
        # Verschiebe Sektions-Beratungs-Oder zu Sektions-Mitgliedschafts-Beratungs-Oder (wird erstellt wenn nicht vorhanden)
        try:
            old_base_mitglied_beratung = ncs.BASE_MITGLIED_BERATUNG.replace("<platzhalter>", old_mitglied_nr)
            new_base_mitglied_beratung = ncs.BASE_MITGLIED_BERATUNG.replace("<platzhalter>", new_mitglied_nr)
            ncs.move_folder("{0}/{1}".format(old_base_mitglied_beratung, beratung.name), "{0}/{1}".format(new_base_mitglied_beratung, beratung.name))
        except Exception as err:
            frappe.log_error(str(err), "NextCloud: changed_mitglied_in_beratung > move_folder")



"""
    Diese Mthode liefert einen rekursiven Baum aller Unterordner & Dateien unterhalb vom root_folder_path
    Soll nicht für die frappe-Tree-View genutzt werden, da dafür die nachfolgende Lazy-Children-Methode (list_children_tree) angedacht ist
"""
@frappe.whitelist()
def list_all_files_tree(sektion=None, mitglied=None):
    """
    Beispiel Ordner:
        {
            'type': 'folder',
            'name': 'YYY',
            'path': '/XXX/YYY/MV0000001/',
            'children': []
        }
    Beispiel File:
        {
            'type': 'file',
            'name': 'Example.md',
            'size': 1095,
            'fileid': '315'
        }
    """
    # Initialisiere Settings-Klasse
    if mitglied and not sektion:
        sektion = frappe.db.get_value("Mitgliedschaft", mitglied, "sektion_id") or None
    
    if not sektion:
        return
    
    ncs = NCSettings(sektion)

    # DoNothing wenn NextCloud in der Sektion deaktiviert
    if not ncs.IS_ENABLED:
        return
    
    root_folder_path = '{0}'.format(ncs.BASE_SEKTION)
    if mitglied:
        root_folder_path = '{0}/{1}'.format(ncs.BASE_MITGLIED, frappe.db.get_value("Mitgliedschaft", mitglied, "mitglied_nr"))
    
    root_folder_path = (root_folder_path or "").strip("/")
    start_path = "/" + root_folder_path if root_folder_path else "/"

    # Schutz gegen Loops
    visited = set()

    def _propfind_children(session, folder_abs_path):
        """
        PROPFIND Depth:1 auf folder_abs_path (absolut, beginnt mit '/')
        Liefert Liste von Items (direkte Children, ohne den Ordner selbst)
        """
        url = ncs.join_webdav_path(folder_abs_path)

        body = """<?xml version="1.0"?>
<d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
  <d:prop>
    <d:resourcetype/>
    <d:getcontentlength/>
    <d:getcontenttype/>
    <d:getlastmodified/>
    <d:getetag/>
    <oc:fileid/>
  </d:prop>
</d:propfind>
"""
        resp = session.request(
            "PROPFIND",
            url,
            headers={"Depth": "1"},
            data=body.encode("utf-8"),
            verify=ncs.VERIFY_TLS
        )

        if resp.status_code != 207:
            frappe.log_error(
                "status_code: {status_code}\nError: {text}\nurl: {url}".format(status_code=resp.status_code, text=resp.text, url=url),
                "NextCloud: list_all_files_tree > PROPFIND"
            )
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        responses = root.findall("d:response", ncs.DAV_NS)

        items = []

        # Die erste response ist üblicherweise der Ordner selbst -> skip
        for r in responses[1:]:
            href_el = r.find("d:href", ncs.DAV_NS)
            if href_el is None or not href_el.text:
                continue

            href = href_el.text

            # href enthält /remote.php/dav/files/<user>/...
            marker = "/remote.php/dav/files/{user}".format(user=urlparse.quote(ncs.USERNAME))
            idx = href.find(marker)
            if idx >= 0:
                # beginnt mit /
                rel = href[idx + len(marker):]
            else:
                rel = href

            rel = urlparse.unquote(rel)
            if not rel.startswith("/"):
                rel = "/" + rel

            prop = r.find("d:propstat/d:prop", ncs.DAV_NS)
            if prop is None:
                continue

            rt = prop.find("d:resourcetype", ncs.DAV_NS)
            is_dir = (rt is not None and rt.find("d:collection", ncs.DAV_NS) is not None)

            size = prop.findtext("d:getcontentlength", default=None, namespaces=ncs.DAV_NS)
            ctype = prop.findtext("d:getcontenttype", default=None, namespaces=ncs.DAV_NS)
            etag = prop.findtext("d:getetag", default=None, namespaces=ncs.DAV_NS)
            lm = prop.findtext("d:getlastmodified", default=None, namespaces=ncs.DAV_NS)
            fileid = prop.findtext("oc:fileid", default=None, namespaces=ncs.DAV_NS)

            try:
                size_int = int(size) if (size is not None and str(size).strip() != "") else None
            except Exception:
                size_int = None

            items.append({
                "path": rel,
                "name": posixpath.basename(rel.rstrip("/")),
                "is_dir": is_dir,
                "size": ncs.format_bytes(size_int),
                "content_type": ctype,
                "etag": etag,
                "last_modified": lm,
                "fileid": fileid
            })

        return items

    def _build_node_for_folder(session, folder_abs_path):
        """
        Baut Folder-Node inkl. rekursiven children[]
        """
        folder_abs_path = folder_abs_path.rstrip("/") or "/"

        if folder_abs_path in visited:
            # Loop-Schutz: bereits besucht -> leeren Ordner zurückgeben
            return {
                "type": "folder",
                "name": posixpath.basename(folder_abs_path.rstrip("/")) if folder_abs_path != "/" else "",
                "path": folder_abs_path,
                "children": []
            }
        visited.add(folder_abs_path)

        node = {
            "type": "folder",
            "name": posixpath.basename(folder_abs_path.rstrip("/")) if folder_abs_path != "/" else "",
            "path": folder_abs_path,
            "children": []
        }

        children = _propfind_children(session, folder_abs_path)

        # sortieren (erst Ordner, dann Files (alphabetisch))
        children.sort(key=lambda x: (0 if x["is_dir"] else 1, (x["name"] or "").lower()))

        for item in children:
            if item["is_dir"]:
                child_folder_path = item["path"].rstrip("/") or "/"
                child_node = _build_node_for_folder(session, child_folder_path)
                # sicherstellen, dass Name/Path stimmen (falls Nextcloud mal komisch liefert)
                child_node["name"] = item["name"] or child_node.get("name")
                child_node["path"] = item["path"]
                node["children"].append(child_node)
            else:
                node["children"].append({
                    "type": "file",
                    "name": item["name"],
                    "path": item["path"],
                    "size": item["size"],
                    "content_type": item["content_type"],
                    "etag": item["etag"],
                    "last_modified": item["last_modified"],
                    "fileid": item["fileid"]
                })

        return node

    with requests.Session() as s:
        s.auth = (ncs.USERNAME, ncs.APP_PASS)
        return _build_node_for_folder(s, start_path)

@frappe.whitelist()
def list_children_tree(sektion=None, mitglied=None, parent=None, parent_path=None, **kwargs):
    """
    Lazy-Loader für frappe.ui.Tree
    Liefert direkte Children (Depth:1) eines Ordners als Tree-Nodes
    parent_path: absoluter Pfad ab root (z.B. "/MVZH/Mitglieder/12345")
    """

    # Sektion ermitteln
    if mitglied and not sektion:
        sektion = frappe.db.get_value("Mitgliedschaft", mitglied, "sektion_id") or None
    
    if not sektion:
        return

    # Settings
    ncs = NCSettings(sektion)

    # DoNothing wenn NextCloud in der Sektion deaktiviert
    if not ncs.IS_ENABLED:
        return

    # Root Pfad ermitteln
    root_folder_path = ncs.BASE_SEKTION
    if mitglied:
        root_folder_path = '{0}/{1}'.format(
            (ncs.BASE_MITGLIED or "").strip("/"),
            frappe.db.get_value("Mitgliedschaft", mitglied, "mitglied_nr")
        )

    root_folder_path = (root_folder_path or "").strip("/")
    start_path = "/" + root_folder_path if root_folder_path else "/"

    # Sub-Ordner Pfad ermitteln für Lazy-Load
    if parent in (None, "", "Files") and not parent_path:
        folder_abs_path = start_path
    else:
        folder_abs_path = (parent_path or parent or start_path or "/").strip()

    # normalisieren
    if not folder_abs_path.startswith("/"):
        folder_abs_path = "/" + folder_abs_path
    folder_abs_path = folder_abs_path.rstrip("/") or "/"
    
    def _propfind_children(session, folder_abs_path):
        url = ncs.join_webdav_path(folder_abs_path)

        body = """<?xml version="1.0"?>
<d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
  <d:prop>
    <d:resourcetype/>
    <d:getcontentlength/>
    <d:getcontenttype/>
    <d:getlastmodified/>
    <d:getetag/>
    <oc:fileid/>
  </d:prop>
</d:propfind>
"""
        resp = session.request(
            "PROPFIND",
            url,
            headers={"Depth": "1"},
            data=body.encode("utf-8"),
            verify=ncs.VERIFY_TLS
        )

        if resp.status_code != 207:
            frappe.log_error(
                "status_code: {status_code}\nError: {text}\nurl: {url}".format(
                    status_code=resp.status_code, text=resp.text, url=url
                ),
                "NextCloud: list_children_tree > PROPFIND"
            )
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        responses = root.findall("d:response", ncs.DAV_NS)

        items = []

        # erste response ist der Ordner selbst -> skip
        for r in responses[1:]:
            href_el = r.find("d:href", ncs.DAV_NS)
            if href_el is None or not href_el.text:
                continue

            href = href_el.text

            marker = "/remote.php/dav/files/{user}".format(user=urlparse.quote(ncs.USERNAME))
            idx = href.find(marker)
            if idx >= 0:
                rel = href[idx + len(marker):]
            else:
                rel = href

            rel = urlparse.unquote(rel)
            if not rel.startswith("/"):
                rel = "/" + rel

            prop = r.find("d:propstat/d:prop", ncs.DAV_NS)
            if prop is None:
                continue

            rt = prop.find("d:resourcetype", ncs.DAV_NS)
            is_dir = (rt is not None and rt.find("d:collection", ncs.DAV_NS) is not None)

            size = prop.findtext("d:getcontentlength", default=None, namespaces=ncs.DAV_NS)
            ctype = prop.findtext("d:getcontenttype", default=None, namespaces=ncs.DAV_NS)
            etag = prop.findtext("d:getetag", default=None, namespaces=ncs.DAV_NS)
            lm = prop.findtext("d:getlastmodified", default=None, namespaces=ncs.DAV_NS)
            fileid = prop.findtext("oc:fileid", default=None, namespaces=ncs.DAV_NS)

            try:
                size_int = int(size) if (size is not None and str(size).strip() != "") else None
            except Exception:
                size_int = None
            
            items.append({
                "path": rel.rstrip("/") if is_dir else rel,
                "name": posixpath.basename(rel.rstrip("/")),
                "is_dir": is_dir,
                "size": ncs.format_bytes(size_int),
                "content_type": ctype,
                "etag": etag,
                "last_modified": lm,
                "fileid": fileid,
                "nc_link": "{0}/apps/files/files/{1}?dir={2}".format(ncs.BASE_ORIGIN, urlparse.quote(str(fileid)), urlparse.quote(folder_abs_path))
            })

        return items

    with requests.Session() as s:
        s.auth = (ncs.USERNAME, ncs.APP_PASS)

        try:
            children = _propfind_children(s, folder_abs_path)
        except requests.exceptions.HTTPError:
            return []
        
        # sortieren: Ordner zuerst, dann Files
        children.sort(key=lambda x: (0 if x["is_dir"] else 1, (x["name"] or "").lower()))

        # WICHTIG: Tree braucht LISTE von Nodes (nicht root dict)
        nodes = []
        for item in children:
            if item["is_dir"]:
                d = {
                    "type": "folder",
                    "name": item["name"],
                    "path": item["path"],
                    "nc_link": item["nc_link"]
                }
                nodes.append({
                    "label": item["name"],
                    "title": item["name"],
                    "value": item["size"],
                    "expandable": True,
                    "children": [],
                    "data": d
                })
            else:
                d = {
                    "type": "file",
                    "name": item["name"],
                    "path": item["path"],
                    "size": item["size"],
                    "content_type": item["content_type"],
                    "etag": item["etag"],
                    "last_modified": item["last_modified"],
                    "fileid": item["fileid"],
                    "nc_link": item["nc_link"]
                }
                nodes.append({
                    "label": item["name"],
                    "title": item["name"],
                    "value": item["size"],
                    "expandable": False,
                    "children": [],
                    "data": d
                })

        return nodes
