# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

# Ablauf Solidaritätsfonds (#2183):
# Vorgemerkt -> Gesuch eingereicht -> Vorgeprüft -> Gutsprache | Antrag Vorstand | Abgelehnt
# Antrag Vorstand -> (Abstimmung, Abschluss durch GL) -> Gutsprache | Abgelehnt

from __future__ import unicode_literals
import hashlib
import frappe
from frappe import _
from frappe.utils import cint, now_datetime, today, get_url, get_url_to_form, escape_html, strip_html
from frappe.core.doctype.communication.email import make
from frappe import sendmail

TYP = "Solidaritätsfonds"
ROLLE_VORPRUEFUNG = "MV_Solifonds_Vorpruefung"
ROLLE_GL = "MV_Solifonds_GL"
PRINT_FORMAT = "Kostengutsprache Solidaritaetsfonds"


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _get_mandat(mandat):
    doc = frappe.get_doc("Mandat", mandat)
    if doc.typ != TYP:
        frappe.throw(_("Dieses Mandat ist kein Solidaritätsfonds-Mandat."))
    if not doc.has_permission("read"):
        frappe.throw(_("Keine Berechtigung für dieses Mandat."), frappe.PermissionError)
    return doc

def _check_rolle(rolle):
    if rolle not in frappe.get_roles():
        frappe.throw(_("Diese Aktion ist der Rolle {0} vorbehalten.").format(rolle), frappe.PermissionError)

def _check_status(doc, *status):
    if doc.status not in status:
        frappe.throw(_("Diese Aktion ist im Status «{0}» nicht möglich.").format(doc.status))

def _kommentar(doc, text):
    doc.add_comment("Info", text)

def _ist_va_von_mandat(doc):
    if not doc.kontaktperson:
        return False
    return bool(frappe.db.exists("Termin Kontaktperson Multi User", {
        "parent": doc.kontaktperson, "user": frappe.session.user
    }))

def get_users_mit_rolle(rolle, sektion_id):
    # Empfänger*innen: aktive User mit der Rolle und User Permission auf die Sektion
    return frappe.db.sql_list("""
        SELECT DISTINCT `u`.`name`
        FROM `tabUser` AS `u`
        JOIN `tabHas Role` AS `r` ON `r`.`parent` = `u`.`name` AND `r`.`parenttype` = 'User'
        JOIN `tabUser Permission` AS `p` ON `p`.`user` = `u`.`name`
        WHERE `u`.`enabled` = 1
        AND `r`.`role` = %(rolle)s
        AND `p`.`allow` = 'Sektion' AND `p`.`for_value` = %(sektion)s
    """, {"rolle": rolle, "sektion": sektion_id})

def get_va_empfaenger(doc):
    if not doc.kontaktperson:
        return []
    return [u for u in frappe.db.sql_list("""
        SELECT `user` FROM `tabTermin Kontaktperson Multi User` WHERE `parent` = %s
    """, doc.kontaktperson) if u]

def _absender(sektion_id):
    sektion = frappe.db.get_value("Sektion", sektion_id,
        ["legacy_mail_absender_mail", "legacy_mail_absende_name"], as_dict=True) or {}
    if not sektion.get("legacy_mail_absender_mail"):
        return None
    return "{0} <{1}>".format(sektion.get("legacy_mail_absende_name") or "Mieterverband",
        sektion.get("legacy_mail_absender_mail"))

def _sende_mail(doc, empfaenger, betreff, inhalt, dateien=None, mit_kommunikation=True):
    # dateien: Namen von File-Dokumenten; sie erscheinen als Anhang der Mail und der Communication
    if not empfaenger:
        frappe.log_error("Keine Empfänger*innen für «{0}» (Mandat {1}).".format(betreff, doc.name), "Solifonds Mail")
        return
    absender = _absender(doc.sektion_id)
    if not mit_kommunikation:
        # Keine Communication: sie stünde in der Timeline des Mandats und wäre für alle mit Leserecht sichtbar
        sendmail(recipients=empfaenger, sender=absender, subject=betreff, content=inhalt, delayed=True)
        return
    comm = make(
        recipients=empfaenger,
        sender=absender,
        subject=betreff,
        content=inhalt,
        doctype="Mandat",
        name=doc.name,
        attachments=dateien or [],
        send_email=False
    )["name"]
    sendmail(
        recipients=empfaenger,
        sender=absender,
        subject=betreff,
        content=inhalt,
        attachments=[{"fid": f} for f in (dateien or [])],
        reference_doctype="Mandat",
        reference_name=doc.name,
        unsubscribe_method=None,
        unsubscribe_params=None,
        unsubscribe_message=None,
        communication=comm,
        delayed=True,
        message_id=frappe.get_value("Communication", comm, "message_id")
    )

def _text_html(text):
    return escape_html(text or "").replace("\n", "<br>")


# ---------------------------------------------------------------------------
# 1. Einreichen (VA oder Beratung)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def gesuch_einreichen(mandat):
    doc = _get_mandat(mandat)
    # Einreichen dürfen die VA des Mandats und Personen mit MV_Mandat
    if not (_ist_va_von_mandat(doc) or "MV_Mandat" in frappe.get_roles()):
        frappe.throw(_("Einreichen können die zugewiesene Vertrauensanwält*in oder die Beratung."), frappe.PermissionError)
    _check_status(doc, "Vorgemerkt")

    fehlend = []
    if not doc.kontaktperson:
        fehlend.append(_("Vertrauensanwält*in"))
    if not doc.solifonds_art:
        fehlend.append(_("Art des Antrags"))
    if not (doc.solifonds_begruendung or "").strip():
        fehlend.append(_("Begründung"))
    if fehlend:
        frappe.throw(_("Vor dem Einreichen fehlt noch: {0}").format(", ".join(fehlend)))

    doc.status = "Gesuch eingereicht"
    doc.gesuch_eingereicht_am = now_datetime()
    doc.gesuch_eingereicht_von = frappe.session.user
    doc.save(ignore_permissions=True)
    _kommentar(doc, _("Solifonds-Gesuch eingereicht."))
    return doc.status


# ---------------------------------------------------------------------------
# 2. Vorprüfung
# ---------------------------------------------------------------------------

@frappe.whitelist()
def vorpruefung_abschliessen(mandat, vorpruefung_ok, begruendung=None):
    _check_rolle(ROLLE_VORPRUEFUNG)
    doc = _get_mandat(mandat)
    _check_status(doc, "Gesuch eingereicht")
    if not cint(vorpruefung_ok):
        frappe.throw(_("Die Voraussetzungen gemäss Reglement müssen bestätigt sein. Sonst das Gesuch an die VA zurückweisen."))

    doc.vorpruefung_ok = 1
    doc.vorpruefung_begruendung = begruendung
    doc.vorgeprueft_am = now_datetime()
    doc.vorgeprueft_von = frappe.session.user
    doc.status = "Vorgeprüft"
    doc.save(ignore_permissions=True)
    _kommentar(doc, _("Vorprüfung abgeschlossen, an GL weitergeleitet."))
    return doc.status

@frappe.whitelist()
def an_va_zurueckweisen(mandat, grund):
    _check_rolle(ROLLE_VORPRUEFUNG)
    doc = _get_mandat(mandat)
    _check_status(doc, "Gesuch eingereicht")
    if not (grund or "").strip():
        frappe.throw(_("Bitte einen Grund angeben."))

    doc.status = "Vorgemerkt"
    doc.gesuch_eingereicht_am = None
    doc.gesuch_eingereicht_von = None
    doc.save(ignore_permissions=True)
    _kommentar(doc, _("Gesuch an die VA zurückgewiesen: {0}").format(escape_html(grund)))
    _sende_mail(doc, get_va_empfaenger(doc),
        _("Solifonds-Gesuch zurückgewiesen: {0}").format(doc.name),
        "<p>{0}</p><p>{1}</p><p><a href='{2}'>{3}</a></p>".format(
            _("Das Solifonds-Gesuch wurde in der Vorprüfung zurückgewiesen."),
            _text_html(grund), get_url_to_form("Mandat", doc.name), doc.name))
    return doc.status

@frappe.whitelist()
def vorpruefung_zuruecknehmen(mandat):
    _check_rolle(ROLLE_VORPRUEFUNG)
    doc = _get_mandat(mandat)
    _check_status(doc, "Vorgeprüft")

    doc.vorpruefung_ok = 0
    doc.vorgeprueft_am = None
    doc.vorgeprueft_von = None
    doc.status = "Gesuch eingereicht"
    doc.save(ignore_permissions=True)
    _kommentar(doc, _("Vorprüfung zurückgenommen."))
    return doc.status


# ---------------------------------------------------------------------------
# 3. Entscheid GL
# ---------------------------------------------------------------------------

@frappe.whitelist()
def gl_entscheid(mandat, entscheid, bemerkung=None):
    _check_rolle(ROLLE_GL)
    doc = _get_mandat(mandat)
    _check_status(doc, "Vorgeprüft")
    # Die GL wählt bei beiden Arten frei (statutarische Vorgaben: siehe Doku, nicht im Code erzwungen)
    if entscheid not in ("Gutsprache", "Antrag Vorstand", "Abgelehnt"):
        frappe.throw(_("Unbekannter Entscheid."))

    doc.entscheid_bemerkung = bemerkung
    if entscheid == "Antrag Vorstand":
        doc.status = "Antrag Vorstand"
        doc.save(ignore_permissions=True)
        _kommentar(doc, _("Antrag an den Vorstand gestellt."))
        abstimmung_starten(doc)
    else:
        _entscheid_setzen(doc, entscheid, "GL")
    return doc.status

def _entscheid_setzen(doc, entscheid, durch):
    doc.status = entscheid
    doc.entscheid_durch = durch
    doc.entscheid_datum = today()
    doc.save(ignore_permissions=True)
    _kommentar(doc, _("Entscheid {0}: {1}").format(durch, entscheid))
    if entscheid == "Gutsprache":
        gutsprache_mail(doc)
    else:
        ablehnung_mail(doc)


# ---------------------------------------------------------------------------
# 4. Mails bei Gutsprache / Ablehnung
# ---------------------------------------------------------------------------

def gutsprache_mail(doc):
    # Info an die VA, nicht ans Mitglied; das Mitglied unterschreibt das Formular bei der VA
    # PDF als private Datei am Mandat ablegen, damit es im Mandat und in der Communication als Anhang erscheint
    pdf = frappe.get_doc({
        "doctype": "File",
        "file_name": "Kostengutsprache_{0}.pdf".format(doc.name),
        "attached_to_doctype": "Mandat",
        "attached_to_name": doc.name,
        "content": frappe.get_print("Mandat", doc.name, print_format=PRINT_FORMAT, as_pdf=True),
        "is_private": 1
    }).insert(ignore_permissions=True)
    inhalt = "<p>{0}</p><p>{1}</p><p><a href='{2}'>{3}</a></p>".format(
        _("Für das Mandat wurde eine Kostengutsprache aus dem Solidaritätsfonds erteilt (Kostendach CHF {0}).").format(
            frappe.format_value(doc.kostendach, {"fieldtype": "Currency"})),
        _("Im Anhang das Formular «Kostengutsprache Solidaritätsfonds». Bitte vom Mitglied unterschreiben lassen."),
        get_url_to_form("Mandat", doc.name), doc.name)
    _sende_mail(doc, get_va_empfaenger(doc),
        _("Kostengutsprache Solidaritätsfonds: {0}").format(doc.name), inhalt, [pdf.name])

def ablehnung_mail(doc):
    # Ablehnung geht nur an die Vorprüfung, weder an die VA noch ans Mitglied
    empfaenger = get_users_mit_rolle(ROLLE_VORPRUEFUNG, doc.sektion_id)
    inhalt = "<p>{0}</p><p>{1}</p><p><a href='{2}'>{3}</a></p>".format(
        _("Das Solifonds-Gesuch wurde abgelehnt ({0}).").format(doc.entscheid_durch or ""),
        _text_html(doc.entscheid_bemerkung),
        get_url_to_form("Mandat", doc.name), doc.name)
    _sende_mail(doc, empfaenger, _("Solifonds-Gesuch abgelehnt: {0}").format(doc.name), inhalt)


# ---------------------------------------------------------------------------
# 5. Vorstandsabstimmung
# ---------------------------------------------------------------------------

def get_vorstand(sektion_id):
    return frappe.get_all("Termin Kontaktperson",
        filters={"ist_vorstand": 1, "disabled": 0, "sektion_id": sektion_id},
        fields=["name"])

def abstimmung_starten(doc):
    vorstand = get_vorstand(doc.sektion_id)
    if not vorstand:
        frappe.throw(_("In der Sektion {0} ist keine Kontaktperson mit «Vorstand» erfasst.").format(doc.sektion_id))

    # Im Mandat steht nur der Hash des Tokens; der Token selbst steht nur im Link der Mail
    tokens = {}
    doc.set("vorstand_stimmen", [])
    for person in vorstand:
        token = frappe.generate_hash(length=32)
        tokens[person.name] = token
        doc.append("vorstand_stimmen", {
            "kontaktperson": person.name,
            "token": _token_hash(token)
        })
    doc.save(ignore_permissions=True)

    for stimme in doc.vorstand_stimmen:
        empfaenger = [u for u in frappe.db.sql_list("""
            SELECT `user` FROM `tabTermin Kontaktperson Multi User` WHERE `parent` = %s
        """, stimme.kontaktperson) if u]
        link = get_url("/solifonds-abstimmung?token={0}".format(tokens[stimme.kontaktperson]))
        inhalt = "<p>{0}</p><p><a href='{1}'>{2}</a></p><p>{3}</p>".format(
            _("Die Geschäftsleitung beantragt eine Kostengutsprache aus dem Solidaritätsfonds. Bitte stimmen Sie über den anonymisierten Fall ab."),
            link, _("Zur Abstimmung"),
            _("Dieser Link ist persönlich und nur für Sie gültig."))
        _sende_mail(doc, empfaenger, _("Solifonds: Abstimmung Vorstand ({0})").format(doc.name), inhalt,
            mit_kommunikation=False)
        # Verlauf: an wen der Link ging, ohne den Link selbst
        if empfaenger:
            _kommentar(doc, _("Abstimmungslink per E-Mail an {0} (Vorstand) verschickt: {1}").format(
                escape_html(stimme.kontaktperson), escape_html(", ".join(empfaenger))))
        else:
            _kommentar(doc, _("Kein Abstimmungslink an {0} (Vorstand): keine E-Mail-Adresse hinterlegt.").format(
                escape_html(stimme.kontaktperson)))

def get_abstimmung_stand(doc):
    ja = len([s for s in doc.vorstand_stimmen if s.stimme == "Ja"])
    nein = len([s for s in doc.vorstand_stimmen if s.stimme == "Nein"])
    enthaltung = len([s for s in doc.vorstand_stimmen if s.stimme == "Enthaltung"])
    total = len(doc.vorstand_stimmen)
    return {"ja": ja, "nein": nein, "enthaltung": enthaltung, "offen": total - ja - nein - enthaltung, "total": total}

@frappe.whitelist()
def abstimmung_abschliessen(mandat, patt_entscheid=None):
    _check_rolle(ROLLE_GL)
    doc = _get_mandat(mandat)
    _check_status(doc, "Antrag Vorstand")

    # Einfache Mehrheit der abgegebenen Stimmen (Enthaltungen zählen nicht)
    stand = get_abstimmung_stand(doc)
    durch = "Vorstand"
    if stand["ja"] > stand["nein"]:
        entscheid = "Gutsprache"
    elif stand["nein"] > stand["ja"]:
        entscheid = "Abgelehnt"
    else:
        # Bei Patt entscheidet die GL
        if patt_entscheid not in ("Gutsprache", "Abgelehnt"):
            return {"patt": 1, "stand": stand}
        entscheid = patt_entscheid
        durch = "GL"

    _kommentar(doc, _("Vorstandsabstimmung abgeschlossen: Ja {0}, Nein {1}, Enthaltung {2}, offen {3}.").format(
        stand["ja"], stand["nein"], stand["enthaltung"], stand["offen"]))
    if durch == "GL":
        _kommentar(doc, _("Patt in der Vorstandsabstimmung, Entscheid durch GL."))
    _entscheid_setzen(doc, entscheid, durch)
    return {"status": doc.status, "stand": stand}

def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def get_stimme_per_token(token):
    if not token or len(token) < 32:
        return None
    name = frappe.db.get_value("Mandat Vorstand Stimme", {"token": _token_hash(token), "parenttype": "Mandat"}, "name")
    return frappe.get_doc("Mandat Vorstand Stimme", name) if name else None

@frappe.whitelist(allow_guest=True)
def abstimmen(token, stimme, kommentar=None):
    zeile = get_stimme_per_token(token)
    if not zeile:
        frappe.throw(_("Ungültiger Link."))
    if stimme not in ("Ja", "Nein", "Enthaltung"):
        frappe.throw(_("Ungültige Stimme."))
    if frappe.db.get_value("Mandat", zeile.parent, "status") != "Antrag Vorstand":
        frappe.throw(_("Die Abstimmung ist abgeschlossen."))

    # Kommentar kommt ohne Login: kein HTML, Länge begrenzt
    kommentar = strip_html(kommentar or "").strip()[:2000]
    frappe.db.set_value("Mandat Vorstand Stimme", zeile.name, {
        "stimme": stimme,
        "kommentar": kommentar,
        "abgestimmt_am": now_datetime()
    }, update_modified=False)
    frappe.db.commit()
    return stimme


# ---------------------------------------------------------------------------
# 6. Nächtliche Listen-Mail
# ---------------------------------------------------------------------------

def sende_solifonds_listen():
    for sektion_id in frappe.db.sql_list("""
        SELECT DISTINCT `sektion_id` FROM `tabMandat`
        WHERE `typ` = %s AND `status` IN ('Gesuch eingereicht', 'Vorgeprüft', 'Antrag Vorstand')
    """, TYP):
        _sende_liste(sektion_id, ROLLE_VORPRUEFUNG, ["Gesuch eingereicht"], _("Solifonds: Gesuche zur Vorprüfung"))
        _sende_liste(sektion_id, ROLLE_GL, ["Vorgeprüft", "Antrag Vorstand"], _("Solifonds: Gesuche zum Entscheid"))

def _sende_liste(sektion_id, rolle, status, betreff):
    mandate = frappe.get_all("Mandat",
        filters={"typ": TYP, "sektion_id": sektion_id, "status": ["in", status]},
        fields=["name", "status", "mv_mitgliedschaft", "solifonds_art", "kontaktperson", "gesuch_eingereicht_am"],
        order_by="gesuch_eingereicht_am asc")
    empfaenger = get_users_mit_rolle(rolle, sektion_id)
    if not mandate or not empfaenger:
        return

    zeilen = "".join("<tr><td><a href='{0}'>{1}</a></td><td>{2}</td><td>{3}</td><td>{4}</td><td>{5}</td><td>{6}</td></tr>".format(
        get_url_to_form("Mandat", m.name), m.name, escape_html(m.status), escape_html(m.mv_mitgliedschaft or ""),
        escape_html(m.solifonds_art or ""), escape_html(m.kontaktperson or "–"),
        frappe.utils.formatdate(m.gesuch_eingereicht_am) if m.gesuch_eingereicht_am else "") for m in mandate)
    inhalt = """<p>{0}</p>
        <table border="1" cellpadding="6" style="border-collapse: collapse">
        <tr><th>Mandat</th><th>Status</th><th>Mitglied</th><th>Art</th><th>VA</th><th>Eingereicht</th></tr>{1}</table>
        <p><a href="{2}">{3}</a></p>""".format(
        _("Folgende Solifonds-Gesuche warten auf Sie:"), zeilen,
        get_url("/desk#vbz-solifonds"), _("Zum Solifonds-Dashboard"))

    absender = _absender(sektion_id)
    sendmail(recipients=empfaenger, sender=absender,
        subject="{0} ({1})".format(betreff, len(mandate)), content=inhalt, delayed=True)


# ---------------------------------------------------------------------------
# 7. Daten für Dashboard und Formular
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_dashboard():
    _check_rolle(ROLLE_GL)
    # Sektionstrennung über User Permissions (get_list)
    mandate = frappe.get_list("Mandat",
        filters={"typ": TYP, "status": ["not in", ["Abgeschlossen", "Rückzug", "Gelöscht"]]},
        fields=["name", "status", "sektion_id", "mv_mitgliedschaft", "solifonds_art", "kostendach",
                "kontaktperson", "gesuch_eingereicht_am", "vorgeprueft_am", "entscheid_datum", "creation"],
        order_by="creation asc", limit_page_length=500)

    stimmen = {}
    namen = [m.name for m in mandate if m.status == "Antrag Vorstand"]
    if namen:
        for s in frappe.get_all("Mandat Vorstand Stimme", filters={"parent": ["in", namen], "parenttype": "Mandat"},
                fields=["parent", "stimme"]):
            stand = stimmen.setdefault(s.parent, {"ja": 0, "nein": 0, "enthaltung": 0, "offen": 0, "total": 0})
            stand["total"] += 1
            schluessel = {"Ja": "ja", "Nein": "nein", "Enthaltung": "enthaltung"}.get(s.stimme, "offen")
            stand[schluessel] += 1

    themen = {}
    if mandate:
        for t in frappe.get_all("RSV Thema MultiTable",
                filters={"parent": ["in", [m.name for m in mandate]], "parenttype": "Mandat"},
                fields=["parent", "thema"], order_by="idx asc"):
            themen.setdefault(t.parent, []).append(t.thema)

    for m in mandate:
        m.stand = stimmen.get(m.name)
        m.themen = ", ".join(themen.get(m.name, []))
    return mandate
