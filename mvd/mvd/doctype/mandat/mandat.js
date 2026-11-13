// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

{% include "mvd/mvd/doctype/mandat/solifonds_dialoge.js" %}

frappe.ui.form.on('Mandat', {
    refresh: function(frm) {
        // Solifonds nach dem Einreichen: «nur RB» darf nur noch ansehen (Server: mandat_permissions.ist_rb_gesperrt);
        // möglich bleiben Abschliessen, Rückzug und Anhänge
        if (rb_gesperrt(frm)) {
            frm.set_read_only();
            frm.refresh_fields();
            frm.disable_save();
        }
        // Hinweis oben: was jetzt ansteht, je nach Status und Rolle
        status_hinweis(frm);

        // Mitgliedschaftsübersicht wie in der Beratung
        load_html_overview(frm);
        frappe.mvd.schlichtungsbehoerde_listener(frm, 'uebersicht_html');

        // «Fall verfolgen» sehen alle, setzen nur GL und Vorprüfung; Visum (nur RSV) setzt nur die GL (#2210)
        frm.set_df_property('fall_verfolgen', 'read_only', frappe.user.has_role(['MV_Solifonds_GL', 'MV_Solifonds_Vorpruefung']) ? 0 : 1);
        frm.set_df_property('visum', 'read_only', frappe.user.has_role('MV_Solifonds_GL') ? 0 : 1);
        // Mitglied und Beratung kommen aus create_mandat; ändern nur System Manager
        ['mv_mitgliedschaft', 'beratung'].forEach(function(f) {
            frm.set_df_property(f, 'read_only', (frm.is_new() || frappe.user.has_role('System Manager')) ? 0 : 1);
        });
        // «Bestätigungs-E-Mail gesendet» setzt das System; «nur RB» darf es nicht ändern
        frm.set_df_property('bestaetigungs_email_gesendet', 'read_only', (frm.doc.__onload || {}).nur_rb ? 1 : 0);

        // #2205: Status, Typ und VA je nach Status; Knöpfe für Nicht vergeben / Abschliessen / Rückzug / Gelöscht
        setup_status_felder(frm);
        add_status_buttons(frm);

        // #2213: Schlichtungsbehörde nachträglich ermitteln, falls sie beim Erstellen nicht gefunden wurde
        if (!frm.is_new() && frm.doc.mv_mitgliedschaft && !frm.doc.schlichtungsbehoerde && frm.perm[0].write) {
            frm.add_custom_button(__('Schlichtungsbehörde ermitteln'), function() {
                frappe.call({
                    method: 'mvd.mvd.doctype.mandat.mandat.schlichtungsbehoerde_ermitteln',
                    args: {'mandat': frm.doc.name},
                    freeze: true,
                    callback: function() { frm.reload_doc(); }
                });
            });
        }

        // Ablauf Solidaritätsfonds (#2183)
        if (!frm.is_new() && frm.doc.typ == 'Solidaritätsfonds') {
            add_solifonds_buttons(frm);
        }

        // Pool darf nicht zugeordnet werden
        frm.set_query('kontaktperson', function() {
            return {
                filters: [
                    ['Termin Kontaktperson', 'name', 'not like', '%pool%']
                ]
            };
        });

        if (!frm.is_new() && !frm.doc.kontaktperson) {
            frm.add_custom_button(__('Suche Vertrauensanwält*in'), function() {
                // #2211: Mit Verfahrenssprache zuerst fragen, ob nur VAs mit dieser Sprache angeschrieben werden
                frappe.mvd.mandat.frage_sprache(frm, suche_va);
            });
        }

        function suche_va(nur_sprache) {
                frappe.call({
                    method: 'mvd.mvd.doctype.mandat.mandat.suche_vertrauensanwaeltin',
                    args: {
                        "mandat_id": frm.doc.name,
                        "sektion_id": frm.doc.sektion_id,
                        "nur_sprache": nur_sprache ? 1 : 0
                    },
                    freeze: true,
                    callback: function(r) {
                        if (!r.exc && r.message) {
                            var mail_data = r.message;
                            var current_user_sender = frappe.session.user_fullname + " <" + frappe.session.user + ">";
                            
                            new frappe.mvd.MailComposer({
                                doc: frm.doc,
                                frm: frm,
                                subject: mail_data.subject,      
                                recipients: mail_data.recipients, 
                                cc: mail_data.cc,
                                attach_document_print: false,
                                txt: '',    
                                email_template: mail_data.email_template,       
                                last_email: '',                   
                                is_a_reply: false,                
                                sender: current_user_sender                        
                            });
                        }
                    }
                });
        }
    },
    mv_mitgliedschaft: function(frm) {
        load_html_overview(frm);
    },
    typ: function(frm) {
        setup_status_felder(frm);
    },
    email_1: function(frm) {
        open_mandat_email(frm, 'mandat_email_1');
    },
    email_2: function(frm) {
        open_mandat_email(frm, 'mandat_email_2');
    },
    email_3: function(frm) {
        open_mandat_email(frm, 'mandat_email_3');
    }
});

// ---------------------------------------------------------------------------
// #2211: «Suche Vertrauensanwält*in» – auf die Verfahrenssprache einschränken?
// ---------------------------------------------------------------------------

frappe.provide('frappe.mvd.mandat');
frappe.mvd.mandat.SPRACHNAMEN = {'de': 'Deutsch', 'fr': 'Französisch'};

frappe.mvd.mandat.frage_sprache = function(frm, weiter) {
    // Ohne Verfahrenssprache gibt es nichts zu fragen: an alle VAs der Sektion
    if (!frm.doc.sprache) {
        weiter(false);
        return;
    }
    let name = frappe.mvd.mandat.SPRACHNAMEN[frm.doc.sprache] || frm.doc.sprache;
    let d = new frappe.ui.Dialog({
        title: __('Suche Vertrauensanwält*in'),
        fields: [{'fieldname': 'frage', 'fieldtype': 'HTML', 'options':
            `<p>Verfahrenssprache: <b>${frappe.utils.escape_html(name)}</b></p>` +
            `<p>Nur Vertrauensanwält*innen anschreiben, die diese Sprache haben?</p>` +
            `<p class="text-muted small">Vertrauensanwält*innen ohne eingetragene Sprache werden immer angeschrieben.</p>`}],
        primary_action_label: __('Ja, nur {0}', [name]),
        primary_action: function() {
            d.hide();
            weiter(true);
        }
    });
    // «Nein» als eigener Knopf; Schliessen (×) bricht ab
    $(`<button class="btn btn-default btn-sm" style="margin-right: 5px;">${__('Nein, alle')}</button>`)
        .insertBefore(d.get_primary_btn())
        .on('click', function() {
            d.hide();
            weiter(false);
        });
    d.show();
};

// ---------------------------------------------------------------------------
// #2205: Status-Konzept (Regeln serverseitig in mandat_status.py)
// ---------------------------------------------------------------------------

frappe.provide('frappe.mvd.mandat_status');
frappe.mvd.mandat_status.STATUS_RSV = ['Unzugewiesen', 'Nicht vergeben', 'Vorgemerkt', 'Gesuch eingereicht', 'Laufend (RSV)',
    'Abgelehnt', 'Abgeschlossen', 'Rückzug', 'Gelöscht'];
frappe.mvd.mandat_status.VOR_EINREICHUNG = ['Unzugewiesen', 'Nicht vergeben', 'Vorgemerkt'];
frappe.mvd.mandat_status.JEDERZEIT = ['Rückzug', 'Gelöscht'];
frappe.mvd.mandat_status.METHOD = 'mvd.mvd.doctype.mandat.mandat_status.status_aendern';

function setup_status_felder(frm) {
    let ms = frappe.mvd.mandat_status;
    let vor_einreichung = frm.is_new() || ms.VOR_EINREICHUNG.includes(frm.doc.status);
    let ist_solifonds = frm.doc.typ == 'Solidaritätsfonds';

    // Typ nur bis «Vorgemerkt», VA ab «Gesuch eingereicht» nur noch durch die GL
    frm.set_df_property('typ', 'read_only', vor_einreichung ? 0 : 1);
    frm.set_df_property('kontaktperson', 'read_only', (vor_einreichung || frappe.user.has_role(['MV_Solifonds_GL', 'System Manager'])) ? 0 : 1);

    if (ist_solifonds) {
        // Solifonds: Status nur über die Knöpfe
        frm.set_df_property('status', 'read_only', 1);
    } else {
        // RSV: von Hand wählbar, nur RSV-Status; «Nicht vergeben» über den Knopf (Bemerkung Pflicht)
        let optionen = ms.STATUS_RSV.filter(function(s) {
            if (s == 'Nicht vergeben') {
                return frm.doc.status == s;
            }
            if (frm.doc.status == 'Abgelehnt') {
                return s == 'Abgelehnt' || ms.JEDERZEIT.includes(s);
            }
            return true;
        });
        if (frm.doc.status && !optionen.includes(frm.doc.status)) {
            optionen.unshift(frm.doc.status);
        }
        frm.set_df_property('status', 'options', optionen);
        frm.set_df_property('status', 'read_only', 0);
    }
}

function status_call(frm, status, bemerkung) {
    if (frm.is_dirty()) {
        frappe.msgprint(__('Bitte zuerst das Mandat speichern.'));
        return;
    }
    frappe.call({
        method: frappe.mvd.mandat_status.METHOD,
        args: {'mandat': frm.doc.name, 'status': status, 'bemerkung': bemerkung || null},
        freeze: true,
        callback: function() { frm.reload_doc(); }
    });
}

// ---------------------------------------------------------------------------
// Status-Hinweis oben im Formular: was steht jetzt an, und für wen?
// Rollen: VA = eigene VA des Mandats oder «nur RB»; vp = Vorprüfung; gl = Solifonds-GL; sonst «andere» (Sekretariat, MA).
// Farben: yellow = du bist dran, blue = Info, green = erledigt, red = abgelehnt.
// Texte synchron halten mit dem Handbuch (Dokumentation Mandate MVBE, Abschnitt «Hinweis oben im Mandat»).
// ---------------------------------------------------------------------------

frappe.mvd.mandat_status.DRAN = '<b>' + __('Du bist dran:') + '</b> ';
frappe.mvd.mandat_status.NUR_ANSEHEN = __('Du kannst das Mandat nur noch ansehen. Möglich sind noch Anhänge sowie «Abschliessen» und «Rückzug» (Status).');

function status_hinweis(frm) {
    if (frm.is_new()) {
        return;
    }
    let h = status_hinweis_text(frm);
    if (!h) {
        return;
    }
    let text = h[0];
    // «nur RB» nach dem Einreichen: was noch geht (bei erledigten Mandaten nicht mehr nötig)
    if (rb_gesperrt(frm)) {
        if (['Gesuch eingereicht', 'Vorgeprüft', 'Antrag Vorstand'].includes(frm.doc.status)) {
            text += ' ' + frappe.mvd.mandat_status.NUR_ANSEHEN;
        } else if (frm.doc.status == 'Laufend (Solifonds)') {
            text += ' ' + __('Sonst kannst du das Mandat nur noch ansehen und Anhänge hinzufügen.');
        }
    }
    frm.set_intro(text, h[1]);
    // Knopf «Kopieren» bei der CC-Adresse
    $(frm.wrapper).find('.mandat-cc-kopieren').off('click').on('click', function() {
        frappe.utils.copy_to_clipboard($(this).attr('data-adresse'));
        return false;
    });
}

function status_hinweis_text(frm) {
    let onload = frm.doc.__onload || {};
    let va = !!(onload.ist_va || onload.nur_rb);
    let vp = frappe.user.has_role('MV_Solifonds_Vorpruefung');
    let gl = frappe.user.has_role('MV_Solifonds_GL');
    let solifonds = frm.doc.typ == 'Solidaritätsfonds';
    let dran = frappe.mvd.mandat_status.DRAN;

    switch (frm.doc.status) {
        case 'Unzugewiesen':
            return [__('Noch keine Vertrauensanwält*in. Über <b>Suche Vertrauensanwält*in</b> anfragen oder die VA direkt eintragen. Findet sich keine: <b>Status → Nicht vergeben</b>.'), 'blue'];
        case 'Nicht vergeben':
            return [__('Keine Vertrauensanwält*in gefunden. Wird doch noch eine VA eingetragen, steht das Mandat wieder auf «Vorgemerkt».'), 'blue'];
        case 'Vorgemerkt':
            if (!va) {
                return [solifonds ? __('Wartet auf das Einreichen durch die Vertrauensanwält*in.')
                    : __('Wartet darauf, dass die Vertrauensanwält*in das Gesuch bei der Coop einreicht.'), 'blue'];
            }
            if (solifonds) {
                let grund = rueckweisung(frm);
                return [(grund ? __('Von der Vorprüfung zurückgewiesen: «{0}».', [frappe.utils.escape_html(grund)]) + ' ' : '') +
                    dran + __('Begründung und Kriterien prüfen, dann <b>Solidaritätsfonds → Gesuch einreichen</b>.'), 'yellow'];
            }
            return [dran + __('Gesuch bei der Coop einreichen, mit dieser Adresse im CC:') + ' ' + cc_html(onload.cc_adresse) +
                '<br>' + __('Kommt die Mail an, wechselt der Status automatisch auf «Gesuch eingereicht».'), 'yellow'];
        case 'Gesuch eingereicht':
            if (!solifonds) {
                return [__('Wartet auf den Entscheid der Coop. Bei Deckung bzw. Kostengutsprache «Laufend (RSV)», am Ende «Abgeschlossen» (Feld Status).'), 'blue'];
            }
            if (vp) {
                return [dran + __('<b>Vorprüfung abschliessen</b> (Häkchen «Reglement erfüllt») oder <b>An VA zurückweisen</b> (Menü Solidaritätsfonds).'), 'yellow'];
            }
            return [__('Das Solifonds-Gesuch ist eingereicht und wartet auf die Vorprüfung.'), 'blue'];
        case 'Vorgeprüft':
            if (gl) {
                return [dran + __('<b>Solidaritätsfonds → Entscheid GL</b>: Kostengutsprache, Ablehnung oder Antrag an den Vorstand.'), 'yellow'];
            }
            if (vp) {
                return [__('Vorgeprüft, wartet auf den Entscheid der Geschäftsleitung. Bei Bedarf <b>Vorprüfung zurücknehmen</b>.'), 'blue'];
            }
            return [__('Vorgeprüft, wartet auf den Entscheid der Geschäftsleitung.'), 'blue'];
        case 'Antrag Vorstand':
            if (gl) {
                return [dran + __('Der Vorstand stimmt per E-Mail ab. Danach <b>Solidaritätsfonds → Abstimmung abschliessen</b> (bei Patt entscheidet die GL).'), 'yellow'];
            }
            return [__('Antrag an den Vorstand: Der Vorstand stimmt per E-Mail ab.'), 'blue'];
        case 'Laufend (RSV)':
            if (va) {
                return [__('Ist der Fall erledigt, Status auf «Abgeschlossen» setzen (Feld Status).'), 'blue'];
            }
            return [__('Laufend, die Vertrauensanwält*in führt den Fall.') + (frappe.user.has_role('MV_Solifonds_GL') ? ' ' + __('Visum möglich (Häkchen «Visum»).') : ''), 'blue'];
        case 'Laufend (Solifonds)':
            if (va) {
                return [__('Kostengutsprache erteilt, das PDF kam per E-Mail. Formular vom Mitglied unterschreiben lassen. Ist der Fall erledigt: <b>Status → Abschliessen</b>.'), 'blue'];
            }
            return [__('Kostengutsprache erteilt, die Vertrauensanwält*in führt den Fall.'), 'blue'];
        case 'Abgelehnt':
            return [__('Abgelehnt (Endstatus). Möglich ist nur noch «Rückzug»') + (va ? '' : ' ' + __('oder «Gelöscht»')) + '.', 'red'];
        case 'Abgeschlossen':
        case 'Rückzug':
        case 'Gelöscht':
            return [__('Erledigt (Status «{0}»).', [__(frm.doc.status)]), 'green'];
    }
    return null;
}

// Grund der letzten Rückweisung durch die Vorprüfung, falls das Mandat deswegen wieder auf «Vorgemerkt» steht
function rueckweisung(frm) {
    let v = frm.doc.statusverlauf || [];
    let letzte = v.length ? v[v.length - 1] : null;
    if (letzte && letzte.von_status == 'Gesuch eingereicht' && letzte.nach_status == 'Vorgemerkt') {
        return letzte.bemerkung || '';
    }
    return '';
}

function cc_html(adresse) {
    if (!adresse) {
        return __('siehe Bestätigungs-E-Mail');
    }
    let a = frappe.utils.escape_html(adresse);
    return `<code style="user-select: all;">${a}</code> <button class="btn btn-default btn-xs mandat-cc-kopieren" data-adresse="${a}" ` +
        `title="${__('In die Zwischenablage kopieren')}"><i class="fa fa-copy"></i> ${__('Kopieren')}</button>`;
}

function rb_gesperrt(frm) {
    return !frm.is_new() && !!(frm.doc.__onload && frm.doc.__onload.rb_gesperrt);
}

function add_status_buttons(frm) {
    // «nur RB» nach dem Einreichen: Formular schreibgeschützt, aber Abschliessen/Rückzug bleiben
    let nur_rb = rb_gesperrt(frm);
    if (frm.is_new() || !(frm.perm[0].write || nur_rb)) {
        return;
    }
    let gruppe = __('Status');
    let status = frm.doc.status;
    let ms = frappe.mvd.mandat_status;

    if (status == 'Unzugewiesen') {
        frm.add_custom_button(__('Nicht vergeben'), function() {
            frappe.prompt([{'fieldname': 'bemerkung', 'fieldtype': 'Small Text', 'label': __('Bemerkung'), 'reqd': 1,
                    'description': __('Warum keine Vertrauensanwält*in gefunden wurde. Ohne Personendaten.')}],
                function(values) { status_call(frm, 'Nicht vergeben', values.bemerkung); },
                __('Keine Vertrauensanwält*in gefunden'), __('Nicht vergeben'));
        }, gruppe);
    }

    // RSV: Status von Hand im Feld; Solifonds: Knöpfe
    if (frm.doc.typ != 'Solidaritätsfonds') {
        return;
    }
    if (status == 'Laufend (Solifonds)') {
        frm.add_custom_button(__('Abschliessen'), function() {
            frappe.confirm(__('Mandat abschliessen?'), function() { status_call(frm, 'Abgeschlossen'); });
        }, gruppe);
    }
    ms.JEDERZEIT.forEach(function(ziel) {
        if (status == ziel || (nur_rb && ziel != 'Rückzug')) {
            return;
        }
        frm.add_custom_button(__(ziel), function() {
            frappe.prompt([{'fieldname': 'bemerkung', 'fieldtype': 'Small Text', 'label': __('Bemerkung (optional)'),
                    'description': __('Ohne Personendaten.')}],
                function(values) { status_call(frm, ziel, values.bemerkung); },
                __('Status «{0}» setzen', [__(ziel)]), __(ziel));
        }, gruppe);
    });
}

function load_html_overview(frm) {
    if (frm.doc.mv_mitgliedschaft) {
        frappe.call({
            method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_uebersicht_html",
            args:{
                    'name': frm.doc.mv_mitgliedschaft
            },
            callback: function(r)
            {
                frm.set_df_property('uebersicht_html', 'options', r.message);
            }
        });
    }
}

function open_mandat_email(frm, template_prefix) {
    if (!frm.doc.kontaktperson) {
        frappe.msgprint(__("Bitte zuerst eine*n Berater*in auswählen."));
        return;
    }

    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Termin Kontaktperson',
            name: frm.doc.kontaktperson
        },
        callback: function(r) {
            if (r.message && r.message.user && r.message.user.length > 0) {
                var recipient = r.message.user[0].user;
                var email_template = template_prefix + '-' + frm.doc.sektion_id;

                new frappe.mvd.MailComposer({
                    doc: frm.doc,
                    frm: frm,
                    subject: __('Mandat') + ': ' + frm.docname,
                    recipients: recipient,
                    attach_document_print: false,
                    txt: '',
                    email_template: email_template
                });
            } else {
                frappe.msgprint(__("Keine/r Benutzer*in für die/den ausgewählte/n Berater*in gefunden."));
            }
        }
    });
}

// ---------------------------------------------------------------------------
// Solidaritätsfonds: Knöpfe je nach Status und Rolle (Logik: solifonds.py)
// ---------------------------------------------------------------------------

function solifonds_call(frm, method, args, callback) {
    if (frm.is_dirty()) {
        frappe.msgprint(__('Bitte zuerst das Mandat speichern.'));
        return;
    }
    frappe.call({
        method: frappe.mvd.solifonds.METHOD + method,
        args: Object.assign({'mandat': frm.doc.name}, args || {}),
        freeze: true,
        callback: function(r) {
            if (callback) {
                callback(r);
            } else {
                frm.reload_doc();
            }
        }
    });
}

function add_solifonds_buttons(frm) {
    let gruppe = __('Solidaritätsfonds');
    let status = frm.doc.status;

    if (status == 'Vorgemerkt') {
        frm.add_custom_button(__('Gesuch einreichen'), function() {
            frappe.confirm(__('Solifonds-Gesuch jetzt zur Vorprüfung einreichen?'), function() {
                solifonds_call(frm, 'gesuch_einreichen');
            });
        }, gruppe);
    }

    if (frappe.user.has_role('MV_Solifonds_Vorpruefung')) {
        if (status == 'Gesuch eingereicht') {
            frm.add_custom_button(__('Vorprüfung abschliessen'), function() {
                let d = new frappe.ui.Dialog({
                    title: __('Vorprüfung'),
                    fields: [
                        {'fieldname': 'vorpruefung_ok', 'fieldtype': 'Check', 'label': __('Zweckbestimmungen und Voraussetzungen gem. Reglement erfüllt')},
                        {'fieldname': 'begruendung', 'fieldtype': 'Small Text', 'label': __('Begründung Vorprüfung (optional)'), 'description': frappe.mvd.solifonds.OHNE_PERSONENDATEN}
                    ],
                    primary_action_label: __('Vorgeprüft → an GL'),
                    primary_action: function(values) {
                        d.hide();
                        solifonds_call(frm, 'vorpruefung_abschliessen', {'vorpruefung_ok': values.vorpruefung_ok ? 1 : 0, 'begruendung': values.begruendung});
                    }
                });
                d.show();
            }, gruppe);
            frm.add_custom_button(__('An VA zurückweisen'), function() {
                frappe.prompt([{'fieldname': 'grund', 'fieldtype': 'Small Text', 'label': __('Grund'), 'reqd': 1}], function(values) {
                    solifonds_call(frm, 'an_va_zurueckweisen', {'grund': values.grund});
                }, __('Gesuch an die VA zurückweisen'), __('Zurückweisen'));
            }, gruppe);
        }
        if (status == 'Vorgeprüft') {
            frm.add_custom_button(__('Vorprüfung zurücknehmen'), function() {
                solifonds_call(frm, 'vorpruefung_zuruecknehmen');
            }, gruppe);
        }
    }

    if (frappe.user.has_role('MV_Solifonds_GL')) {
        if (status == 'Vorgeprüft') {
            frm.add_custom_button(__('Entscheid GL'), function() {
                frappe.mvd.solifonds.entscheid_dialog(frm.doc.name, function() { frm.reload_doc(); });
            }, gruppe);
        }
        if (status == 'Antrag Vorstand') {
            frm.add_custom_button(__('Abstimmung abschliessen'), function() {
                frappe.mvd.solifonds.abstimmung_abschliessen(frm.doc.name, function() { frm.reload_doc(); });
            }, gruppe);
        }
    }
}
