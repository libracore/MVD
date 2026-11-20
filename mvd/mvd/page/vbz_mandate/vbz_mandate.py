# -*- coding: utf-8 -*-
# Copyright (c) 2026, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.data import now_datetime
from mvd.mvd.doctype.mandat.mandat_permissions import get_va_kontaktpersonen
from mvd.mvd.doctype.mandat.mandat_status import ERLEDIGT, RSV

TYP_SPALTEN = {
    'Rechtsschutzversicherung': 'rsv',
    'Solidaritätsfonds': 's'
}

# ---------------------------------------------------------------------------
# Konfiguration der Seite: welche Abschnitte, in welcher Reihenfolge, aufgeklappt oder zu (#2239, #2243)
# ---------------------------------------------------------------------------
# Feste Abschnitte (Schlüssel -> Titel). Dazu kommt je Status ein Abschnitt «status:<Status>» mit der Liste der Mandate.
ABSCHNITTE = {
    'uebersicht': 'Übersicht nach Status',
    'zu_visieren': 'Zu visierende Mandate',
    'meine_offen': 'Meine offenen Mandate',
    'meine_erledigt': 'Meine erledigten Mandate',
}

# «Zu visierende Mandate»: RSV-Mandate ohne Visum in diesen Status (nur für die GL, sie setzt das Visum)
VISUM_STATUS = ('Gesuch eingereicht', 'Laufend (RSV)')

# Ansichten je Rolle: die ERSTE passende Zeile gilt.
#   wer:        'va' (Vertrauensanwält*in, sieht nur eigene Mandate), ein Rollenname (z. B. 'MV_Solifonds_GL') oder '*' (alle übrigen)
#   abschnitte: Liste (Abschnitt, aufgeklappt) in der gewünschten Reihenfolge; nicht aufgeführte Abschnitte erscheinen nicht.
#               'status:<Status>' = Liste der Mandate in diesem Status, 'status:*' = alle übrigen Status (Reihenfolge wie im Feld Status)
# «meine_offen» / «meine_erledigt» gibt es nur für VAs (sonst wären es alle Mandate der Sektion),
# «zu_visieren» nur für die GL (Rolle MV_Solifonds_GL). Es erscheinen nur Mandate, auf die Zugriff besteht (get_list).
ANSICHTEN = [
    ('va', [('meine_offen', True), ('meine_erledigt', False)]),
    ('MV_Solifonds_GL', [('zu_visieren', True), ('uebersicht', True), ('status:*', False)]),
    ('*', [('uebersicht', True), ('status:Unzugewiesen', True), ('status:*', False)]),
]


def get_ansicht(ist_va, status_optionen=None):
    """Abschnitte [{key, titel, offen, status?}] der ersten passenden Zeile in ANSICHTEN."""
    rollen = set(frappe.get_roles())
    status_optionen = status_optionen or []
    for wer, abschnitte in ANSICHTEN:
        if not (wer == '*' or (wer == 'va' and ist_va) or wer in rollen):
            continue
        genannt = set(key[len('status:'):] for key, offen in abschnitte if key.startswith('status:') and key != 'status:*')
        ergebnis = []
        for key, offen in abschnitte:
            if key == 'status:*':
                ergebnis += [{'key': 'status:' + st, 'titel': st, 'offen': 1 if offen else 0, 'status': st}
                             for st in status_optionen if st not in genannt]
            elif key.startswith('status:'):
                st = key[len('status:'):]
                if st in status_optionen:
                    ergebnis.append({'key': key, 'titel': st, 'offen': 1 if offen else 0, 'status': st})
            elif key in ABSCHNITTE:
                if key.startswith('meine_') and not ist_va:
                    continue
                if key == 'zu_visieren' and 'MV_Solifonds_GL' not in rollen:
                    continue
                ergebnis.append({'key': key, 'titel': ABSCHNITTE[key], 'offen': 1 if offen else 0})
        return ergebnis
    return []

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

    va_kontaktpersonen = get_va_kontaktpersonen()
    ist_va = va_kontaktpersonen is not None
    abschnitte = get_ansicht(ist_va, status_optionen)
    # Listen nur laden, wenn ein Abschnitt sie braucht
    mandate = get_mandate(status_optionen) if any(a['key'] != 'uebersicht' for a in abschnitte) else []
    if ist_va:
        # #2257: VAs dürfen unzugewiesene Mandate lesen (Link aus der Mail); «Meine Mandate» zeigt trotzdem nur die eigenen (#2250)
        mandate = [m for m in mandate if m.kontaktperson in va_kontaktpersonen]
    for a in abschnitte:
        if a['key'] == 'meine_offen':
            a['liste'] = [m for m in mandate if not m.erledigt]
        elif a['key'] == 'meine_erledigt':
            a['liste'] = [m for m in mandate if m.erledigt]
        elif a['key'] == 'zu_visieren':
            a['liste'] = [m for m in mandate if m.typ == RSV and not m.visum and m.status in VISUM_STATUS]
        elif a.get('status'):
            a['liste'] = [m for m in mandate if m.status == a['status']]
    return {
        'datenstand': now_datetime().strftime("%d.%m.%Y %H:%M:%S"),
        'ist_va': ist_va,
        'abschnitte': abschnitte,
        'status_liste': status_liste,
        'total': dict(total, summe=sum(total.values())),
        'hat_ohne_typ': total['ohne_typ'] > 0
    }


def get_mandate(status_optionen):
    # Nur Mandate, auf die Zugriff besteht: get_list prüft User Permissions (Sektion) und die VA-Einschränkung (#2206)
    # #2205: offene zuerst, erledigte danach; innerhalb nach Status, dann nach Erstellung
    mandate = frappe.get_list('Mandat',
        fields=['name', 'status', 'typ', 'mv_mitgliedschaft', 'kontaktperson', 'visum', 'fertigstellen_bis', 'creation'],
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
