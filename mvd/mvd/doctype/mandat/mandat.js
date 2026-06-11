// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mandat', {
    refresh: function(frm) {
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
    }
});
