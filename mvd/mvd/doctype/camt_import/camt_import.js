// Copyright (c) 2022, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('CAMT Import', {
    refresh: function(frm) {
        // auto save
        if (frm.doc.__islocal) {
           cur_frm.save();
        }
        // filter account
        cur_frm.fields_dict['account'].get_query = function(doc) {
            return {
                filters: {
                    'account_type': 'Bank',
                    'company': cur_frm.doc.company
                }
            }
        }
        
        if (cur_frm.doc.status != 'Open') {
            cur_frm.set_df_property('account','read_only',1);
            cur_frm.set_df_property('company','read_only',1);
            cur_frm.set_df_property('sektion_id','read_only',1);
            cur_frm.set_df_property('camt_file','read_only',1);
            if (cur_frm.doc.status == 'Aktualisierung notwendig') {
                aktualisiere_camt_uebersicht(frm);
            }
        }
    },
    account: function(frm) {
        cur_frm.save();
    },
    import: function(frm) {
        if (cur_frm.doc.account) {
            if (cur_frm.is_dirty()) {
                cur_frm.save();
                import_payments(frm);
            } else {
                import_payments(frm);
            }
        } else {
            frappe.msgprint("Bitte zuerst eine Sektion / ein Account auswählen");
        }
    },
    show_overpaid: function(frm) {
        frappe.route_options = {
            "name": ["in", eval(cur_frm.doc.matched_payments)],
            "unallocated_amount": [">", 0]
        }
        frappe.set_route("List", "Payment Entry");
    },
    show_unassigned: function(frm) {
        frappe.route_options = {
            "name": ["in", eval(cur_frm.doc.unmatched_payments)],
            "docstatus": 0
        }
        frappe.set_route("List", "Payment Entry");
    },
    show_manual_match: function(frm) {
        frappe.set_route("match_payments");
    },
    close_camt_import: function(frm) {
        frappe.confirm(
            'Es wurden nicht alle Zahlungen zugewiesen/verbucht, möchten Sie den CAMT Import trotzdem schliessen?',
            function(){
                // on yes
                cur_frm.set_value("status", "Closed");
                cur_frm.save();
            },
            function(){
                // on no
            }
        )
    },
    generate_report: function(frm) {
        //~ frappe.call({
            //~ method: 'mvd.mvd.doctype.camt_import.camt_import.generate_report',
            //~ args: {
                //~ 'camt_record': cur_frm.doc.name
            //~ },
            //~ freeze: true,
            //~ freeze_message: 'Analysiere Daten und erstelle Bericht...',
            //~ callback: function(r) {
                //~ if (r.message) {
                    //~ var feedback = r.message;
                    //~ if (feedback.status == 'ok') {
                        //~ frappe.msgprint("Bericht erstellt");
                    //~ } else {
                        //~ frappe.msgprint(feedback.feedback_message);
                    //~ }
                //~ } else {
                    //~ frappe.msgprint("Etwas ist schief gelaufen...");
                //~ }
            //~ }
        //~ });
    },
    aktualisiere_camt_uebersicht: function(frm) {
        aktualisiere_camt_uebersicht(frm);
    },
    show_imported_payments: function(frm) {
        frappe.route_options = {"name": ["in", eval(cur_frm.doc.importet_payments)]}
        frappe.set_route("List", "Payment Entry");
    },
    show_unsubmitted_payments: function(frm) {
        frappe.route_options = {
            "name": ["in", eval(cur_frm.doc.unsubmitted_payments)],
            "docstatus": 0
        }
        frappe.set_route("List", "Payment Entry");
    },
    show_submitted_payments: function(frm) {
        frappe.route_options = {
            "name": ["in", eval(cur_frm.doc.submitted_payments)],
            "docstatus": 1
        }
        frappe.set_route("List", "Payment Entry");
    },
    show_matched_payments: function(frm) {
        frappe.route_options = {
            "name": ["in", eval(cur_frm.doc.matched_payments)]
        }
        frappe.set_route("List", "Payment Entry");
    },
    show_canceled_payments: function(frm) {
        frappe.route_options = {
            "name": ["in", eval(cur_frm.doc.importet_payments)],
            "docstatus": 2
        }
        frappe.set_route("List", "Payment Entry");
    }
});

function import_payments(frm) {
    cur_frm.set_value("status", "In Verarbeitung");
    cur_frm.save().then(function(){
        frappe.call({
            method: 'mvd.mvd.doctype.camt_import.camt_import.lese_camt_file',
            args: {
                'file_path': cur_frm.doc.camt_file,
                'camt_import': cur_frm.doc.name
            },
            freeze: true,
            freeze_message: 'Importiere Zahlungen...',
            callback: function(r) {
                cur_frm.reload_doc();
            }
        });
    });
}

function aktualisiere_camt_uebersicht(frm) {
    cur_frm.set_value("status", "In Verarbeitung");
    cur_frm.save().then(function(){
        frappe.call({
            method: 'mvd.mvd.doctype.camt_import.camt_import.aktualisiere_camt_uebersicht',
            args: {
                'camt_import': cur_frm.doc.name
            },
            freeze: true,
            freeze_message: 'Analysiere Daten...',
            callback: function(r) {
                cur_frm.reload_doc();
            }
        });
    });
}
