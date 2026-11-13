// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

// Dialog "Mandat erstellen" für das Formular Beratung.
// Wird über hooks.py (doctype_js "Beratung") geladen.

frappe.provide('frappe.mvd.mandat');

frappe.mvd.mandat.UEBERNEHMEN = 'Ich übernehme das Mandat';
frappe.mvd.mandat.NICHT_UEBERNEHMEN = 'Ich kann das Mandat nicht übernehmen';
frappe.mvd.mandat.SOLIFONDS = 'Solidaritätsfonds';
frappe.mvd.mandat.MANGELS_RS = 'mangels Rechtsschutzdeckung';
frappe.mvd.mandat.SPRACHNAMEN = {'de': 'Deutsch', 'fr': 'Französisch'};

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
            Promise.all([
                frappe.db.get_list('Beratungskategorie', {'filters': {'name': ['in', kategorien]}, 'fields': ['name'], 'limit': 3}),
                // #2211: Verfahrenssprache aus der Mitgliedschaft vorbelegen
                frappe.xcall('mvd.mvd.doctype.mandat.mandat.get_mitglied_sprache', {'beratung': frm.doc.name})
            ]).then(([vorhanden, sprache]) => {
                let namen = vorhanden.map(k => k.name);
                let themen = kategorien.filter(k => namen.includes(k));
                frappe.mvd.mandat.erstellen_dialog(frm, eigene_va, themen, sprache);
            });
        }
    });
};

frappe.mvd.mandat.erstellen_dialog = function(frm, eigene_va, themen, sprache) {
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
            {'fieldname': 'beratungskategorie', 'fieldtype': 'Link', 'label': 'Beratungskategorie', 'options': 'Beratungskategorie', 'reqd': 1,
             'description': 'Aus der Beratung übernommen, änderbar.',
             // Link-Felder setzen den Wert erst nach der Prüfung auf dem Server – danach (2)/(3) sofort ein-/ausblenden
             'change': () => d.refresh_dependency()},
            {'fieldname': 'beratungskategorie_2', 'fieldtype': 'Link', 'label': '(2) Beratungskategorie', 'options': 'Beratungskategorie', 'depends_on': 'eval:doc.beratungskategorie',
             'change': () => d.refresh_dependency()},
            {'fieldname': 'beratungskategorie_3', 'fieldtype': 'Link', 'label': '(3) Beratungskategorie', 'options': 'Beratungskategorie', 'depends_on': 'eval:doc.beratungskategorie_2'},
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
            {'fieldname': 'sprache', 'fieldtype': 'Select', 'label': 'Verfahrenssprache', 'options': ['', 'de', 'fr'].join('\n'), 'default': sprache || '',
             'description': 'de = Deutsch, fr = Französisch. ' + (sprache ? `Aus der Mitgliedschaft übernommen (${frappe.mvd.mandat.SPRACHNAMEN[sprache]}), änderbar.`
                 : 'In der Mitgliedschaft ist keine Sprache hinterlegt.')},
            {'fieldname': 'typ', 'fieldtype': 'Select', 'label': 'Typ', 'reqd': 1, 'options': "Rechtsschutzversicherung\nSolidaritätsfonds", 'default': 'Rechtsschutzversicherung',
             'change': () => pflicht_markieren()},
            {'fieldname': 'solifonds_art', 'fieldtype': 'Select', 'label': 'Antrag auf Kostengutsprache',
             'options': ['', frappe.mvd.mandat.MANGELS_RS, 'aus ideellen Gründen'].join('\n'), 'depends_on': ist_solifonds,
             'change': () => pflicht_markieren(),
             'description': "mangels Rechtsschutzdeckung (Karenzfrist, Geschäfts-/Kollektivmitglied): Kostendach CHF 3'000 pro Instanz, Entscheid GL · aus ideellen Gründen / Rechtssicherheit: Kostendach CHF 8'000 (2 Instanzen), Entscheid Vorstand"},
            {'fieldname': 'kriterien_html', 'fieldtype': 'HTML', 'options': '<p class="text-muted">Geprüfte Kriterien (Antragsformular Punkt 2). <b>Alle Kriterien müssen erfüllt sein (kumulativ)</b> und angekreuzt werden, sonst kann das Mandat nicht erstellt werden.</p>', 'depends_on': ist_mangels_rs}
        ].concat(frappe.mvd.mandat.KRITERIEN.map(k => (
            {'fieldname': k[0], 'fieldtype': 'Check', 'label': k[1], 'depends_on': ist_mangels_rs, 'change': () => pflicht_markieren()}
        ))).concat([
            {'fieldname': 'solifonds_begruendung', 'fieldtype': 'Small Text', 'label': 'Begründung', 'depends_on': ist_solifonds,
             'change': () => pflicht_markieren(),
             'description': 'Erscheint im PDF für das Mitglied. Ohne Personendaten – wird dem Vorstand anonymisiert angezeigt.'},
            {'fieldname': 'bemerkung', 'fieldtype': 'Small Text', 'label': 'Bemerkungen', 'description': 'Wird im Mandat gespeichert und ist für alle sichtbar, die das Mandat sehen. Wird nicht an die VA gemailt.'},
            {'fieldname': 'persoenliche_bemerkung', 'fieldtype': 'Small Text', 'label': 'Persönliche Bemerkung', 'depends_on': `eval:doc.uebernahme=="${frappe.mvd.mandat.UEBERNEHMEN}"`, 'description': 'Wird im Mandat gespeichert und in der Bestätigungsmail an die VA mitgeschickt (nur Typ Rechtsschutzversicherung).'},
            // «Fall verfolgen» ist nur für GL und Vorprüfung
            {'fieldname': 'fall_verfolgen', 'fieldtype': 'Check', 'label': 'Fall verfolgen', 'hidden': frappe.user.has_role(['MV_Solifonds_GL', 'MV_Solifonds_Vorpruefung']) ? 0 : 1}
        ]),
        primary_action_label: 'Erstellen',
        primary_action: function(values) {
            let uebernehmen = values.uebernahme == frappe.mvd.mandat.UEBERNEHMEN;
            let solifonds = values.typ == frappe.mvd.mandat.SOLIFONDS;
            if (solifonds && !values.solifonds_art) {
                frappe.msgprint(__('Bitte wählen, worauf sich der Antrag auf Kostengutsprache stützt.'));
                return;
            }
            if (solifonds && !(values.solifonds_begruendung || '').trim()) {
                frappe.msgprint(__('Bitte eine Begründung für das Solifonds-Gesuch erfassen.'));
                return;
            }
            // #2218: bei «mangels Rechtsschutzdeckung» alle Kriterien Pflicht (kumulativ)
            if (solifonds && values.solifonds_art == frappe.mvd.mandat.MANGELS_RS) {
                let fehlend = frappe.mvd.mandat.KRITERIEN.filter(k => !values[k[0]]).map(k => k[1]);
                if (fehlend.length) {
                    frappe.msgprint({
                        title: __('Kriterien nicht erfüllt'),
                        indicator: 'red',
                        message: __('Bei «mangels Rechtsschutzdeckung» müssen alle Kriterien erfüllt sein (kumulativ). Es fehlt noch:') +
                            '<ul>' + fehlend.map(f => '<li>' + f + '</li>').join('') + '</ul>'
                    });
                    return;
                }
            }

            // Mehrfachklick: Knopf bis zur Antwort sperren (Server prüft zusätzlich)
            let btn = d.get_primary_btn();
            if (btn.prop('disabled')) {
                return;
            }
            btn.prop('disabled', true);
            frappe.call({
                "method": "mvd.mvd.doctype.mandat.mandat.create_mandat",
                "freeze": true,
                "freeze_message": __('Mandat wird erstellt …'),
                "always": () => btn.prop('disabled', false),
                "args": {
                    "beratung": frm.doc.name,
                    "berater_in": uebernehmen ? eigene_va : null,
                    "typ": values.typ,
                    "sprache": values.sprache || null,
                    "bemerkung": values.bemerkung,
                    "persoenliche_bemerkung": uebernehmen ? values.persoenliche_bemerkung : null,
                    "beratungskategorien": [values.beratungskategorie, values.beratungskategorie_2, values.beratungskategorie_3].filter(k => k),
                    "fall_verfolgen": values.fall_verfolgen ? 1 : 0,
                    "solifonds_art": solifonds ? values.solifonds_art : null,
                    "solifonds_begruendung": solifonds ? values.solifonds_begruendung : null,
                    "kriterien": solifonds ? frappe.mvd.mandat.KRITERIEN.map(k => k[0]).filter(k => values[k]) : []
                },
                "callback": function(r) {
                    d.hide();
                    frm.reload_doc();
                    frappe.mvd.mandat.rueckmeldung(frm, r.message, values, uebernehmen, solifonds);
                }
            });
        }
    });

    // Pflicht je nach Typ/Antrag (v12 kennt kein mandatory_depends_on): «Antrag auf Kostengutsprache» und Begründung bei Solidaritätsfonds,
    // die Kriterien bei «mangels Rechtsschutzdeckung». reqd nur setzen, solange das Feld sichtbar ist – sonst blockiert der
    // Dialog wegen eines ausgeblendeten Felds. Checkboxen markiert Frappe nicht (0 gilt nicht als leer), darum selbst rot.
    function pflicht_markieren() {
        let solifonds = d.get_value('typ') == frappe.mvd.mandat.SOLIFONDS;
        let mangels_rs = solifonds && d.get_value('solifonds_art') == frappe.mvd.mandat.MANGELS_RS;
        let art = d.get_field('solifonds_art');
        if (cint(art.df.reqd) != cint(solifonds)) {
            d.set_df_property('solifonds_art', 'reqd', solifonds ? 1 : 0);
        }
        if (cint(d.get_field('solifonds_begruendung').df.reqd) != cint(solifonds)) {
            d.set_df_property('solifonds_begruendung', 'reqd', solifonds ? 1 : 0);
        }
        frappe.mvd.mandat.KRITERIEN.forEach(k => {
            let feld = d.get_field(k[0]);
            feld.df.reqd = mangels_rs ? 1 : 0;
            feld.$wrapper.toggleClass('has-error', mangels_rs && !d.get_value(k[0]));
            feld.$wrapper.find('label').toggleClass('bold', mangels_rs);
        });
    }

    // Beratungskategorien (1)-(3) aus der Beratung vorbelegen
    d.set_values({
        'beratungskategorie': (themen || [])[0] || '',
        'beratungskategorie_2': (themen || [])[1] || '',
        'beratungskategorie_3': (themen || [])[2] || ''
    });

    d.show();
    pflicht_markieren();
};

// Rückmeldung nach dem Erstellen: was jetzt zu tun ist (RSV übernommen: bei der Coop einreichen;
// Solifonds: gleich einreichen? – Später / Ja)
frappe.mvd.mandat.rueckmeldung = function(frm, mandat, values, uebernehmen, solifonds) {
    let link = `<a href="#Form/Mandat/${encodeURIComponent(mandat)}">${frappe.utils.escape_html(mandat)}</a>`;
    if (!uebernehmen) {
        frappe.msgprint({
            title: __('Mandat erstellt'),
            indicator: 'blue',
            message: __('Das Mandat {0} ist erstellt (Status «Unzugewiesen»). Das Sekretariat sucht eine Vertrauensanwält*in.', [link])
        });
    } else if (!solifonds) {
        frappe.msgprint({
            title: __('Mandat erstellt'),
            indicator: 'green',
            message: __('Das Mandat {0} ist erstellt (Status «Vorgemerkt»), die Infos werden dir per E-Mail geschickt.', [link]) +
                '<br><br><b>' + __('Bitte das Gesuch mit der in der E-Mail angegebenen CC-Adresse bei der Coop Rechtsschutzversicherung einreichen.') +
                '</b> ' + __('Dann wird das Mandat automatisch als «Gesuch eingereicht» markiert.')
        });
    } else {
        // Solifonds selbst übernommen: Begründung ist beim Erstellen Pflicht, darum kann gleich eingereicht werden
        let f = new frappe.ui.Dialog({
            title: __('Mandat erstellt'),
            fields: [{'fieldname': 'text', 'fieldtype': 'HTML', 'options':
                '<p>' + __('Das Mandat {0} ist erstellt (Status «Vorgemerkt»).', [link]) + '</p>' +
                '<p><b>' + __('Soll das Solifonds-Gesuch jetzt zur Vorprüfung eingereicht werden?') + '</b></p>' +
                '<p class="text-muted">' + __('Mit «Später» bleibt es vorgemerkt; einreichen dann im Mandat über «Solidaritätsfonds → Gesuch einreichen».') + '</p>'}],
            primary_action_label: __('Ja, jetzt einreichen'),
            primary_action: function() {
                f.get_primary_btn().prop('disabled', true);
                frappe.call({
                    method: 'mvd.mvd.doctype.mandat.solifonds.gesuch_einreichen',
                    args: {'mandat': mandat},
                    freeze: true,
                    always: () => f.get_primary_btn().prop('disabled', false),
                    callback: function() {
                        f.hide();
                        frappe.msgprint({
                            title: __('Gesuch eingereicht'),
                            indicator: 'green',
                            message: __('Das Solifonds-Gesuch {0} ist zur Vorprüfung eingereicht (Status «Gesuch eingereicht»).', [link])
                        });
                    }
                });
            }
        });
        // «Später» als eigener Knopf links vom Primärknopf (secondary_action liefe in v12 bei jedem Schliessen)
        $(`<button class="btn btn-default btn-sm" style="margin-right: 5px;">${__('Später')}</button>`)
            .insertBefore(f.get_primary_btn())
            .on('click', () => f.hide());
        f.show();
    }
};
