// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mandat', {
    refresh: function(frm) {
        // Mitgliedschaftsübersicht wie in der Beratung
        load_html_overview(frm);
        frappe.mvd.schlichtungsbehoerde_listener(frm, 'uebersicht_html');

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
