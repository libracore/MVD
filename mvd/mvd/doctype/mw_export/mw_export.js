// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('MW Export', {
    refresh: function(frm) {
        if (frm.doc.__islocal) {
           cur_frm.save();
        }
        
        if (cur_frm.doc.zeitungsauflage_data) {
            cur_frm.set_df_property('zeitungsauflage','options', cur_frm.doc.zeitungsauflage_data);
        } else {
            cur_frm.set_df_property('zeitungsauflage','options', '');
        }
        
        if (cur_frm.doc.status != 'Neu') {
            var i = 0;
            for (i; i<cur_frm.fields.length; i++) {
                cur_frm.set_df_property(cur_frm.fields[i].df.fieldname,'read_only', 1);
                cur_frm.set_df_property("section_query_generator", "hidden", 1)
            }
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
    },
    export_queries: function(frm) {
        cur_frm.set_value("status", "CSV Erstellung");
        cur_frm.save().then(function(){
            frappe.call({
                method: 'export_queries',
                doc: frm.doc,
                callback: function(response) {
                   cur_frm.reload_doc();
                   frappe.msg_print('Der Export wurde gestartet. Sie können den Fortschritt <a href="/desk#background_jobs">hier</a> einsehen.');
                }
            });
        });
    }
});
