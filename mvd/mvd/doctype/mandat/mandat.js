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
