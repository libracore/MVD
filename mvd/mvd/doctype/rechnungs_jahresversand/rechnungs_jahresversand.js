// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Rechnungs Jahresversand', {
    refresh: function(frm) {
        if (!cur_frm.doc.sektion_id) {
            cur_frm.set_value("sektion_id", frappe.boot.default_sektion);
        }
        
        if (!frappe.user.has_role("System Manager")) {
            cur_frm.set_df_property('status', 'read_only', 1);
        }
    },
    download_draft: function(frm) {
        frappe.call({
            'method': "mvd.mvd.doctype.rechnungs_jahresversand.rechnungs_jahresversand.get_draft_csv",
            'args': {
                'jahresversand': cur_frm.doc.name
            },
            'freeze': true,
            'freeze_message': 'Erstelle Entwurfs CSV...',
            'callback': function(response) {
                var csv = response.message;

                if (csv == 'done') {
                    cur_frm.reload_doc();
                }
            }
        });
    },
    rechnungen_stornieren: function(frm) {
        frappe.msgprint("Diese Funktion steht im Moment nicht zur Verfügung");
    },
    download_new_csv: function(frm) {
        frappe.call({
            'method': "mvd.mvd.doctype.rechnungs_jahresversand.rechnungs_jahresversand.get_csv",
            'args': {
                'jahresversand': cur_frm.doc.name,
                'bg_job': true
            },
            'callback': function(response) {
                frappe.msgprint("Der Prozess wurde gestartet. Sie können den Fortschritt <a href='/desk#background_jobs'>hier</a> einsehen.");
                cur_frm.reload_doc();
            }
        });
    }
});
