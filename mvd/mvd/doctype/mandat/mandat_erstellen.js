// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

// Dialog "Mandat erstellen" für das Formular Beratung.
// Wird über hooks.py (doctype_js "Beratung") geladen.

frappe.provide('frappe.mvd.mandat');

frappe.mvd.mandat.UEBERNEHMEN = 'Ich übernehme das Mandat';
frappe.mvd.mandat.NICHT_UEBERNEHMEN = 'Ich kann das Mandat nicht übernehmen';
frappe.mvd.mandat.SOLIFONDS = 'Solidaritätsfonds';
frappe.mvd.mandat.MANGELS_RS = 'mangels Rechtsschutzdeckung';

// Kriterien gemäss Antragsformular Punkt 2, nur bei "mangels Rechtsschutzdeckung"
frappe.mvd.mandat.KRITERIEN = [
    ['kriterium_notlage', 'Mietrechtliche Notlage'],
    ['kriterium_vermoegenseinbussen', 'Drohende oder eingetretene Vermögenseinbussen'],
    ['kriterium_erfolgsaussichten', 'Erfolgsaussichten im Verfahren'],
    ['kriterium_finanzielle_notlage', 'Glaubhaft gemachte finanzielle Notlage'],
    ['kriterium_keine_rs_deckung', 'Glaubhaft fehlende Rechtsschutzdeckung ausserhalb MVB']
];

frappe.mvd.mandat.erstellen = function(frm) {
    if (!frm.doc.mv_mitgliedschaft) {
        frappe.msgprint({
            title: __('Kein Mitglied'),
            indicator: 'red',
            message: __('Ein Mandat ist nur für Beratungen mit Mitglied möglich. Bitte zuerst die Beratung einem Mitglied zuordnen und speichern.')
        });
        return;
    }
    if (!frm.doc.beratungskategorie) {
        frappe.msgprint({
            title: __('Beratungskategorie fehlt'),
            indicator: 'red',
            message: __('Bitte zuerst in der Beratung die Beratungskategorie setzen und speichern.')
        });
        return;
    }
    // Ins Mandat kopiert wird die gespeicherte Beratung, darum keine ungespeicherten Änderungen zulassen
    if (frm.is_dirty()) {
        frappe.msgprint({
            title: __('Beratung nicht gespeichert'),
            indicator: 'red',
            message: __('Bitte zuerst die Beratung speichern.')
        });
        return;
    }

    // Eigene Vertrauensanwält*in (Termin Kontaktperson) der angemeldeten Person ermitteln
    frappe.call({
        method: "mvd.mvd.doctype.beratung.beratung.uebernahme",
        args: {
            'beratung': frm.doc.name,
            'user': frappe.session.user
        },
        callback: function(r) {
            let eigene_va = r.message || null;
            // Nur Beratungskategorien vorschlagen, die es noch gibt (Altdaten enthalten gelöschte)
            let kategorien = [frm.doc.beratungskategorie, frm.doc.beratungskategorie_2, frm.doc.beratungskategorie_3]
                .filter((k, i, a) => k && a.indexOf(k) === i);
            frappe.db.get_list('Beratungskategorie', {'filters': {'name': ['in', kategorien]}, 'fields': ['name'], 'limit': 3}).then(vorhanden => {
                let namen = vorhanden.map(k => k.name);
                let themen = kategorien.filter(k => namen.includes(k));
                // Meta der Thema-Tabelle wird vom Table-MultiSelect-Feld im Dialog benötigt
                frappe.model.with_doctype('RSV Thema MultiTable', function() {
                    frappe.mvd.mandat.erstellen_dialog(frm, eigene_va, themen);
                });
            });
        }
    });
};

frappe.mvd.mandat.erstellen_dialog = function(frm, eigene_va, themen) {
    // Vorbelegung: selbst Berater*in der Beratung -> übernehmen; keine eigene VA -> nicht übernehmen
    let uebernahme_default = '';
    if (eigene_va && frm.doc.kontaktperson == eigene_va) {
        uebernahme_default = frappe.mvd.mandat.UEBERNEHMEN;
    } else if (!eigene_va) {
        uebernahme_default = frappe.mvd.mandat.NICHT_UEBERNEHMEN;
    }

    let ist_solifonds = `eval:doc.typ=="${frappe.mvd.mandat.SOLIFONDS}"`;
    let ist_mangels_rs = `eval:doc.typ=="${frappe.mvd.mandat.SOLIFONDS}" && doc.solifonds_art=="${frappe.mvd.mandat.MANGELS_RS}"`;

    let d = new frappe.ui.Dialog({
        title: 'Mandat erstellen',
        fields: [
            {'fieldname': 'prozess_html', 'fieldtype': 'HTML', 'options': '<div class="alert alert-info">Platzhalter: Hier folgt die Beschreibung des Mandats-Prozesses.</div>'},
            {'fieldname': 'thema', 'fieldtype': 'Table MultiSelect', 'label': 'Thema', 'options': 'RSV Thema MultiTable', 'reqd': 1,
             'description': 'Vorgeschlagen aus den Beratungskategorien der Beratung.'},
            {'fieldname': 'uebernahme', 'fieldtype': 'Select', 'label': 'Übernahme', 'reqd': 1,
             'options': ['', frappe.mvd.mandat.UEBERNEHMEN, frappe.mvd.mandat.NICHT_UEBERNEHMEN].join('\n'), 'default': uebernahme_default,
             'change': function() {
                if (d.get_value('uebernahme') == frappe.mvd.mandat.UEBERNEHMEN && !eigene_va) {
                    d.set_value('uebernahme', frappe.mvd.mandat.NICHT_UEBERNEHMEN);
                    frappe.msgprint({
                        title: __('Keine Vertrauensanwält*in'),
                        indicator: 'red',
                        message: __('Sie sind keiner Vertrauensanwält*in zugeordnet und können das Mandat darum nicht selbst übernehmen.')
                    });
                }
             }
            },
            {'fieldname': 'seki_hinweis', 'fieldtype': 'HTML', 'options': '<p class="text-muted">Das Sekretariat bemüht sich um eine geeignete VA.</p>', 'depends_on': `eval:doc.uebernahme=="${frappe.mvd.mandat.NICHT_UEBERNEHMEN}"`},
            {'fieldname': 'typ', 'fieldtype': 'Select', 'label': 'Typ', 'reqd': 1, 'options': "Rechtsschutzversicherung\nSolidaritätsfonds", 'default': 'Rechtsschutzversicherung'},
            {'fieldname': 'solifonds_art', 'fieldtype': 'Select', 'label': 'Antrag auf Kostengutsprache',
             'options': ['', frappe.mvd.mandat.MANGELS_RS, 'aus ideellen Gründen'].join('\n'), 'depends_on': ist_solifonds,
             'description': "mangels Rechtsschutzdeckung (Karenzfrist, Geschäfts-/Kollektivmitglied): Kostendach CHF 3'000 pro Instanz, Entscheid GL · aus ideellen Gründen / Rechtssicherheit: Kostendach CHF 8'000 (2 Instanzen), Entscheid Vorstand"},
            {'fieldname': 'kriterien_html', 'fieldtype': 'HTML', 'options': '<p class="text-muted">Geprüfte Kriterien (Antragsformular Punkt 2)</p>', 'depends_on': ist_mangels_rs}
        ].concat(frappe.mvd.mandat.KRITERIEN.map(k => (
            {'fieldname': k[0], 'fieldtype': 'Check', 'label': k[1], 'depends_on': ist_mangels_rs}
        ))).concat([
            {'fieldname': 'solifonds_begruendung', 'fieldtype': 'Small Text', 'label': 'Begründung', 'depends_on': ist_solifonds,
             'description': 'Erscheint im PDF für das Mitglied. Ohne Personendaten – wird dem Vorstand anonymisiert angezeigt. Darf bei der Vorerfassung leer bleiben («keine Musse»), ist zum Einreichen aber Pflicht.'},
            {'fieldname': 'bemerkung', 'fieldtype': 'Small Text', 'label': 'Bemerkungen', 'description': 'Wird im Mandat gespeichert und ist für alle sichtbar, die das Mandat sehen. Wird nicht an die VA gemailt.'},
            {'fieldname': 'persoenliche_bemerkung', 'fieldtype': 'Small Text', 'label': 'Persönliche Bemerkung', 'depends_on': `eval:doc.uebernahme=="${frappe.mvd.mandat.UEBERNEHMEN}"`, 'description': 'Wird im Mandat gespeichert und in der Bestätigungsmail an die VA mitgeschickt (nur Typ Rechtsschutzversicherung).'},
            {'fieldname': 'fall_verfolgen', 'fieldtype': 'Check', 'label': 'Fall verfolgen'}
        ]),
        primary_action_label: 'Erstellen',
        primary_action: function(values) {
            let uebernehmen = values.uebernahme == frappe.mvd.mandat.UEBERNEHMEN;
            let solifonds = values.typ == frappe.mvd.mandat.SOLIFONDS;
            if (solifonds && !values.solifonds_art) {
                frappe.msgprint(__('Bitte wählen, worauf sich der Antrag auf Kostengutsprache stützt.'));
                return;
            }

            frappe.call({
                "method": "mvd.mvd.doctype.mandat.mandat.create_mandat",
                "args": {
                    "beratung": frm.doc.name,
                    "berater_in": uebernehmen ? eigene_va : null,
                    "typ": values.typ,
                    "bemerkung": values.bemerkung,
                    "persoenliche_bemerkung": uebernehmen ? values.persoenliche_bemerkung : null,
                    "thema": (values.thema || []).map(row => row.thema).filter(thema => thema),
                    "fall_verfolgen": values.fall_verfolgen ? 1 : 0,
                    "solifonds_art": solifonds ? values.solifonds_art : null,
                    "solifonds_begruendung": solifonds ? values.solifonds_begruendung : null,
                    "kriterien": solifonds ? frappe.mvd.mandat.KRITERIEN.map(k => k[0]).filter(k => values[k]) : []
                },
                "callback": function(r) {
                    d.hide();
                    frm.reload_doc();
                    frappe.msgprint(`Das Mandat (${r.message}) wurde erstellt.`);
                }
            });
        }
    });

    // Themen mit den Beratungskategorien der Beratung vorbelegen
    d.set_value('thema', (themen || []).map(k => ({'thema': k})));

    d.show();
};
