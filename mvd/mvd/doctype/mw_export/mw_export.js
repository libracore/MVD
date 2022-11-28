// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('MW Export', {
    refresh: function(frm) {
        if (cur_frm.doc.zeitungsauflage_data) {
            cur_frm.set_df_property('zeitungsauflage','options', cur_frm.doc.zeitungsauflage_data);
        }
    },
    query_hinzufuegen: function(frm) {
        frappe.call({
            method: 'query_hinzufuegen',
            doc: frm.doc,
            callback: function(response) {
               cur_frm.reload_doc();
            }
        });
    }
});
