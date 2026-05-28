# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import requests
from frappe.utils import cint
from frappe.utils.background_jobs import enqueue
import os
import zipfile
from urllib.parse import unquote
try:
    from jinja2 import pass_context as context_decorator
except ImportError:
    from jinja2 import contextfunction as context_decorator
from jinja2.runtime import Context
import json

'''
current Working:
- Page für Status-Übersicht von RSVMandat & RSVMandatsliste inkl. Absprung in Liste mit Filter

ToDo bis Do Mittag:
- Button "Fehlende Dokumente Anforderung" -> Macht ein Mail-Dialog mit Template welches alle Fehlenden Dokumente auflistet
- (P2) Mail-In mit Anhang: Anhang autom. als Attachment in RSVMandat
'''

class RSVMandat(Document):
    def validate(self):
        self.fetch_document_table()
    
    def after_insert(self):
        if not self.adr_egaid:
            gebaeudeverzeichnis_id_and_bfs_nr = get_gebaeudeverzeichnis_id(hausnummer=self.hausnummer, nr_zusatz=self.nr_zusatz, strasse=self.strasse, plz=self.plz, ort=self.ort)
            if gebaeudeverzeichnis_id_and_bfs_nr is not None:
                self.adr_egaid = gebaeudeverzeichnis_id_and_bfs_nr.get("adr_egaid")
                self.bfs_nr = gebaeudeverzeichnis_id_and_bfs_nr.get("bfs_nr")
            else:
                self.reason_missing_rsvmandatlist = "Auf Basis der Adressdaten konnte keine Gebäude ID zugeordnet werden.<br>Eine entsprechende Mandatsliste muss manuell angelegt und verknüpft werden."
        
        if not self.schlichtungsbehoerde:
            self.schlichtungsbehoerde = get_schlichtungsbehoerde(self.bfs_nr)
        
        if not self.rsvmandatsliste and self.adr_egaid:
            self.rsvmandatsliste = self.get_gruppenmandat(cint(self.force_new_rsvmandatliste))
        
        self.save()
    
    def on_update(self):
        if self.rsvmandatsliste:
            self.reason_missing_rsvmandatlist = None
        
        if self.rsvmandatsliste:
            args = {
                'rsvmandatsliste': self.rsvmandatsliste
            }
            enqueue("mvd.mvd.doctype.rsvmandatsliste.rsvmandatsliste.reset_status", queue='short', job_name='Update {0} Typ'.format(self.rsvmandatsliste), timeout=5000, **args)
    
    def fetch_document_table(self):
        if len(self.dokumente) < 1:
            fetched_documents = []
            for _thema in self.thema:
                thema = frappe.get_doc("Beratungskategorie", _thema.thema)
                for document in thema.dokumente:
                    if document.dokument not in fetched_documents:
                        fetched_documents.append(document.dokument)
                        doc_row = self.append("dokumente", {})
                        doc_row.dokument = document.dokument
                        if document.dokument == 'Mietvertrag':
                            mietvertrag_pfad = self.get_mietvertrag_pfad()
                            if mietvertrag_pfad:
                                doc_row.file_upload = mietvertrag_pfad
    
    def get_mietvertrag_pfad(self):
        mietvertrag_pfad = frappe.db.sql(
            """
                SELECT `bd`.`file` AS `mietvertrag_pfad`
                FROM `tabBeratung` AS `b`
                LEFT JOIN `tabBeratungsdateien` AS `bd` ON `b`.`name` = `bd`.`parent`
                WHERE `b`.`rsv_mandat` = '{0}'
                AND `bd`.`document_type` = 'Mietvertrag'
            """.format(self.name),
            as_dict=True
        )
        if len(mietvertrag_pfad) < 1: return None

        return mietvertrag_pfad[0].mietvertrag_pfad
    
    def get_gruppenmandat(self, force_new_rsvmandatliste):
        siedlung = get_siedlung(self.adr_egaid)
        if siedlung:
            rsvmandatsliste = get_gruppenmandat_based_on_siedlung(siedlung, force_new_rsvmandatliste)
            if rsvmandatsliste.get("qty") in [0, 1]:
                return rsvmandatsliste.get("rsvmandatsliste")
            else:
                self.reason_missing_rsvmandatlist = "Auf Basis der zutreffenden Siedlung gibt es mehrere Mandatslisten. Bitte wählen Sie die zugehörige manuell aus."
        else:
            self.reason_missing_rsvmandatlist = "Auf Basis der Adressdaten konnte keine Siedlung zugeordnet werden.<br>Eine entsprechende Mandatsliste muss manuell angelegt und verknüpft werden."
        
        return None
    
    def create_zip(self):
        file_urls = []
        for dokument in self.dokumente:
            if dokument.file_upload:
                file_urls.append(dokument.file_upload)
        
        if len(file_urls) > 0:
            zip_url = create_zip_and_attach(
                file_urls=file_urls,
                doctype=self.doctype,
                docname=self.name,
                zip_name="Dokumente_{0}.zip".format(self.name)
            )

def resolve_file_path(file_url):
    file_url = unquote(file_url)

    if file_url.startswith("/private/files/"):
        filename = file_url.replace("/private/files/", "", 1)
        return frappe.get_site_path("private", "files", filename)

    if file_url.startswith("/files/"):
        filename = file_url.replace("/files/", "", 1)
        return frappe.get_site_path("public", "files", filename)

    frappe.error_log("RSVMandat: ZIP CreationUnsupported file_url: {0}".format(file_url), "RSVMandat: ZIP Creation")
    return None


def create_zip_and_attach(file_urls, doctype, docname, zip_name="documents.zip"):
    zip_path = frappe.get_site_path("private", "files", zip_name)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_url in file_urls:
            file_path = resolve_file_path(file_url)

            if not os.path.exists(file_path):
                frappe.error_log("File not found: {0}".format(file_url), "RSVMandat: ZIP Creation")
                continue

            arcname = os.path.basename(file_path)
            zipf.write(file_path, arcname)

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": zip_name,
        "file_url": "/private/files/{0}".format(zip_name),
        "is_private": 1,
        "attached_to_doctype": doctype,
        "attached_to_name": docname
    })

    file_doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return file_doc.file_url

def get_gebaeudeverzeichnis_id(hausnummer=None, nr_zusatz=None, strasse=None, plz=None, ort=None):
    full_number = "{0}{1}".format(hausnummer or "", nr_zusatz or "")
    safe_strasse = str(strasse).replace("'", "''")
    safe_ort = str(ort).replace("'", "''")
    safe_full_number = str(full_number).replace("'", "''")
    sql_result = frappe.db.sql("""SELECT `name`, `com_fosnr`
                        FROM `tabAmtliches Gebaeudeverzeichnis`
                        WHERE `plz` = '{0}'
                        AND `stn_label` = '{1}'
                        AND `adr_number` = '{2}'
                        AND `wohnort` = '{3}'
                        LIMIT 1
                        """.format(plz or '', safe_strasse, safe_full_number, safe_ort), as_dict=True)
    if len(sql_result) > 0:
        return {
            'adr_egaid': sql_result[0].name,
            'bfs_nr': sql_result[0].com_fosnr
        }
    
    return None

def get_schlichtungsbehoerde(bfs_nr):
    # --- EXTERNER API CALL AN MP ---
    api_url = "https://mp.libracore.ch/api/method/mietrechtspraxis.api.get_arbitration_authority_from_bfs"
    try:
        response = requests.get(api_url, params={"bfs_nr": bfs_nr}, timeout=5)
        if response.status_code == 200:
            response_json = response.json()
            aa_data = response_json.get("message") if response_json else None
            
            if aa_data and aa_data.get("titel"):
                return aa_data.get("titel")
        else:
            return None
            
    except Exception as e:
        return None
    
    return None

def get_siedlung(adr_egaid, no_auto_creation=False):
    def create_siedlung(adr_egaid):
        new_siedlung = frappe.new_doc('Siedlung')

        gebaeudeverzeichnis_row = new_siedlung.append('zugehoerige_gebaeude', {})
        gebaeudeverzeichnis_row.adr_egaid = adr_egaid

        new_siedlung.insert()
        return new_siedlung.name
    
    query = """
        SELECT `parent`
        FROM `tabZugehoerige Gebaeude`
        WHERE `adr_egaid` = '{0}'
    """.format(adr_egaid)

    siedlung = frappe.db.sql(query, as_dict=True)
    if len(siedlung) > 0:
        return siedlung[0].parent
    
    if no_auto_creation:
        return None
    
    return create_siedlung(adr_egaid)

def get_gruppenmandat_based_on_siedlung(siedlung, force_new_rsvmandatliste=0):
    def create_gruppenmandat_based_on_siedlung(siedlung):
        new_rsvmandatsliste = frappe.new_doc('RSVMandatsliste')
        new_rsvmandatsliste.siedlung = siedlung
        new_rsvmandatsliste.insert()
        return new_rsvmandatsliste.name
    
    if force_new_rsvmandatliste == 1:
        return {
            'qty': 0,
            'rsvmandatsliste': create_gruppenmandat_based_on_siedlung(siedlung)
        }
    
    query = """
        SELECT `name`
        FROM `tabRSVMandatsliste`
        WHERE `siedlung` = '{0}'
    """.format(siedlung)

    rsvmandatsliste = frappe.db.sql(query, as_dict=True)
    if len(rsvmandatsliste) < 1:
        return {
            'qty': 0,
            'rsvmandatsliste': create_gruppenmandat_based_on_siedlung(siedlung)
        }
    else:
        return {
            'qty': len(rsvmandatsliste),
            'rsvmandatsliste': rsvmandatsliste[0].name if len(rsvmandatsliste) == 1 else rsvmandatsliste
        }

@frappe.whitelist()
def check_for_existing_rsvmandaliste(**kwargs):
    rsvmandatsliste = None
    gebaeudeverzeichnis_id_and_bfs_nr = get_gebaeudeverzeichnis_id(hausnummer=kwargs.get("hausnummer", None), nr_zusatz=kwargs.get("nr_zusatz", None), strasse=kwargs.get("strasse", None), plz=kwargs.get("plz", None), ort=kwargs.get("ort", None))
    if gebaeudeverzeichnis_id_and_bfs_nr is not None:
        adr_egaid = gebaeudeverzeichnis_id_and_bfs_nr.get("adr_egaid")
        siedlung = get_siedlung(adr_egaid, no_auto_creation=True)
        if siedlung:
            rsvmandatsliste = get_gruppenmandat_based_on_siedlung(siedlung)
    
    if rsvmandatsliste:
        return siedlung
    
    return rsvmandatsliste

@frappe.whitelist()
def create_rsv_mandat(**kwargs):
    rsv_mandat = frappe.new_doc("RSVMandat")
    rsv_mandat.strasse = kwargs.get("strasse", None)
    rsv_mandat.hausnummer = kwargs.get("hausnummer", None)
    rsv_mandat.nr_zusatz = kwargs.get("nr_zusatz", None)
    rsv_mandat.plz = kwargs.get("plz", None)
    rsv_mandat.ort = kwargs.get("ort", None)
    rsv_mandat.mv_mitgliedschaft = kwargs.get("mv_mitgliedschaft", None)

    if kwargs.get("rsv_mandatliste", None):
        rsv_mandat.rsvmandatsliste = kwargs.get("rsv_mandatliste", None)
    
    if kwargs.get("rsv_mandatliste_new_creation", None):
        if cint(kwargs.get("rsv_mandatliste_new_creation", None)) == 1:
            rsv_mandat.force_new_rsvmandatliste = 1
            rsv_mandat.rsvmandatsliste = None

    rsv_mandat.insert()
    return rsv_mandat.name

### Jinja-Methoden für die RSV-Mandat E-Mails ###
def get_doc_from_ctx(ctx): 
    if hasattr(ctx, "get") and ctx.get("doc"):
        return ctx.get("doc")
    elif isinstance(ctx, Context): # Falls der ctx vom typ jinja2.context ist -> Email
        doc = json.loads(ctx.get('frappe').get('form_dict').get('doc'))
        return frappe.get_doc(doc.get('doctype'), doc.get('name'))
    return ctx

@context_decorator
def rsv_dokumente_fehlende(ctx):
    doc = get_doc_from_ctx(ctx)
    if doc.get("doctype") == "RSVMandat":
        if doc.dokumente:
            document_list_html = ""
            for document in doc.dokumente:
                if not document.file_upload:
                    document_list_html += "- {0}<br>".format(document.dokument)
            return document_list_html
    
    return '---'

@context_decorator
def rsv_dokumente_erhalten(ctx):
    doc = get_doc_from_ctx(ctx)
    if doc.get("doctype") == "RSVMandat":
        if doc.dokumente:
            document_list_html = ""
            for document in doc.dokumente:
                if document.file_upload:
                    document_list_html += "- {0}<br>".format(document.dokument)
            return document_list_html
    
    return '---'
