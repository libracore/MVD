# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

# Abstimmung des Vorstands über einen anonymisierten Solifonds-Antrag (#2183).
# Zugang ohne Login über den persönlichen Token aus der Mail.

from __future__ import unicode_literals
import frappe
from mvd.mvd.doctype.mandat.solifonds import get_stimme_per_token, get_abstimmung_stand

no_cache = 1

def get_context(context):
    context.no_cache = 1
    token = frappe.form_dict.get("token")
    zeile = get_stimme_per_token(token)
    if not zeile:
        context.ungueltig = 1
        return context

    mandat = frappe.get_doc("Mandat", zeile.parent)
    # Nur anonymisierte Angaben, keine Personen- oder Adressdaten
    context.token = token
    context.fall = mandat.name
    context.offen = 1 if mandat.status == "Antrag Vorstand" else 0
    context.status = mandat.status
    context.art = mandat.solifonds_art or ""
    context.kostendach = frappe.utils.fmt_money(mandat.kostendach or 0, precision=0)
    from mvd.mvd.doctype.mandat.mandat import get_beratungskategorien_text
    context.themen = get_beratungskategorien_text(mandat)
    context.begruendung = mandat.solifonds_begruendung or ""
    context.vorpruefung = mandat.vorpruefung_begruendung or ""
    context.stellungnahme_gl = mandat.entscheid_bemerkung or ""
    context.meine_stimme = zeile.stimme or ""
    context.mein_kommentar = zeile.kommentar or ""
    context.stand = get_abstimmung_stand(mandat)
    return context
