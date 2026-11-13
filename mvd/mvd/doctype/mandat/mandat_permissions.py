# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt
#
# #2206: Vertrauensanwält*innen (VA) sehen nur ihre eigenen Mandate.
#
# Als VA gilt, wer als User an einer Termin Kontaktperson mit «Ist Vertrauensanwält*in» hängt.
# Eine VA sieht nur Mandate, deren Kontaktperson eine «ihrer» Kontaktpersonen ist; Mandate ohne VA
# und Mandate anderer VAs sieht sie nicht. Mitgliedschaften, Beratungen usw. bleiben unberührt.
# Die Sichtbarkeit ergibt sich direkt aus Kontaktperson und Mandat: keine Rolle und keine
# User Permissions zu pflegen, ein VA-Wechsel wirkt sofort.
# (MVZH arbeitet mit RSVMandat/RSVMitglied, nicht mit Mandat, und ist darum nicht betroffen.)
#
# Wer eine der AUSNAHME_ROLLEN hat, sieht weiterhin alle Mandate (Sektion über User Permission).
#
# Solifonds ab «Gesuch eingereicht»: Wer nur Rechtsberatung ist (MV_RB ohne eine der WEITERE_ROLLEN), darf das
# Mandat nur noch ansehen. Ausnahmen: die Knöpfe «Abschliessen» und «Rückzug» (RB_STATUS) und Anhänge hochladen.
# Kommentare und E-Mails aus dem Mandat gehen weiterhin (brauchen kein Schreibrecht). Weist die Vorprüfung das
# Gesuch zurück («Vorgemerkt»), ist das Mandat wieder bearbeitbar.

from __future__ import unicode_literals
import frappe
from mvd.mvd.doctype.mandat.mandat_status import SOLIFONDS, VOR_EINREICHUNG

AUSNAHME_ROLLEN = {"System Manager", "MV_GL", "MV_Solifonds_GL", "MV_Solifonds_Vorpruefung"}
# Wer eine dieser Rollen hat, ist nicht «nur RB»
WEITERE_ROLLEN = {"System Manager", "MV_MA", "MV_GL", "MV_Solifonds_GL", "MV_Solifonds_Vorpruefung"}
# Status, die «nur RB» auch nach dem Einreichen per Knopf setzen darf
RB_STATUS = ("Abgeschlossen", "Rückzug")
SCHREIBEN = ("write", "delete", "submit", "cancel", "amend")


def get_va_kontaktpersonen(user=None):
    """Kontaktpersonen, auf deren Mandate der User beschränkt ist.
    None = keine Einschränkung (keine VA oder Ausnahmerolle)."""
    user = user or frappe.session.user
    if user in ("Administrator", "Guest"):
        return None

    cache = getattr(frappe.local, "mandat_va_kontaktpersonen", None)
    if cache is None:
        cache = frappe.local.mandat_va_kontaktpersonen = {}
    if user in cache:
        return cache[user]

    kontaktpersonen = None
    if not AUSNAHME_ROLLEN & set(frappe.get_roles(user)):
        zeilen = frappe.db.sql("""
            SELECT `kp`.`name`, `kp`.`ist_vertrauensanwaeltin`
            FROM `tabTermin Kontaktperson Multi User` AS `mu`
            JOIN `tabTermin Kontaktperson` AS `kp` ON `kp`.`name` = `mu`.`parent`
            WHERE `mu`.`parenttype` = 'Termin Kontaktperson'
              AND `mu`.`user` = %s
        """, user, as_dict=True)
        if any(z.ist_vertrauensanwaeltin for z in zeilen):
            # Sichtbar sind die Mandate aller eigenen Kontaktpersonen
            kontaktpersonen = sorted(set(z.name for z in zeilen))

    cache[user] = kontaktpersonen
    return kontaktpersonen


def get_permission_query_conditions(user=None):
    """Listen, Berichte, get_list: VA nur eigene Mandate."""
    kontaktpersonen = get_va_kontaktpersonen(user)
    if kontaktpersonen is None:
        return ""
    return "`tabMandat`.`kontaktperson` IN ({0})".format(
        ", ".join(frappe.db.escape(kp, percent=False) for kp in kontaktpersonen))


def ist_nur_rb(user=None):
    rollen = set(frappe.get_roles(user or frappe.session.user))
    return "MV_RB" in rollen and not (WEITERE_ROLLEN & rollen)


def ist_rb_gesperrt(doc, user=None):
    """Solifonds ab «Gesuch eingereicht» und User nur RB: nur noch ansehen.
    Massgebend ist der gespeicherte Stand, nicht der (evtl. geänderte) im Formular."""
    if doc.get("__islocal") or not doc.get("name") or not ist_nur_rb(user):
        return False
    gespeichert = frappe.db.get_value("Mandat", doc.get("name"), ["typ", "status"], as_dict=True)
    return bool(gespeichert) and gespeichert.typ == SOLIFONDS and gespeichert.status not in VOR_EINREICHUNG


def _rb_ausnahme(ptype):
    # Knöpfe «Abschliessen»/«Rückzug» (mandat_status.status_aendern setzt das Flag)
    if frappe.flags.get("mandat_rb_status"):
        return True
    # Anhang hochladen: File prüft dafür Schreibrecht auf dem Mandat
    form = frappe.form_dict or {}
    return ptype == "write" and form.get("cmd") == "upload_file" and form.get("doctype") == "Mandat"


def has_permission(doc, ptype=None, user=None):
    """Einzelnes Mandat (Formular, get_doc + has_permission): VA nur eigene; Solifonds nach dem Einreichen
    für «nur RB» nur lesen. None = Entscheid den Rollenrechten überlassen, False = gesperrt."""
    if ptype in SCHREIBEN and ist_rb_gesperrt(doc, user) and not _rb_ausnahme(ptype):
        return False
    kontaktpersonen = get_va_kontaktpersonen(user)
    if kontaktpersonen is None:
        return None
    if ptype == "create" or doc.get("__islocal") or not doc.get("name"):
        # Neue Mandate entstehen über create_mandat (Beratung, eigene Prüfung); hier nicht blockieren
        return None
    return True if doc.get("kontaktperson") in kontaktpersonen else False
