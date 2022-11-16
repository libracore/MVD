// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mahnlauf', {
    mahnungen_buchen: function(frm) {
        frappe.call({
            'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.bulk_submit",
            'args': {
                'mahnlauf': cur_frm.doc.name
            },
            "freeze": true,
            "freeze_message": "Buche Mahnungen...",
            'callback': function(r) {
                cur_frm.reload_doc();
            }
        })
    },
    mahnungen_stornieren: function(frm) {
        frappe.call({
            'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.bulk_cancel",
            'args': {
                'mahnlauf': cur_frm.doc.name
            },
            "freeze": true,
            "freeze_message": "Storniere Mahnungen...",
            'callback': function(r) {
                cur_frm.reload_doc();
            }
        })
    }
});
