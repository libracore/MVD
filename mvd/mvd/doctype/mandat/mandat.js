// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

{% include "mvd/mvd/doctype/mandat/solifonds_dialoge.js" %}

frappe.ui.form.on('Mandat', {
    refresh: function(frm) {
        // Mitgliedschaftsübersicht wie in der Beratung
        load_html_overview(frm);
        frappe.mvd.schlichtungsbehoerde_listener(frm, 'uebersicht_html');

        // «Fall verfolgen» sehen alle, setzen nur GL und Vorprüfung; Visum (nur RSV) setzt nur die GL (#2210)
        frm.set_df_property('fall_verfolgen', 'read_only', frappe.user.has_role(['MV_Solifonds_GL', 'MV_Solifonds_Vorpruefung']) ? 0 : 1);
        frm.set_df_property('visum', 'read_only', frappe.user.has_role('MV_Solifonds_GL') ? 0 : 1);

        // #2205: Status, Typ und VA je nach Status; Knöpfe für Nicht vergeben / Abschliessen / Rückzug / Gelöscht
        setup_status_felder(frm);
        add_status_buttons(frm);

        // #2213: Schlichtungsbehörde nachträglich ermitteln, falls sie beim Erstellen nicht gefunden wurde
        if (!frm.is_new() && frm.doc.mv_mitgliedschaft && !frm.doc.schlichtungsbehoerde) {
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
                
                frappe.call({
                    method: 'mvd.mvd.doctype.mandat.mandat.suche_vertrauensanwaeltin',
                    args: {
                        "mandat_id": frm.doc.name,
                        "sektion_id": frm.doc.sektion_id
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

function add_status_buttons(frm) {
    if (frm.is_new() || !frm.perm[0].write) {
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
        if (status == ziel) {
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
