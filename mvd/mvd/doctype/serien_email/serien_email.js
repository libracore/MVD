// Copyright (c) 2023, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Serien Email', {
    refresh: function(frm) {
        // filter for template link field
        cur_frm.fields_dict['template'].get_query = function(doc) {
             return {
                 filters: {
                     "e_mail_vorlage": 1,
                     "sektion_id": cur_frm.doc.sektion_id
                 }
             }
        }
        
        if (cur_frm.doc.docstatus == 1) {
            if (cur_frm.doc.status == 'New') {
                frm.add_custom_button(__("Starte Versand"), function() {
                    cur_frm.set_value("status", "Sending").then(() => {
                        cur_frm.save_or_update();
                    });
                }).addClass("btn-warning")
            }
            if (cur_frm.doc.status == 'Sending') {
                frm.add_custom_button(__("Stoppe Versand"), function() {
                    cur_frm.set_value("status", "Cancelled").then(() => {
                        cur_frm.save_or_update();
                    });
                }).addClass("btn-danger")
            }
            if (cur_frm.doc.status == 'Cancelled') {
                frm.add_custom_button(__("Versand Neustart"), function() {
                    cur_frm.set_value("status", "Sending").then(() => {
                        cur_frm.save_or_update();
                    });
                }).addClass("btn-danger")
            }
        }
        
        if (cur_frm.doc.docstatus == 0) {
            frm.add_custom_button(__("Entferne Mitglieder ohne gültige E-Mailadresse"), function() {
                var empfaenger = cur_frm.doc.empfaenger;
                var to_removed = []
                
                // check wich to remove
                empfaenger.forEach(function(entry) {
                   if (entry.status == 'E-Mail missing') {
                       to_removed.unshift(entry.idx);
                   }
                });
                
                // remove
                to_removed.forEach(function(entry) {
                   cur_frm.doc.empfaenger.splice(entry-1, 1);
                });
                cur_frm.refresh_field('empfaenger');
                
                // reset idx
                var idx_loop = 1;
                empfaenger.forEach(function(entry) {
                   entry.idx = idx_loop;
                   idx_loop += 1;
                });
                cur_frm.refresh_field('empfaenger');
            })
        }
    }
});

frappe.ui.form.on("Serien Email Empfaenger", "email", function(frm, cdt, cdn) {
    var empfaenger = locals[cdt][cdn];
    empfaenger.status = 'Manuelle E-Mail';
    cur_frm.refresh_field('empfaenger');
});
