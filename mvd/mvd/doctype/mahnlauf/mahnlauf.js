// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mahnlauf', {
    onload: function(frm) {
        cur_frm.set_value("sektion_id", get_default_sektion());
    },
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
    },
    erstelle_pdf: function(frm) {
        frappe.call({
            'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.mahnung_massenlauf",
            'args': {
                'mahnlauf': cur_frm.doc.name
            },
            "freeze": true,
            "freeze_message": "Bereite Massenlauf vor...",
            'callback': function(r) {
                frappe.set_route("Form", "Massenlauf", r.message);
            }
        })
    },
    entwuerfe_loeschen: function(frm) {
        frappe.call({
            'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.bulk_delete",
            'args': {
                'mahnlauf': cur_frm.doc.name
            },
            "freeze": true,
            "freeze_message": "Lösche Entwurfs Mahnungen...",
            'callback': function(r) {
                cur_frm.reload_doc();
            }
        })
    }
});

function get_default_sektion() {
    var default_sektion = '';
    if (frappe.defaults.get_user_permissions()["Sektion"]) {
        var sektionen = frappe.defaults.get_user_permissions()["Sektion"];
        sektionen.forEach(function(entry) {
            if (entry.is_default == 1) {
                default_sektion = entry.doc;
            }
        });
    }
    return default_sektion
}
