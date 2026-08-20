# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint
from frappe.utils.data import today, formatdate
from frappe.utils.background_jobs import enqueue
import os
import zipfile
from urllib.parse import unquote
from mvd.mvd.doctype.druckvorlage.druckvorlage import get_doc_from_ctx
from html import escape
try:
    from jinja2 import pass_context as context_decorator
except ImportError:
    from jinja2 import contextfunction as context_decorator
from jinja2.runtime import Context

class RSVMitglied(Document):
    def autoname(self):
        if self.mv_mitgliedschaft:
            vorname = self.vorname if self.vorname else frappe.db.get_value("Mitgliedschaft", self.mv_mitgliedschaft, "vorname_1")
            nachname = self.nachname if self.nachname else frappe.db.get_value("Mitgliedschaft", self.mv_mitgliedschaft, "nachname_1")
            mitgl_nr = self.mitglied_nr if self.mitglied_nr else frappe.db.get_value("Mitgliedschaft", self.mv_mitgliedschaft, "mitglied_nr")
        elif self.faktura_kunde:
            vorname = frappe.db.get_value("Kunden", self.faktura_kunde, "vorname")
            nachname = frappe.db.get_value("Kunden", self.faktura_kunde, "nachname")
            mitgl_nr = self.faktura_kunde
        
        new_name = "{0}_{1}_{2}_{3}".format(formatdate(today(), "yy-MM-dd"), mitgl_nr, vorname, nachname)

        if frappe.db.exists("RSVMitglied", new_name):
            counter = frappe.db.sql(
                """
                    SELECT COUNT(`name`) AS `qty` FROM `tabRSVMitglied` WHERE `name` LIKE '{0}%'
                """.format(new_name),
                as_dict=True
            )[0].qty

            new_name = "{0}-{1}".format(new_name, counter)
        
        self.name = new_name
    
    def validate(self):
        if self.faktura_kunde:
            self.faktura_kunde_name = "{0} {1}".format(frappe.db.get_value("Kunden", self.faktura_kunde, "vorname"), frappe.db.get_value("Kunden", self.faktura_kunde, "nachname"))
        else:
            self.faktura_kunde_name = None

        if self.rsvmandat:
            self.fetch_rsv_mandat_themen()
        
        self.fetch_document_table()

        if self.status == 'Geprüft':
            self.datum_pruefung = today()
    
    def after_insert(self):
        if not self.adr_egaid:
            gebaeudeverzeichnis_id_and_bfs_nr = get_gebaeudeverzeichnis_id(hausnummer=self.hausnummer, nr_zusatz=self.nr_zusatz, strasse=self.strasse, plz=self.plz, ort=self.ort)
            if gebaeudeverzeichnis_id_and_bfs_nr is not None:
                self.adr_egaid = gebaeudeverzeichnis_id_and_bfs_nr.get("adr_egaid")
                self.bfs_nr = gebaeudeverzeichnis_id_and_bfs_nr.get("bfs_nr")
            else:
                self.reason_missing_rsvmandat = "Auf Basis der Adressdaten konnte keine Gebäude ID zugeordnet werden.<br>Ein entsprechendes RSV-Mandat muss manuell angelegt und verknüpft werden."
        
        if not cint(self.mandat_und_siedlungs_sperre) == 1:
            if not self.rsvmandat and self.adr_egaid:
                self.rsvmandat = self.get_gruppenmandat(force_new_rsvmandat=cint(self.force_new_rsvmandat))
        else:
            # Keine autom. RSV-Mandat- und Siedlungsanlage durch after_insert.
            # Wird autom. wieder entfernt, da es nach after_insert keinen Nutzen mehr hat.
            self.mandat_und_siedlungs_sperre = 0
            self.reason_missing_rsvmandat = "Die allfällige autom. RSV-Mandat- sowie Siedlungsanlage wurde gesperrt. Diese müssen ggf. manuell angelegt und verknüpft werden."
        
        self.save()
    
    def on_update(self):
        if self.rsvmandat:
            self.reason_missing_rsvmandat = None
        
        if self.rsvmandat:
            args = {
                'rsvmitglied': self.name,
                'rsvmandat': self.rsvmandat
            }
            enqueue("mvd.mvd.doctype.rsvmandat.rsvmandat.update_rsvmandat", queue='short', job_name='Update {0}'.format(self.rsvmandat), timeout=5000, **args)

        if self.mv_mitgliedschaft:
            args = {
                'mitglied': self.mv_mitgliedschaft
            }
            enqueue("mvd.mvd.doctype.siedlungsfall.siedlungsfall.update_mitglied_in_siedlungsfall", queue='short', job_name='Update {0} in Siedlungsfall'.format(self.mv_mitgliedschaft), timeout=5000, **args)

    def fetch_rsv_mandat_themen(self):
        rsvmandat = frappe.get_doc("RSVMandat", self.rsvmandat)
        already_added_themen = []
        self.thema = []

        for thema in rsvmandat.thema:
            if thema.thema and thema.thema not in already_added_themen:
                self.append("thema", {'thema': thema.thema})
                already_added_themen.append(thema.thema)
    
    def fetch_document_table(self):
        fetched_documents = []
        if len(self.dokumente) > 0:
            for document in self.dokumente:
                fetched_documents.append(document.dokument)
        
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
                    # if document.dokument == 'Schadenanzeige':
                    #     attachments = frappe.db.sql(
                    #         """
                    #             SELECT `file_url`, `file_name`
                    #             FROM `tabFile`
                    #             WHERE `attached_to_doctype` = 'RSVMitglied'
                    #             AND `attached_to_name` = '{0}'
                    #             LIMIT 1
                    #         """.format(self.name),
                    #         as_dict=True
                    #     )
                    #     if len(attachments) > 0:
                    #         for attachment in attachments:
                    #             if "Schadenanzeige" in attachment.file_name and "{0}".format(self.name) in attachment.file_name:
                    #                 doc_row.file_upload = attachment.file_url
    
    def get_mietvertrag_pfad(self):
        mietvertrag_pfad = frappe.db.sql(
            """
                SELECT `bd`.`file` AS `mietvertrag_pfad`
                FROM `tabBeratung` AS `b`
                LEFT JOIN `tabBeratungsdateien` AS `bd` ON `b`.`name` = `bd`.`parent`
                WHERE `b`.`rsv_mitglied` = '{0}'
                AND `bd`.`document_type` = 'Mietvertrag'
            """.format(self.name),
            as_dict=True
        )
        if len(mietvertrag_pfad) < 1: return None

        return mietvertrag_pfad[0].mietvertrag_pfad
    
    def get_gruppenmandat(self, force_new_rsvmandat=0, for_lookup=False):
        siedlung = get_siedlung(self.adr_egaid)
        if siedlung:
            rsvmandat = get_gruppenmandat_based_on_siedlung(siedlung, force_new_rsvmandat=force_new_rsvmandat, for_lookup=for_lookup)
            if for_lookup:
                return rsvmandat
            if rsvmandat.get("qty") in [0, 1]:
                return rsvmandat.get("rsvmandat")
            else:
                self.reason_missing_rsvmandat = "Auf Basis der zutreffenden Siedlung gibt es mehrere RSV-Mandate. Bitte wählen Sie das zugehörige manuell aus."
        else:
            if for_lookup:
                return "Keine Siedlung gefunden"
            self.reason_missing_rsvmandat = "Auf Basis der Adressdaten konnte keine Siedlung zugeordnet werden.<br>Eine entsprechendes RSV-Mandat muss manuell angelegt und verknüpft werden."
        
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
    
    def open_beratung(self):
        beratung = frappe.db.sql(
            """
                SELECT `name` FROM `tabBeratung`
                WHERE `rsv_mitglied` = '{0}'
            """.format(self.name),
            as_dict=True
        )

        if len(beratung) < 1:
            frappe.throw("Es wurde keine zugehörige Beratung gefunden.")
        
        return beratung[0].name
    
    def get_or_create_rsv_mandat(self, force_new_rsvmandat=0, for_lookup=False):
        return self.get_gruppenmandat(force_new_rsvmandat=force_new_rsvmandat, for_lookup=for_lookup)


def resolve_file_path(file_url):
    file_url = unquote(file_url)

    if file_url.startswith("/private/files/"):
        filename = file_url.replace("/private/files/", "", 1)
        return frappe.get_site_path("private", "files", filename)

    if file_url.startswith("/files/"):
        filename = file_url.replace("/files/", "", 1)
        return frappe.get_site_path("public", "files", filename)

    frappe.error_log("RSVMitglied: ZIP CreationUnsupported file_url: {0}".format(file_url), "RSVMitglied: ZIP Creation")
    return None


def create_zip_and_attach(file_urls, doctype, docname, zip_name="documents.zip"):
    zip_path = frappe.get_site_path("private", "files", zip_name)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_url in file_urls:
            file_path = resolve_file_path(file_url)

            if not os.path.exists(file_path):
                frappe.error_log("File not found: {0}".format(file_url), "RSVMitglied: ZIP Creation")
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

def get_gruppenmandat_based_on_siedlung(siedlung, force_new_rsvmandat=0, for_lookup=False):
    def create_gruppenmandat_based_on_siedlung(siedlung):
        new_rsvmandat = frappe.new_doc('RSVMandat')
        new_rsvmandat.siedlung = siedlung
        new_rsvmandat.insert()
        return new_rsvmandat.name
    
    if force_new_rsvmandat == 1:
        return {
            'qty': 0,
            'rsvmandat': create_gruppenmandat_based_on_siedlung(siedlung)
        }
    
    query = """
        SELECT `name`
        FROM `tabRSVMandat`
        WHERE `siedlung` = '{0}'
    """.format(siedlung)

    rsvmandat = frappe.db.sql(query, as_dict=True)
    if len(rsvmandat) < 1:
        if for_lookup:
            return {
                'qty': 0
            }
        return {
            'qty': 0,
            'rsvmandat': create_gruppenmandat_based_on_siedlung(siedlung)
        }
    else:
        return {
            'qty': len(rsvmandat),
            'rsvmandat': rsvmandat[0].name if len(rsvmandat) == 1 else rsvmandat
        }

@frappe.whitelist()
def check_for_existing_rsvmandat(**kwargs):
    rsvmandat = None
    gebaeudeverzeichnis_id_and_bfs_nr = get_gebaeudeverzeichnis_id(hausnummer=kwargs.get("hausnummer", None), nr_zusatz=kwargs.get("nr_zusatz", None), strasse=kwargs.get("strasse", None), plz=kwargs.get("plz", None), ort=kwargs.get("ort", None))
    if gebaeudeverzeichnis_id_and_bfs_nr is not None:
        adr_egaid = gebaeudeverzeichnis_id_and_bfs_nr.get("adr_egaid")
        siedlung = get_siedlung(adr_egaid, no_auto_creation=True)
        if siedlung:
            rsvmandat = get_gruppenmandat_based_on_siedlung(siedlung)
    
    if rsvmandat:
        return siedlung
    
    return rsvmandat

@frappe.whitelist()
def create_rsv_mitglied(**kwargs):
    rsv_mitglied = frappe.new_doc("RSVMitglied")
    rsv_mitglied.strasse = kwargs.get("strasse", None)
    rsv_mitglied.hausnummer = kwargs.get("hausnummer", None)
    rsv_mitglied.nr_zusatz = kwargs.get("nr_zusatz", None)
    rsv_mitglied.plz = kwargs.get("plz", None)
    rsv_mitglied.ort = kwargs.get("ort", None)
    rsv_mitglied.mv_mitgliedschaft = kwargs.get("mv_mitgliedschaft", None)
    rsv_mitglied.faktura_kunde = kwargs.get("faktura_kunde", None)

    if kwargs.get("rsv_mandat", None):
        rsv_mitglied.rsvmandat = kwargs.get("rsv_mandat", None)
    
    if kwargs.get("rsv_mandat_new_creation", None):
        if cint(kwargs.get("rsv_mandat_new_creation", None)) == 1:
            rsv_mitglied.force_new_rsvmandat = 1
            rsv_mitglied.rsvmandat = None
    
    if kwargs.get("mandat_und_siedlungs_sperre", None):
        if cint(kwargs.get("mandat_und_siedlungs_sperre", None)) == 1:
            rsv_mitglied.mandat_und_siedlungs_sperre = 1
    
    if kwargs.get("mandat_typ", None):
        rsv_mitglied.status = kwargs.get("mandat_typ", None)

    rsv_mitglied.insert()
    return rsv_mitglied.name

### Jinja-Methoden für die RSV-Mandat E-Mails ###
@context_decorator
def rsv_dokumente_fehlende(ctx):
    doc = get_doc_from_ctx(ctx)
    if doc.get("doctype") == "RSVMitglied":
        if doc.dokumente:
            document_list_html = ""
            for document in doc.dokumente:
                if cint(document.formal_gepr) != 1:
                    document_list_html += "- {0}<br>".format(document.dokument)
            return document_list_html
    
    return '---'

@context_decorator
def rsv_dokumente_erhalten(ctx):
    doc = get_doc_from_ctx(ctx)
    if doc.get("doctype") == "RSVMitglied":
        if doc.dokumente:
            document_list_html = ""
            for document in doc.dokumente:
                if cint(document.formal_gepr) == 1:
                    document_list_html += "- {0}<br>".format(document.dokument)
            return document_list_html
    
    return '---'

@frappe.whitelist()
def get_siedlungs_adressen_html(adr_egaid):
    adr = frappe.get_doc("Amtliches Gebaeudeverzeichnis", adr_egaid)
    data = {
        'strasse': adr.stn_label,
        'nummer': adr.adr_number,
        'plz': adr.plz,
        'ort': adr.wohnort
    }
    return frappe.render_template('templates/includes/siedlungsadresse.html', data)

# ---------------------------------------------------------------------------
# (Hilfs-) Methoden für die HTML Darstellung der Informationen aus RSV-Mandat
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_rsv_mandat_html(rsv_mandat):
    fieldlist = [
        'typ',
        'bezeichnung',
        'siedlung',
        'schlichtungsbehoerde',
        'vermieterin',
        'verwaltung',
        {
            'fieldname': 'thema',
            'value_field': 'thema'
        },
        {
            'fieldname': 'sprachen',
            'value_field': 'sprache'
        },
        'publikation_per',
        'frist',
        'verhandlungsdatum',
        'fallnummer',
        'kurzbeschrieb',
        'notizen'
    ]
    
    return get_field_values_html("RSVMandat", rsv_mandat, fieldlist)

def get_field_values_html(doctype, docname, fieldlist):
    """
    Erstellt eine HTML-Darstellung ausgewählter Felder eines Frappe-Dokuments.

    fieldlist Beispiele:

        [
            "first_name",
            "last_name",
            "email"
        ]

    oder gemischt:

        [
            "first_name",
            "last_name",
            {
                "fieldname": "languages",
                "value_field": "language"
            },
            {
                "fieldname": "customer_group",
                "label": "Kundengruppe"
            }
        ]

    Unterstützt u.a.:
    - Data
    - Link
    - Select
    - Date
    - Datetime
    - Currency
    - Float
    - Int
    - Check
    - Text / Small Text / Long Text
    - Table MultiSelect
    """

    doc = frappe.get_doc(doctype, docname)
    meta = frappe.get_meta(doctype)

    rows = []

    for field_config in fieldlist:
        config = normalize_field_config(field_config)

        fieldname = config["fieldname"]
        df = meta.get_field(fieldname)

        if not df:
            continue

        label = config.get("label") or df.label or fieldname

        value = get_field_value_html(
            doc=doc,
            df=df,
            config=config
        )

        if not value:
            continue

        rows.append(
            """
            <div style="
                display: flex;
                padding: 6px 0;
                border-bottom: 1px solid #e5e5e5;
            ">
                <div style="
                    width: 35%;
                    font-weight: 600;
                    padding-right: 15px;
                    box-sizing: border-box;
                ">
                    {label}
                </div>
                <div style="
                    width: 65%;
                    box-sizing: border-box;
                ">
                    {value}
                </div>
            </div>
            """.format(
                label=escape(str(label)),
                value=value
            )
        )

    return """
        <div style="
            width: 100%;
            font-size: 13px;
            line-height: 1.4;
        ">
            {rows}
        </div>
    """.format(
        rows="".join(rows)
    )


def normalize_field_config(field_config):
    # Vereinheitlichung der field_config aka field_list

    if isinstance(field_config, str):
        return {
            "fieldname": field_config
        }

    if isinstance(field_config, dict):
        if not field_config.get("fieldname"):
            frappe.throw("fieldname fehlt in fieldlist-Konfiguration.")

        return field_config

    frappe.throw(
        "Ungültiger Eintrag in fieldlist: {0}".format(field_config)
    )


def get_field_value_html(doc, df, config):
    if df.fieldtype == "Table MultiSelect":
        return get_table_multiselect_html(
            doc=doc,
            df=df,
            config=config
        )

    value = doc.get(df.fieldname)

    if value is None or value == "":
        return False

    if df.fieldtype == "Check":
        return "Ja" if value else "Nein"

    if df.fieldtype in (
        "Text",
        "Small Text",
        "Long Text",
        "Text Editor"
    ):
        return escape(str(value)).replace("\n", "<br>")

    return format_standard_value(
        value=value,
        df=df,
        doc=doc
    )


def format_standard_value(value, df, doc):
    try:
        formatted_value = frappe.format_value(
            value,
            df=df,
            doc=doc
        )
    except Exception:
        formatted_value = value

    if formatted_value is None or formatted_value == "":
        return "-"

    return escape(str(formatted_value))


def get_table_multiselect_html(doc, df, config):
    """
    Formatiert ein Table MultiSelect Feld.

    value_field kann explizit angegeben werden:

        {
            "fieldname": "languages",
            "value_field": "language"
        }

    Falls value_field nicht angegeben wird, wird versucht,
    automatisch das passende Feld im Child-Doctype zu finden.
    """

    child_rows = doc.get(df.fieldname) or []

    if not child_rows:
        return False

    value_fieldname = config.get("value_field")

    child_meta = frappe.get_meta(df.options)

    if not value_fieldname:
        value_fieldname = find_table_multiselect_value_field(child_meta)

    if not value_fieldname:
        return "-"

    child_df = child_meta.get_field(value_fieldname)

    values = []

    for row in child_rows:
        value = row.get(value_fieldname)

        if value is None or value == "":
            continue

        if child_df:
            formatted_value = format_standard_value(
                value=value,
                df=child_df,
                doc=row
            )
        else:
            formatted_value = escape(str(value))

        values.append(formatted_value)

    if not values:
        return "-"

    separator = config.get("separator", ", ")

    return escape(separator).join(values)


def find_table_multiselect_value_field(child_meta):
    """
    Versucht automatisch, das relevante Feld eines Table MultiSelect
    Child-Doctypes zu finden.

    Priorität:
    1. Link
    2. Data
    3. Select
    """

    for fieldtype in ("Link", "Data", "Select"):
        for df in child_meta.fields:
            if df.fieldtype == fieldtype:
                return df.fieldname

    return None