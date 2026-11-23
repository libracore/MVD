# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt
"""Hinweis oben im Mandat: was steht jetzt an, und für wen? (#2205, #2241)

Alle Texte stehen in HINWEISE. Der Server wählt in Mandat.onload den passenden Hinweis aus
(__onload.hinweis), mandat.js zeigt ihn nur an.
Texte synchron halten mit dem Handbuch (Wiki «MVBE Mandate (Dokumentation)», Page-ID 292880515, Abschnitt «Hinweis oben im Mandat»).
"""

from __future__ import unicode_literals
import frappe
from frappe.utils import escape_html, cint
from mvd.mvd.doctype.mandat.mandat_status import SOLIFONDS

# ---------------------------------------------------------------------------
# Konfiguration
#
# Je Zeile: (Status, Typ, Rolle, Bedingung, Farbe, Text). Die erste passende Zeile gilt.
#   Typ:       "RSV", "Solifonds" oder "*"
#   Rolle:     "va"  = eigene Vertrauensanwält*in des Mandats oder «nur RB»
#              "vp"  = Vorprüfung (MV_Solifonds_Vorpruefung)
#              "gl"  = Geschäftsleitung (MV_Solifonds_GL)
#              "*"   = alle (Sekretariat, MA, …)
#   Bedingung: None oder ein Name aus BEDINGUNGEN (unten)
#   Farbe:     yellow = du bist dran, blue = Info, green = erledigt, red = abgelehnt
#   Text:      HTML; Platzhalter {dran}, {cc}, {rueckweisung}, {status}
# ---------------------------------------------------------------------------

HINWEISE = [
    ("Unzugewiesen", "*", "*", None, "blue",
     "Noch keine Vertrauensanwält*in. Über <b>Suche Vertrauensanwält*in</b> anfragen oder die VA direkt eintragen. "
     "Findet sich keine: <b>Status → Nicht vergeben</b>."),

    ("Nicht vergeben", "*", "*", None, "blue",
     "Keine Vertrauensanwält*in gefunden. Wird doch noch eine VA eingetragen, steht das Mandat wieder auf «Vorgemerkt»."),

    ("Vorgemerkt", "Solifonds", "va", None, "yellow",
     "{rueckweisung}{dran}Begründung und Kriterien prüfen, dann <b>Solidaritätsfonds → Gesuch einreichen</b>."),
    ("Vorgemerkt", "Solifonds", "*", None, "blue",
     "Wartet auf das Einreichen durch die Vertrauensanwält*in."),
    ("Vorgemerkt", "RSV", "va", None, "yellow",
     "{dran}Gesuch bei der Coop einreichen, mit dieser Adresse im CC: {cc}"
     "<br>Kommt die Mail an, wechselt der Status automatisch auf «Gesuch eingereicht»."),
    ("Vorgemerkt", "RSV", "*", None, "blue",
     "Wartet darauf, dass die Vertrauensanwält*in das Gesuch bei der Coop einreicht."),

    ("Gesuch eingereicht", "RSV", "va", None, "blue",
     "Wartet auf den Entscheid der Coop. Erteilt sie Deckung bzw. Kostengutsprache, setzt du den Status auf "
     "<b>«Laufend (RSV)»</b> (Feld Status)."),
    ("Gesuch eingereicht", "RSV", "gl", "nicht_visiert", "yellow",
     "{dran}Gesuch prüfen und <b>visieren</b> (Häkchen «Visum»). Will die Geschäftsleitung den Fall weiter im Auge behalten, "
     "zusätzlich <b>«Fall verfolgen»</b> setzen.<br>" + "Wartet auf den Entscheid der Coop. Danach setzt die Vertrauensanwält*in den Status."),
    ("Gesuch eingereicht", "RSV", "*", None, "blue",
     "Wartet auf den Entscheid der Coop. Danach setzt die Vertrauensanwält*in den Status."),
    ("Gesuch eingereicht", "Solifonds", "vp", None, "yellow",
     "{dran}Gesuch prüfen. Passt es: <b>Solidaritätsfonds → Vorprüfung abschliessen</b> und bestätigen, dass die Voraussetzungen "
     "gemäss Reglement erfüllt sind. Sonst: <b>Solidaritätsfonds → An VA zurückweisen</b> (mit Grund)."),
    ("Gesuch eingereicht", "Solifonds", "*", None, "blue",
     "Das Solifonds-Gesuch ist eingereicht und wartet auf die Vorprüfung."),

    ("Vorgeprüft", "*", "gl", None, "yellow",
     "{dran}<b>Solidaritätsfonds → Entscheid GL</b>: Kostengutsprache, Ablehnung oder Antrag an den Vorstand."),
    ("Vorgeprüft", "*", "vp", None, "blue",
     "Vorgeprüft, wartet auf den Entscheid der Geschäftsleitung. Bei Bedarf <b>Solidaritätsfonds → Vorprüfung zurücknehmen</b>."),
    ("Vorgeprüft", "*", "*", None, "blue",
     "Vorgeprüft, wartet auf den Entscheid der Geschäftsleitung."),

    ("Antrag Vorstand", "*", "gl", None, "yellow",
     "{dran}Der Vorstand stimmt über den persönlichen Link in seiner E-Mail ab; den Stand siehst du unten im Abschnitt «Vorstand». "
     "Danach <b>Solidaritätsfonds → Abstimmung abschliessen</b> (bei Patt entscheidet die GL)."),
    ("Antrag Vorstand", "*", "*", None, "blue",
     "Antrag an den Vorstand: Die Abstimmung läuft."),

    ("Laufend (RSV)", "*", "va", None, "blue",
     "Ist der Fall erledigt, Status auf «Abgeschlossen» setzen (Feld Status)."),
    ("Laufend (RSV)", "*", "gl", "nicht_visiert", "yellow",
     "{dran}Mandat prüfen und <b>visieren</b> (Häkchen «Visum»). Will die Geschäftsleitung den Fall weiter im Auge behalten, "
     "zusätzlich <b>«Fall verfolgen»</b> setzen.<br>Laufend, die Vertrauensanwält*in führt den Fall."),
    ("Laufend (RSV)", "*", "*", None, "blue",
     "Laufend, die Vertrauensanwält*in führt den Fall."),

    ("Laufend (Solifonds)", "*", "va", None, "blue",
     "Kostengutsprache erteilt, das PDF kam per E-Mail. Formular vom Mitglied unterschreiben lassen. "
     "Ist der Fall erledigt: <b>Status → Abschliessen</b>."),
    ("Laufend (Solifonds)", "*", "*", None, "blue",
     "Kostengutsprache erteilt, die Vertrauensanwält*in führt den Fall."),

    ("Abgelehnt", "*", "va", None, "red",
     "Das Gesuch wurde abgelehnt. Weiter bearbeitet wird es nicht; möglich ist nur noch der Status «Rückzug»."),
    ("Abgelehnt", "RSV", "*", None, "red",
     "Das Gesuch wurde abgelehnt. Weiter bearbeitet wird es nicht; möglich ist nur noch der Status «Rückzug» bzw. «Gelöscht». "
     "Ändert sich der Entscheid, kann die Geschäftsleitung den Status im Feld <b>Status</b> anpassen."),
    ("Abgelehnt", "*", "*", None, "red",
     "Das Gesuch wurde abgelehnt. Weiter bearbeitet wird es nicht; möglich ist nur noch der Status «Rückzug» bzw. «Gelöscht»."),

    ("Abgeschlossen", "*", "*", None, "green", "Erledigt (Status «{status}»)."),
    ("Rückzug", "*", "*", None, "green", "Erledigt (Status «{status}»)."),
    ("Gelöscht", "*", "*", None, "green", "Gelöscht – das Mandat wird nicht weiter bearbeitet."),
]

# Zusatz für «nur RB», wenn das Solifonds-Mandat nach dem Einreichen gesperrt ist (#2206), je Status
NUR_RB_ZUSATZ = {
    "Gesuch eingereicht": "Du kannst das Mandat nur noch ansehen. Möglich sind noch Anhänge sowie «Abschliessen» und «Rückzug» (Status).",
    "Vorgeprüft": "Du kannst das Mandat nur noch ansehen. Möglich sind noch Anhänge sowie «Abschliessen» und «Rückzug» (Status).",
    "Antrag Vorstand": "Du kannst das Mandat nur noch ansehen. Möglich sind noch Anhänge sowie «Abschliessen» und «Rückzug» (Status).",
    "Laufend (Solifonds)": "Sonst kannst du das Mandat nur noch ansehen und Anhänge hinzufügen.",
}

# ---------------------------------------------------------------------------
# Bedingungen und Platzhalter
# ---------------------------------------------------------------------------

BEDINGUNGEN = {
    "nicht_visiert": lambda doc: not cint(doc.visum),
}


def rueckweisung(doc):
    """Grund der letzten Rückweisung durch die Vorprüfung, falls das Mandat deswegen wieder auf «Vorgemerkt» steht."""
    verlauf = doc.get("statusverlauf") or []
    letzte = verlauf[-1] if verlauf else None
    if letzte and letzte.von_status == "Gesuch eingereicht" and letzte.nach_status == "Vorgemerkt":
        return letzte.bemerkung or ""
    return ""


def cc_html(adresse):
    if not adresse:
        return frappe._("siehe Bestätigungs-E-Mail")
    a = escape_html(adresse)
    return ('<code style="user-select: all;">{0}</code> <button class="btn btn-default btn-xs mandat-cc-kopieren" '
            'data-adresse="{0}" title="{1}"><i class="fa fa-copy"></i> {2}</button>').format(
        a, frappe._("In die Zwischenablage kopieren"), frappe._("Kopieren"))


# ---------------------------------------------------------------------------
# Auswahl
# ---------------------------------------------------------------------------

def get_rollen(doc, ist_va, nur_rb):
    rollen = set(frappe.get_roles())
    r = {"*"}
    if ist_va or nur_rb:
        r.add("va")
    if "MV_Solifonds_Vorpruefung" in rollen:
        r.add("vp")
    if "MV_Solifonds_GL" in rollen:
        r.add("gl")
    return r


def finde_zeile(doc, rollen):
    typ = "Solifonds" if doc.typ == SOLIFONDS else "RSV"
    for zeile in HINWEISE:
        status, z_typ, rolle, bedingung, farbe, text = zeile
        if status != doc.status or z_typ not in ("*", typ) or rolle not in rollen:
            continue
        if bedingung and not BEDINGUNGEN[bedingung](doc):
            continue
        return zeile
    return None


def get_hinweis(doc, ist_va=False, nur_rb=False, rb_gesperrt=False, cc_adresse=None):
    """{"text": html, "farbe": …} oder None."""
    zeile = finde_zeile(doc, get_rollen(doc, ist_va, nur_rb))
    if not zeile:
        return None
    grund = rueckweisung(doc)
    text = frappe._(zeile[5]).format(
        dran="<b>{0}</b> ".format(frappe._("Du bist dran:")),
        cc=cc_html(cc_adresse) if "{cc}" in zeile[5] else "",
        rueckweisung=(frappe._("Von der Vorprüfung zurückgewiesen: «{0}».").format(escape_html(grund)) + " ") if grund else "",
        status=frappe._(doc.status))
    if rb_gesperrt and doc.status in NUR_RB_ZUSATZ:
        text += " " + frappe._(NUR_RB_ZUSATZ[doc.status])
    return {"text": text, "farbe": zeile[4]}
