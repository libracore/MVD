# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt
#
# #2205: Status-Konzept Mandat (Wiki «Mandate und Solifonds MVBE Status», 295239681)
#
# - RSV und Solifonds haben je eigene Status; «Gutsprache» heisst neu «Laufend (RSV)» / «Laufend (Solifonds)».
# - RSV: Status von Hand wählbar (nur RSV-Status). Solifonds: Status nur über die Knöpfe.
# - Automatik Unzugewiesen/Vorgemerkt nur vor dem Einreichen (behebt #2207).
# - Ab «Gesuch eingereicht» sind VA und Typ gesperrt; die GL (MV_Solifonds_GL) kann die VA trotzdem ändern.
# - Jede Statusänderung kommt in die Untertabelle «Statusverlauf» (Statusaenderung): wann, wer, von/nach, wodurch.

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import now_datetime, strip_html

RSV = "Rechtsschutzversicherung"
SOLIFONDS = "Solidaritätsfonds"

LAUFEND_RSV = "Laufend (RSV)"
LAUFEND_SOLIFONDS = "Laufend (Solifonds)"
NICHT_VERGEBEN = "Nicht vergeben"

STATUS_RSV = ["Unzugewiesen", NICHT_VERGEBEN, "Vorgemerkt", "Gesuch eingereicht", LAUFEND_RSV,
              "Abgelehnt", "Abgeschlossen", "Rückzug", "Gelöscht"]
STATUS_SOLIFONDS = ["Unzugewiesen", NICHT_VERGEBEN, "Vorgemerkt", "Gesuch eingereicht", "Vorgeprüft", "Antrag Vorstand",
                    LAUFEND_SOLIFONDS, "Abgelehnt", "Abgeschlossen", "Rückzug", "Gelöscht"]

# Vor dem Einreichen: VA und Typ änderbar, Automatik Unzugewiesen/Vorgemerkt aktiv
VOR_EINREICHUNG = ("Unzugewiesen", NICHT_VERGEBEN, "Vorgemerkt")
# Aus jedem Status möglich, auch ohne VA (Beschluss 03.11.2026)
JEDERZEIT = ("Rückzug", "Gelöscht")
LAUFEND = (LAUFEND_RSV, LAUFEND_SOLIFONDS)
# Für die VA bzw. die Übersichten erledigt
ERLEDIGT = ("Abgeschlossen", "Abgelehnt", "Rückzug", "Gelöscht", NICHT_VERGEBEN)

QUELLE_HAND = "von Hand"
QUELLE_KNOPF = "Knopf"
QUELLE_AUTOMATIK = "Automatik"
QUELLE_MIGRATION = "Migration"

ROLLE_GL = "MV_Solifonds_GL"


def status_fuer_typ(typ):
    return STATUS_SOLIFONDS if typ == SOLIFONDS else STATUS_RSV

def darf_va_sperre_uebersteuern():
    return bool({ROLLE_GL, "System Manager"} & set(frappe.get_roles()))


def status_vor_speichern(doc):
    """Aus Mandat.before_save: Regeln prüfen, Automatik anwenden, Statusverlauf schreiben."""
    if frappe.flags.in_patch:
        return

    if not doc.typ:
        doc.typ = RSV

    alt = None
    if not doc.is_new():
        alt = frappe.db.get_value("Mandat", doc.name, ["status", "typ", "kontaktperson"], as_dict=True)

    if alt:
        # Typ nur bis «Vorgemerkt» änderbar
        if alt.typ and doc.typ != alt.typ and alt.status not in VOR_EINREICHUNG:
            frappe.throw(_("Der Typ lässt sich nur bis zum Status «Vorgemerkt» ändern."))
        # VA ab «Gesuch eingereicht» gesperrt; die GL kann übersteuern
        if (alt.kontaktperson or None) != (doc.kontaktperson or None) and alt.status not in VOR_EINREICHUNG \
                and not darf_va_sperre_uebersteuern():
            frappe.throw(_("Ab dem Status «Gesuch eingereicht» lässt sich die Vertrauensanwält*in nicht mehr ändern. Bitte die Geschäftsleitung fragen."))

    # Automatik Unzugewiesen/Vorgemerkt, nur vor dem Einreichen (#2207)
    vorher = doc.status
    if doc.is_new() or doc.status in ("Unzugewiesen", "Vorgemerkt"):
        doc.status = "Vorgemerkt" if doc.kontaktperson else "Unzugewiesen"
    elif doc.status == NICHT_VERGEBEN and doc.kontaktperson:
        # Doch noch eine VA gefunden
        doc.status = "Vorgemerkt"
    if doc.status != vorher or doc.is_new():
        doc.flags.status_quelle = doc.flags.status_quelle or QUELLE_AUTOMATIK

    alt_status = alt.status if alt else None
    if doc.status == alt_status:
        return

    if doc.status not in status_fuer_typ(doc.typ):
        frappe.throw(_("Den Status «{0}» gibt es beim Typ «{1}» nicht.").format(doc.status, doc.typ))

    if doc.status not in VOR_EINREICHUNG + JEDERZEIT and not doc.kontaktperson:
        frappe.throw(_("Für den Status «{0}» braucht es eine Vertrauensanwält*in.").format(doc.status))

    if alt_status == "Abgelehnt" and doc.status not in JEDERZEIT:
        frappe.throw(_("«Abgelehnt» ist ein Endstatus. Möglich sind nur noch «Rückzug» und «Gelöscht»."))

    if doc.status == NICHT_VERGEBEN:
        if alt_status != "Unzugewiesen":
            frappe.throw(_("«Nicht vergeben» ist nur aus «Unzugewiesen» möglich."))
        if not (doc.flags.status_bemerkung or "").strip():
            frappe.throw(_("Bitte «Nicht vergeben» über den Knopf setzen; die Bemerkung ist Pflicht."))

    # Solifonds: Status nur über die Knöpfe (und die Automatik)
    if doc.typ == SOLIFONDS and alt and doc.flags.status_quelle not in (QUELLE_KNOPF, QUELLE_AUTOMATIK):
        frappe.throw(_("Beim Solidaritätsfonds wird der Status über die Knöpfe gesetzt."))

    if doc.status in LAUFEND and not doc.get("kostengutsprache_am"):
        doc.kostengutsprache_am = now_datetime()

    protokolliere_status(doc, alt_status)


def protokolliere_status(doc, alt_status, parentfield="statusverlauf"):
    """Zeile im Statusverlauf; Quelle und Bemerkung über doc.flags (status_quelle, status_bemerkung)."""
    doc.append(parentfield, {
        "datum": now_datetime(),
        "von_status": alt_status,
        "nach_status": doc.status,
        "benutzer": frappe.session.user,
        "quelle": doc.flags.status_quelle or QUELLE_HAND,
        "bemerkung": doc.flags.status_bemerkung or (_("Mandat erstellt") if doc.is_new() else None)
    })


def set_status(doctype, name, status, quelle, bemerkung=None, parentfield="statusverlauf"):
    """Statuswechsel ohne save (z. B. aus einem Hook): Status und Verlaufszeile gemeinsam schreiben."""
    alt_status = frappe.db.get_value(doctype, name, "status")
    if alt_status == status:
        return
    werte = {"status": status}
    if status in LAUFEND and not frappe.db.get_value(doctype, name, "kostengutsprache_am"):
        werte["kostengutsprache_am"] = now_datetime()
    frappe.db.set_value(doctype, name, werte)
    idx = frappe.db.sql("""SELECT IFNULL(MAX(`idx`), 0) FROM `tabStatusaenderung`
        WHERE `parent` = %s AND `parenttype` = %s AND `parentfield` = %s""", (name, doctype, parentfield))[0][0]
    frappe.get_doc({
        "doctype": "Statusaenderung",
        "parent": name,
        "parenttype": doctype,
        "parentfield": parentfield,
        "idx": idx + 1,
        "datum": now_datetime(),
        "von_status": alt_status,
        "nach_status": status,
        "benutzer": frappe.session.user,
        "quelle": quelle,
        "bemerkung": bemerkung
    }).db_insert()


@frappe.whitelist()
def status_aendern(mandat, status, bemerkung=None):
    """Knöpfe im Mandat: «Nicht vergeben» (beide Typen), beim Solifonds «Abschliessen», «Rückzug», «Gelöscht»."""
    doc = frappe.get_doc("Mandat", mandat)
    if not doc.has_permission("write"):
        frappe.throw(_("Keine Berechtigung für dieses Mandat."), frappe.PermissionError)

    bemerkung = strip_html(bemerkung or "").strip() or None
    if status == NICHT_VERGEBEN:
        if doc.status != "Unzugewiesen":
            frappe.throw(_("«Nicht vergeben» ist nur aus «Unzugewiesen» möglich."))
        if not bemerkung:
            frappe.throw(_("Bitte eine Bemerkung angeben (ohne Personendaten)."))
    elif status in JEDERZEIT:
        if doc.status == status:
            frappe.throw(_("Das Mandat hat diesen Status bereits."))
    elif status == "Abgeschlossen":
        laufend = LAUFEND_SOLIFONDS if doc.typ == SOLIFONDS else LAUFEND_RSV
        if doc.typ == SOLIFONDS and doc.status != laufend:
            frappe.throw(_("Abschliessen ist beim Solidaritätsfonds nur aus «{0}» möglich.").format(laufend))
    else:
        frappe.throw(_("Dieser Status lässt sich hier nicht setzen."))

    doc.status = status
    doc.flags.status_quelle = QUELLE_KNOPF
    doc.flags.status_bemerkung = bemerkung
    doc.save()
    if bemerkung:
        doc.add_comment("Info", _("Status «{0}»: {1}").format(status, frappe.utils.escape_html(bemerkung)))
    return doc.status
