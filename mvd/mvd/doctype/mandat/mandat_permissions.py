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

from __future__ import unicode_literals
import frappe

AUSNAHME_ROLLEN = {"System Manager", "MV_GL", "MV_Solifonds_GL", "MV_Solifonds_Vorpruefung"}


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


def has_permission(doc, ptype=None, user=None):
    """Einzelnes Mandat (Formular, get_doc + has_permission): VA nur eigene.
    None = Entscheid den Rollenrechten überlassen, False = gesperrt."""
    kontaktpersonen = get_va_kontaktpersonen(user)
    if kontaktpersonen is None:
        return None
    if ptype == "create" or doc.get("__islocal") or not doc.get("name"):
        # Neue Mandate entstehen über create_mandat (Beratung, eigene Prüfung); hier nicht blockieren
        return None
    return True if doc.get("kontaktperson") in kontaktpersonen else False
