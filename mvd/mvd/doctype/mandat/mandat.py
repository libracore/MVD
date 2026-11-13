# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import io
import zipfile
import requests
from six.moves.urllib.parse import quote
import frappe
from frappe.model.document import Document
from frappe.core.doctype.communication.email import make
from frappe import sendmail
from frappe.utils import datetime
from frappe.model.naming import make_autoname
from frappe.email.doctype.email_template.email_template import get_email_template
from frappe.utils.pdf import get_pdf
from frappe import attach_print
from frappe.utils import get_url_to_form, get_url, escape_html, cint, now_datetime, strip_html
from mvd.mvd.doctype.mandat.mandat_status import status_vor_speichern, set_status, RSV, QUELLE_AUTOMATIK

SOLIFONDS_KOSTENDACH = {
    "mangels Rechtsschutzdeckung": 3000,
    "aus ideellen Gründen": 8000
}

SOLIFONDS_KRITERIEN = [
    "kriterium_notlage",
    "kriterium_vermoegenseinbussen",
    "kriterium_erfolgsaussichten",
    "kriterium_finanzielle_notlage",
    "kriterium_keine_rs_deckung"
]

def darf_fall_verfolgen():
    return bool({"MV_Solifonds_GL", "MV_Solifonds_Vorpruefung"} & set(frappe.get_roles()))

def darf_visieren():
    # #2210: Visum setzt und entfernt nur die GL
    return "MV_Solifonds_GL" in frappe.get_roles()

class Mandat(Document):
    def autoname(self):
        jahr = datetime.date.today().year
        if self.mv_mitgliedschaft:
            sektion = frappe.db.get_value("Mitgliedschaft", self.mv_mitgliedschaft, "sektion_id")
        else:
            sektion = 'MVD'
        self.name = make_autoname("{0}-{1}-.#".format(sektion, jahr))

    def before_save(self):
        # «Fall verfolgen» dürfen nur GL und Vorprüfung ändern
        if not darf_fall_verfolgen() and not frappe.flags.in_patch:
            alt = 0 if self.is_new() else cint(frappe.db.get_value("Mandat", self.name, "fall_verfolgen"))
            if cint(self.fall_verfolgen) != alt:
                frappe.throw(frappe._("«Fall verfolgen» können nur Geschäftsleitung und Vorprüfung setzen."))

        self.pruefe_visum()

        if self.kontaktperson and "pool" in self.kontaktperson.lower():
            self.kontaktperson = None
            frappe.throw(
                msg=frappe._("Pool ist als Vertrauensanwält*in nicht erlaubt. Bitte korrigieren."),
                title=frappe._("Ungültige Kontaktperson")
            )

        # #2208: Hierarchie wie in der Beratung – (2) nur mit (1), (3) nur mit (2); Lücken aufrücken
        set_beratungskategorien(self, [self.get(f) for f in KATEGORIE_FELDER])

        if self.typ == "Solidaritätsfonds":
            self.kostendach = SOLIFONDS_KOSTENDACH.get(self.solifonds_art) or 0

        # #2205: Status-Regeln, Automatik Unzugewiesen/Vorgemerkt (nur vor dem Einreichen, #2207) und Statusverlauf
        status_vor_speichern(self)

    def pruefe_visum(self):
        # #2210: Visum nur bei RSV und nur durch die GL; wer und wann wird festgehalten
        alt = 0 if self.is_new() else cint(frappe.db.get_value("Mandat", self.name, "visum"))
        if cint(self.visum) == alt or frappe.flags.in_patch:
            return
        if not darf_visieren():
            frappe.throw(frappe._("Das Visum kann nur die Geschäftsleitung setzen oder entfernen."))
        if cint(self.visum) and self.typ == "Solidaritätsfonds":
            frappe.throw(frappe._("Ein Visum gibt es nur bei Mandaten Rechtsschutzversicherung."))
        if cint(self.visum):
            self.visiert_von = frappe.session.user
            self.visiert_am = now_datetime()
        else:
            self.visiert_von = None
            self.visiert_am = None
        self.flags.visum_geaendert = True

    def on_update(self):
        if self.flags.visum_geaendert:
            self.add_comment("Info", frappe._("Mandat visiert.") if cint(self.visum) else frappe._("Visum entfernt."))

        # Bestätigungs-Email senden
        if (self.typ == "Rechtsschutzversicherung" and 
            self.kontaktperson and 
            not self.bestaetigungs_email_gesendet):
        
            email_sent = send_confirmation_email(self)
            if email_sent:
                self.db_set("bestaetigungs_email_gesendet", 1)

@frappe.whitelist()
def create_mandat(beratung, berater_in=None, typ=None, bemerkung=None, persoenliche_bemerkung=None, beratungskategorien=None,
                  fall_verfolgen=0, solifonds_art=None, solifonds_begruendung=None, kriterien=None, sprache=None):
    from mvd.mvd.doctype.beratung.beratung import uebernahme

    if "MV_Mandat" not in frappe.get_roles():
        frappe.throw(frappe._("Keine Berechtigung zum Erstellen von Mandaten."), frappe.PermissionError)

    beratung = frappe.get_doc("Beratung", beratung)
    if not beratung.has_permission("read"):
        frappe.throw(frappe._("Keine Berechtigung für diese Beratung."), frappe.PermissionError)

    # Doppelklick / mehrere Anfragen gleichzeitig: Beratung bis zum Ende der Transaktion sperren und den
    # aktuellen Stand lesen (FOR UPDATE liest den zuletzt gespeicherten Wert, nicht den Stand vom Anfang der Anfrage)
    aktuelles_mandat = frappe.db.sql("SELECT `mandat` FROM `tabBeratung` WHERE `name` = %s FOR UPDATE", beratung.name)
    if beratung.mandat or (aktuelles_mandat and aktuelles_mandat[0][0]):
        frappe.throw(frappe._("Es existiert bereits ein Mandat für diesen Datensatz."))

    if not beratung.mv_mitgliedschaft:
        frappe.throw(frappe._("Ein Mandat ist nur für Beratungen mit Mitglied möglich. Bitte zuerst die Beratung einem Mitglied zuordnen und speichern."))

    if not beratung.beratungskategorie:
        frappe.throw(frappe._("Bitte zuerst in der Beratung die Beratungskategorie setzen und speichern."))

    # Persönliche Bemerkung darf nur die VA selbst setzen
    if persoenliche_bemerkung and (not berater_in or berater_in != uebernahme(beratung.name, frappe.session.user)):
        frappe.throw(frappe._("Eine persönliche Bemerkung kann nur erfassen, wer das Mandat selbst übernimmt."))

    mandat = frappe.new_doc("Mandat")

    mandat.mv_mitgliedschaft = beratung.mv_mitgliedschaft
    mandat.sektion_id = beratung.sektion_id
    mandat.beratung = beratung.name
    # #2208: Beratungskategorien (1)-(3) wie in der Beratung; aus dem Dialog (änderbar), sonst 1:1 aus der Beratung
    kategorien = frappe.parse_json(beratungskategorien) if beratungskategorien else get_beratungskategorien(beratung)
    set_beratungskategorien(mandat, kategorien)
    mandat.kontaktperson = berater_in
    mandat.typ = typ or RSV
    # #2211: Verfahrenssprache (nur de/fr) aus dem Dialog (änderbar), sonst aus der Mitgliedschaft
    if sprache and sprache not in VERFAHRENSSPRACHEN:
        frappe.throw(frappe._("Als Verfahrenssprache sind nur Deutsch (de) und Französisch (fr) möglich."))
    if not sprache:
        sprache = frappe.db.get_value("Mitgliedschaft", beratung.mv_mitgliedschaft, "language")
    mandat.sprache = sprache if sprache in VERFAHRENSSPRACHEN else None
    mandat.bemerkung = bemerkung
    mandat.persoenliche_bemerkung = persoenliche_bemerkung
    # «Fall verfolgen» setzen nur GL und Vorprüfung
    mandat.fall_verfolgen = cint(fall_verfolgen) if darf_fall_verfolgen() else 0

    if typ == "Solidaritätsfonds":
        mandat.solifonds_art = solifonds_art
        # "keine Musse": Begründung darf bei der Vorerfassung leer sein, Pflicht erst beim Einreichen
        mandat.solifonds_begruendung = solifonds_begruendung
        # Kriterien gibt es nur bei "mangels Rechtsschutzdeckung"
        if solifonds_art == "mangels Rechtsschutzdeckung":
            gewaehlt = frappe.parse_json(kriterien) if kriterien else []
            for kriterium in SOLIFONDS_KRITERIEN:
                mandat.set(kriterium, 1 if kriterium in gewaehlt else 0)
            # #2218: alle Kriterien (kumulativ) schon beim Erstellen Pflicht, nicht erst beim Einreichen
            from mvd.mvd.doctype.mandat.solifonds import _check_kriterien
            _check_kriterien(mandat)

    # #2213: Mietobjekt und zuständige Schlichtungsbehörde übernehmen
    if beratung.mv_mitgliedschaft:
        mandat.mietobjekt, mandat.schlichtungsbehoerde = get_mietobjekt_und_schlichtungsbehoerde(beratung.mv_mitgliedschaft)

    mandat.insert(ignore_permissions=True)

    frappe.db.set_value("Beratung", beratung.name, "mandat", mandat.name)

    # #2238: im Verlauf der Beratung festhalten (wer und wann zeigt der Eintrag selbst)
    if mandat.kontaktperson:
        uebernahme_text = frappe._("übernommen von {0}").format(escape_html(mandat.kontaktperson))
    else:
        uebernahme_text = frappe._("nicht übernommen, das Sekretariat sucht eine Vertrauensanwält*in")
    beratung.add_comment("Info", frappe._("Mandat {0} erstellt (Typ: {1}), {2}.").format(
        '<a href="#Form/Mandat/{0}">{0}</a>'.format(escape_html(mandat.name)), escape_html(mandat.typ), uebernahme_text))

    return mandat.name

def get_mietobjekt_und_schlichtungsbehoerde(mitgliedschaft):
    # #2213: Objektadresse der Mitgliedschaft als Text und die zuständige Schlichtungsbehörde.
    # Ohne Treffer im Gebäudeverzeichnis oder ohne Antwort von mp.libracore.ch bleibt die Behörde leer.
    from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import validate_address
    m = frappe.db.get_value("Mitgliedschaft", mitgliedschaft, [
        "name", "objekt_zusatz_adresse", "objekt_strasse", "objekt_hausnummer", "objekt_nummer_zu",
        "objekt_plz", "objekt_ort"], as_dict=True)
    if not m:
        return None, None
    zeilen = [
        m.objekt_zusatz_adresse,
        " ".join(x for x in (m.objekt_strasse, "{0}{1}".format(m.objekt_hausnummer or "", m.objekt_nummer_zu or "")) if x),
        " ".join(x for x in (m.objekt_plz, m.objekt_ort) if x)
    ]
    mietobjekt = "\n".join(z for z in zeilen if z) or None

    # validate_address mit doc statt doc_id schreibt nichts in die Mitgliedschaft
    validierung = validate_address(doc=frappe._dict(m))
    behoerde = None
    if validierung.get("success") and validierung.get("bfs_nr"):
        behoerde = get_schlichtungsbehoerde_adresse(validierung.get("bfs_nr"))
    return mietobjekt, behoerde

def get_schlichtungsbehoerde_adresse(bfs_nr):
    try:
        response = requests.get("https://mp.libracore.ch/api/method/mietrechtspraxis.api.get_arbitration_authority_from_bfs",
            params={"bfs_nr": bfs_nr}, timeout=5)
        daten = (response.json() or {}).get("message") if response.status_code == 200 else None
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Mandat: Schlichtungsbehörde nicht abrufbar")
        return None
    if not daten or not daten.get("aa_address_html"):
        return None
    # «Name, Region, Strasse, PLZ Ort» -> eine Zeile pro Teil
    return "\n".join(t.strip() for t in strip_html(daten.get("aa_address_html")).split(",") if t.strip()) or None

@frappe.whitelist()
def schlichtungsbehoerde_ermitteln(mandat):
    doc = frappe.get_doc("Mandat", mandat)
    if not doc.has_permission("write"):
        frappe.throw(frappe._("Keine Berechtigung für dieses Mandat."), frappe.PermissionError)
    if not doc.mv_mitgliedschaft:
        frappe.throw(frappe._("Das Mandat hat kein Mitglied."))
    mietobjekt, behoerde = get_mietobjekt_und_schlichtungsbehoerde(doc.mv_mitgliedschaft)
    if not behoerde:
        frappe.throw(frappe._("Die Schlichtungsbehörde konnte nicht ermittelt werden: Die Objektadresse wurde im amtlichen Gebäudeverzeichnis nicht gefunden oder mp.libracore.ch antwortet nicht."))
    doc.schlichtungsbehoerde = behoerde
    if not doc.mietobjekt:
        doc.mietobjekt = mietobjekt
    doc.save()
    return behoerde

KATEGORIE_FELDER = ("beratungskategorie", "beratungskategorie_2", "beratungskategorie_3")

def set_beratungskategorien(mandat, kategorien):
    # Reihenfolge bleibt, leere und doppelte fallen weg, höchstens drei
    liste = []
    for kategorie in kategorien or []:
        if kategorie and kategorie not in liste:
            liste.append(kategorie)
    for i, feld in enumerate(KATEGORIE_FELDER):
        mandat.set(feld, liste[i] if i < len(liste) else None)

def get_beratungskategorien_text(mandat):
    return ", ".join(k for k in (mandat.get(f) for f in KATEGORIE_FELDER) if k)

def get_beratungskategorien(beratung):
    kategorien = []
    for kategorie in (beratung.beratungskategorie, beratung.beratungskategorie_2, beratung.beratungskategorie_3):
        # gelöschte Beratungskategorien (Altdaten) auslassen
        if kategorie and kategorie not in kategorien and frappe.db.exists("Beratungskategorie", kategorie):
            kategorien.append(kategorie)
    return kategorien

def send_confirmation_email(mandat):
    try:
        email_sent = True
        raw_recipients = frappe.db.get_all("Termin Kontaktperson Multi User", 
            filters={"parent": mandat.kontaktperson}, 
            fields=["user"]
        )
        recipients = [d.user for d in raw_recipients if d.user]
        
        sektion_data = frappe.db.get_value("Sektion", mandat.sektion_id, 
            ["template_bestaetigung_kontaktperson", 
             "template_bestaetigung_mitglied",
             "legacy_mail_absender_mail", 
             "legacy_mail_absende_name",
             "pw_email"], as_dict=True)
        
        mitglied_email = frappe.db.get_value("Mitgliedschaft", mandat.mv_mitgliedschaft, "e_mail_1")

        # Absender definieren
        absender_format = "{0} <{1}>".format(
            sektion_data.get("legacy_mail_absende_name") or "Mieterverband", 
            sektion_data.get("legacy_mail_absender_mail")
        )

        # --- 1. EMAIL AN BERATER (mit CC und Attachment) ---
        template_berater = sektion_data.get("template_bestaetigung_kontaktperson")

        if not recipients:
            frappe.log_error("Keine Empfänger für Kontaktperson {0} gefunden.".format(mandat.kontaktperson), "Mandat Email Error")
            email_sent = False
        elif not template_berater:
            frappe.log_error("In Sektion {0} unter Mandat: Kein Template für Kontaktperson hinterlegt.".format(mandat.sektion_id), "Mandat Email Error")
            email_sent = False
        else:
            rendered_berater = get_email_template(template_berater, {"doc": mandat})

            link_beratung = get_url_to_form("Beratung", mandat.beratung)
            link_mandat = get_url_to_form("Mandat", mandat.name)
            if mandat.mv_mitgliedschaft:
                link_mitglied = get_url_to_form("Mitgliedschaft", mandat.mv_mitgliedschaft)
                # #2209: zusätzlich die Mitglied-Nr. (MV…)
                mitglied_nr = mandat.mitglied_nr or frappe.db.get_value("Mitgliedschaft", mandat.mv_mitgliedschaft, "mitglied_nr")
                mitglied_label = "{0} ({1})".format(mandat.mv_mitgliedschaft, mitglied_nr) if mitglied_nr else str(mandat.mv_mitgliedschaft)
            else:
                link_mitglied = "#"
                mitglied_label = "Keine Mitgliedschaft verknüpft"

            # Wir schicken das Stammdatenblatt und die Dokumente der Beratung als Anhang
            attachments = []
            if mandat.mv_mitgliedschaft:
                pdf_content = frappe.get_print("Mitgliedschaft", mandat.mv_mitgliedschaft, "Stammdatenblatt", as_pdf=True)
                filename = "Stammdatenblatt_{0}.pdf".format(mandat.mv_mitgliedschaft)
                
                file_doc = frappe.get_doc({
                    "doctype": "File",
                    "file_name": filename,
                    "attached_to_doctype": "Mandat",
                    "attached_to_name": mandat.name,
                    "content": pdf_content,
                    "is_private": 1
                })
                file_doc.insert(ignore_permissions=True)
                attachments.append({"fid": file_doc.name})
            
            # #2214: statt ZIP-Datei ein Link; das ZIP entsteht erst beim Abruf (Login und Leserecht aufs Mandat nötig)
            zip_link_html = ""
            if mandat.beratung and frappe.db.count("File", {"attached_to_doctype": "Beratung", "attached_to_name": mandat.beratung}):
                zip_link_html = """<a href="{0}">Alle Anlagen der Beratung als ZIP herunterladen</a> (Anmeldung in Libracore nötig)""".format(
                    get_anlagen_zip_url(mandat.name))

            persoenliche_bemerkung_html = ""
            if mandat.persoenliche_bemerkung:
                persoenliche_bemerkung_html = """
                    <br><br>
                    <p><b>Persönliche Bemerkung:</b><br>{0}</p>
                """.format(escape_html(mandat.persoenliche_bemerkung).replace("\n", "<br>"))

            footer_links = """
                <br><br>
                <hr>
                <p style="font-size: 12px; color: #555;">
                    <b>Interne Links für Berater:</b><br>
                    - <a href="{0}">Direkt zur Beratung: {1}</a><br>
                    - <a href="{2}">Direkt zum Mandat: {3}</a><br>
                    - <a href="{4}">Zur Mitgliedschaft: {5}</a>{6}
                </p>
            """.format(link_beratung, mandat.beratung, link_mandat, mandat.name, link_mitglied, escape_html(mitglied_label),
                       # #2216: Zeile «Anlagen» nur, wenn es Anlagen gibt (sonst blieb ein einzelner Strich stehen)
                       "<br>\n                    - {0}".format(zip_link_html) if zip_link_html else "")
            
            full_message = rendered_berater.get("message") + persoenliche_bemerkung_html + footer_links
            comm = make(
                recipients=recipients,
                sender=absender_format,
                subject=rendered_berater.get("subject"),
                content=full_message,
                doctype='Mandat',
                name=mandat.name,
                send_email=False
            )["name"]
            sendmail(
                recipients=recipients,
                sender=absender_format,
                subject=rendered_berater.get("subject"),
                content=full_message,
                attachments=attachments,
                reference_doctype=mandat.doctype,
                reference_name=mandat.name,
                unsubscribe_method=None,
                unsubscribe_params=None,
                unsubscribe_message=None,
                communication=comm,
                delayed=True,
                message_id=frappe.get_value("Communication", comm, "message_id")
            )
        
        # --- 2. EMAIL AN MITGLIED ---
        # template_mitglied = sektion_data.get("template_bestaetigung_mitglied")
        # if not mandat.mv_mitgliedschaft or not mitglied_email:
        #     msg = "Mitglied-Bestätigung (Mandat {0}) fehlgeschlagen (E-Mail fehlt oder kein Mitglied hinterlegt).".format(mandat.name)
        #     sendmail(recipients=sektion_data.get("pw_email"), sender="libracore@mvd.mieterverband.ch", 
        #              subject="Fehler: Bestätigung Mandat", content=msg, reference_doctype="Mandat", reference_name=mandat.name)
            
        # elif not template_mitglied:
        #     frappe.log_error("In Sektion {0} unter Mandat: Kein Template für Mitglied hinterlegt.".format(mandat.sektion_id), "Mandat Email Error")
        #     email_sent = False
        # else:
        #     rendered_mitglied = get_email_template(template_mitglied, {"doc": mandat})
        #     comm = make(
        #         recipients=mitglied_email,
        #         sender=absender_format,
        #         subject=rendered_mitglied.get("subject"),
        #         content=rendered_mitglied.get("message"),
        #         doctype='Mandat',
        #         name=mandat.name,
        #         send_email=False
        #     )["name"]
        #     sendmail(
        #         recipients=mitglied_email,
        #         sender=absender_format,
        #         subject=rendered_mitglied.get("subject"),
        #         content=rendered_mitglied.get("message"),
        #         reference_doctype=mandat.doctype,
        #         reference_name=mandat.name,
        #         unsubscribe_method=None,
        #         unsubscribe_params=None,
        #         unsubscribe_message=None,
        #         communication=comm,
        #         delayed=True,
        #         message_id=frappe.get_value("Communication", comm, "message_id")
        #     )
        
        return email_sent
    
    except Exception:
        frappe.log_error(
            title="Mandat Confirmation Email Error",
            message=frappe.get_traceback()
        )
        return False


def get_anlagen_zip_url(mandat):
    return get_url("/api/method/mvd.mvd.doctype.mandat.mandat.download_anlagen?mandat={0}".format(quote(mandat)))

@frappe.whitelist(allow_guest=True)
def download_anlagen(mandat):
    # #2214: Anlagen der Beratung als ZIP, erst beim Abruf erzeugt. allow_guest nur, um Gäste zum Login umzuleiten.
    if frappe.session.user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login?redirect-to={0}".format(
            quote("/api/method/mvd.mvd.doctype.mandat.mandat.download_anlagen?mandat={0}".format(quote(mandat))))
        return
    doc = frappe.get_doc("Mandat", mandat)
    if not doc.has_permission("read"):
        frappe.throw(frappe._("Keine Berechtigung für dieses Mandat."), frappe.PermissionError)
    zip_data = get_beratung_zip_attachment(doc.beratung) if doc.beratung else None
    if not zip_data:
        frappe.throw(frappe._("Zu diesem Mandat gibt es keine Anlagen."))
    frappe.local.response.filename = zip_data["fname"]
    frappe.local.response.filecontent = zip_data["fcontent"]
    frappe.local.response.type = "download"

def get_beratung_zip_attachment(beratung_id):
    files = frappe.get_all("File", filters={
        "attached_to_doctype": "Beratung",
        "attached_to_name": beratung_id
    }, fields=["name", "file_name", "file_url", "file_size"])

    if not files:
        return None
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for f in files:
            try:
                # get_full_path kennt öffentliche (/files) und private (/private/files) Dateien
                full_path = frappe.get_doc("File", f.name).get_full_path()
                with open(full_path, "rb") as content:
                    zip_file.writestr(f.file_name, content.read())
            except Exception as e:
                frappe.log_error("Fehler beim Zippen von {0}: {1}".format(f.file_name, str(e)))

    return {
        "fname": "Anlagen_Beratung_{0}.zip".format(beratung_id),
        "fcontent": zip_buffer.getvalue()
    }


VERFAHRENSSPRACHEN = ("de", "fr")
SPRACHNAMEN = {"de": "Deutsch", "fr": "Französisch"}

def sprachname(sprache):
    if not sprache:
        return ""
    return SPRACHNAMEN.get(sprache) or frappe.db.get_value("Language", sprache, "language_name") or sprache

@frappe.whitelist()
def get_mitglied_sprache(beratung):
    # #2211: Vorbelegung «Verfahrenssprache» im Dialog «Mandat erstellen»
    beratung = frappe.get_doc("Beratung", beratung)
    if not beratung.has_permission("read"):
        frappe.throw(frappe._("Keine Berechtigung für diese Beratung."), frappe.PermissionError)
    if not beratung.mv_mitgliedschaft:
        return None
    sprache = frappe.db.get_value("Mitgliedschaft", beratung.mv_mitgliedschaft, "language")
    return sprache if sprache in VERFAHRENSSPRACHEN else None

def filter_va_nach_sprache(kontaktpersonen, sprache):
    # #2211: VAs mit dieser Sprache; wer noch keine Sprache eingetragen hat, gilt für alle Sprachen
    if not kontaktpersonen:
        return []
    mit_sprachen = {}
    for z in frappe.db.get_all("Termin Kontaktperson Multi Language",
            filters={"parent": ["in", kontaktpersonen], "parenttype": "Termin Kontaktperson"}, fields=["parent", "language"]):
        mit_sprachen.setdefault(z.parent, set()).add(z.language)
    return [k for k in kontaktpersonen if k not in mit_sprachen or sprache in mit_sprachen[k]]

@frappe.whitelist()
def suche_vertrauensanwaeltin(mandat_id, sektion_id=None, nur_sprache=0):
    # Nur wer das Mandat lesen darf; Sektion aus dem Mandat, nicht vom Client
    mandat = frappe.get_doc("Mandat", mandat_id)
    if not mandat.has_permission("read"):
        frappe.throw(frappe._("Keine Berechtigung für dieses Mandat."), frappe.PermissionError)
    sektion_id = mandat.sektion_id

    anwaelte = frappe.db.get_all("Termin Kontaktperson", 
        filters={"ist_vertrauensanwaeltin": 1, "sektion_id": sektion_id}, 
        fields=["name"]
    )
    if not anwaelte:
        frappe.throw("Es wurden keine Kontaktpersonen mit dem Status 'Vertrauensanwält*in' gefunden.")
    
    anwaelte_liste = [d.name for d in anwaelte]
    if cint(nur_sprache) and mandat.sprache:
        anwaelte_liste = filter_va_nach_sprache(anwaelte_liste, mandat.sprache)
        if not anwaelte_liste:
            frappe.throw(frappe._("Keine Vertrauensanwält*in der Sektion hat die Sprache «{0}». Es wurde keine Mail vorbereitet. "
                "Mit «Nein» wird an alle Vertrauensanwält*innen geschrieben.").format(sprachname(mandat.sprache)))
    raw_recipients = frappe.db.get_all("Termin Kontaktperson Multi User", 
        filters={"parent": ["in", anwaelte_liste]}, 
        fields=["user"]
    )
    
    recipients_list = list(set([d.user for d in raw_recipients if d.user]))
    if not recipients_list:
        frappe.throw("Es wurden keine Vertrauensanwält*innen mit hinterlegter E-Mail-Adresse gefunden.")
        
    recipients_string = ", ".join(recipients_list)

    visierende_person = frappe.db.get_value("Sektion", sektion_id, "visierende_person")

    subject = "Neues unzugewiesenes Mandat verfügbar: {0}".format(mandat_id)
    if mandat.typ == "Solidaritätsfonds":
        # #2219: Hinweis auf den Solidaritätsfonds (Art des Antrags, Kostendach)
        hinweis = ["Solidaritätsfonds"]
        if mandat.solifonds_art:
            hinweis.append(mandat.solifonds_art)
        if mandat.kostendach:
            hinweis.append("Kostendach CHF {0}".format(frappe.utils.fmt_money(mandat.kostendach, precision=0)))
        subject = "Neues unzugewiesenes Mandat verfügbar ({0}): {1}".format(", ".join(hinweis), mandat_id)

    email_template = frappe.db.get_value("Sektion", sektion_id, "template_suche_vertrauensanwaeltin")

    return {
        "recipients": recipients_string,
        "subject": subject,
        "email_template": email_template or '',
        "cc": visierende_person or ''
    }


def update_mandat_status_nach_email(doc, method):
    if doc.sent_or_received != "Received" or doc.communication_type != "Communication":
        return

    mandat_name = None
    if doc.get("timeline_links"):
        for link in doc.timeline_links:
            if link.link_doctype == "Mandat":
                mandat_name = link.link_name
                break

    if not mandat_name:
        return

    anzahl_emails = frappe.db.count("Communication Link", filters={
        "link_doctype": "Mandat",
        "link_name": mandat_name,
    })

    # Beim Solidaritätsfonds steuert der Ablauf (Einreichen, Vorprüfung, GL) den Status
    if frappe.db.get_value("Mandat", mandat_name, "typ") == "Solidaritätsfonds":
        return

    # #2205: nur aus «Vorgemerkt» (mit VA); Status und Statusverlauf gemeinsam
    if anzahl_emails == 1 and frappe.db.get_value("Mandat", mandat_name, "status") == "Vorgemerkt":
        set_status("Mandat", mandat_name, "Gesuch eingereicht", QUELLE_AUTOMATIK, "Erste E-Mail eingegangen")
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "Mandat",
            "reference_name": mandat_name,
            "content": "Status automatisch auf 'Gesuch eingereicht' geändert (Erste E-Mail eingegangen)."
        }).insert(ignore_permissions=True)

        sektion_id = frappe.db.get_value("Mandat", mandat_name, "sektion_id")
        visierende_person = frappe.db.get_value("Sektion", sektion_id, "visierende_person")

        if visierende_person:
            recipients = [visierende_person]
            link_mandat = get_url_to_form("Mandat", mandat_name)
            subject = "Neue Nachricht in Mandat : {0}".format(mandat_name)
            content = """
                <p>Guten Tag,</p>
                <p>Es ist ein neue Nachricht im Mandat eingegangen.</p>
                <a href="{0}">Link zum Mandat: {1}</a><br>
                <br>
                <p>Liebe Grüsse<br>Libracore</p>
            """.format(link_mandat, mandat_name)
            
            comm = make(
                recipients=recipients,
                subject=subject,
                content=content,
                doctype='Mandat',
                name=mandat_name,
                send_email=False
            )["name"]

            sendmail(
                recipients=recipients,
                subject=subject,
                content=content,
                reference_doctype='Mandat',
                reference_name=mandat_name,
                unsubscribe_method=None,
                unsubscribe_params=None,
                unsubscribe_message=None,
                communication=comm,
                delayed=True,
                message_id=frappe.get_value("Communication", comm, "message_id")
            )
        else:
            frappe.log_error(
                "Keine visierende Person für Sektion {0} gefunden. Benachrichtigung für Mandat {1} nicht gesendet."
                .format(sektion_id, mandat_name), 
                "Mandat Email Error"
            )
