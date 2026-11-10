# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.data import now_datetime
from mvd.mvd.doctype.mandat.mandat_permissions import get_va_kontaktpersonen
from mvd.mvd.doctype.mandat.mandat_status import ERLEDIGT

TYP_SPALTEN = {
    'Rechtsschutzversicherung': 'rsv',
    'Solidaritätsfonds': 's'
}

@frappe.whitelist()
def get_status_uebersicht():
    # Eine Abfrage; Sektionstrennung über User Permissions (get_list)
    anzahl = {}
    for row in frappe.get_list('Mandat', fields=['status', 'typ', 'count(`name`) as anzahl'], group_by='status, typ', order_by='status'):
        status = anzahl.setdefault(row.status or '', {'rsv': 0, 's': 0, 'ohne_typ': 0})
        status[TYP_SPALTEN.get(row.typ, 'ohne_typ')] += row.anzahl

    # Reihenfolge wie im Select-Feld, Status ohne Mandate mit 0
    status_optionen = [s.strip() for s in (frappe.get_meta('Mandat').get_field('status').options or '').split('\n') if s.strip()]
    status_reihenfolge = status_optionen + [s for s in anzahl if s not in status_optionen]  # Altdaten, leerer Status

    status_liste = []
    total = {'rsv': 0, 's': 0, 'ohne_typ': 0}
    for status in status_reihenfolge:
        werte = anzahl.get(status, {'rsv': 0, 's': 0, 'ohne_typ': 0})
        status_liste.append(dict(werte, status=status, summe=sum(werte.values())))
        for spalte in total:
            total[spalte] += werte[spalte]

    ist_va = get_va_kontaktpersonen() is not None
    meine_mandate = get_meine_mandate(status_optionen) if ist_va else []
    return {
        'datenstand': now_datetime().strftime("%d.%m.%Y %H:%M:%S"),
        'ist_va': ist_va,
        'meine_mandate': meine_mandate,
        'meine_mandate_offen': len([m for m in meine_mandate if not m.erledigt]),
        'status_liste': status_liste,
        'total': dict(total, summe=sum(total.values())),
        'hat_ohne_typ': total['ohne_typ'] > 0
    }


def get_meine_mandate(status_optionen):
    # #2206: Mandate der Vertrauensanwält*in (Einschränkung über mandat_permissions, get_list)
    # #2205: alle zugewiesenen, egal welcher Status; offene zuerst, erledigte danach
    mandate = frappe.get_list('Mandat',
        fields=['name', 'status', 'typ', 'mv_mitgliedschaft', 'fertigstellen_bis', 'creation'],
        order_by='creation asc', limit_page_length=0)

    mitglieder = {}
    ids = list(set(m.mv_mitgliedschaft for m in mandate if m.mv_mitgliedschaft))
    if ids:
        for mg in frappe.get_all('Mitgliedschaft', filters={'name': ['in', ids]},
                fields=['name', 'mitglied_nr', 'vorname_1', 'nachname_1', 'firma']):
            name = " ".join(x for x in (mg.vorname_1, mg.nachname_1) if x) or mg.firma or ''
            mitglieder[mg.name] = {'mitglied_nr': mg.mitglied_nr or mg.name, 'mitglied_name': name}

    reihenfolge = dict((status, i) for i, status in enumerate(status_optionen))
    for m in mandate:
        m.update(mitglieder.get(m.mv_mitgliedschaft, {'mitglied_nr': m.mv_mitgliedschaft or '', 'mitglied_name': ''}))
        m.typ_kurz = TYP_SPALTEN.get(m.typ, '').upper() or '–'
        m.erledigt = 1 if m.status in ERLEDIGT else 0
    mandate.sort(key=lambda m: (m.erledigt, reihenfolge.get(m.status, len(reihenfolge)), m.creation))
    return mandate
