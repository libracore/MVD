// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('MW Export', {
    onload: function(frm) {
        if (frm.doc.__islocal && (!frm.doc.einzelqueries || frm.doc.einzelqueries.length === 0)) {
            let child = frm.add_child('einzelqueries');
            child.titel = 'STOP_nicht-MVD';
            child.query = "(`sektion_id` = 'MVBE' AND `language` = 'fr') OR `sektion_id` LIKE 'AL%' OR `sektion_id` = 'ASI' OR `sektion_id` = 'ASLOCA'";
            frm.refresh_field('einzelqueries');
        }
    },
    refresh: function(frm) {
        if (frm.doc.__islocal) {
           frappe.dom.freeze('Zähle Abonnent*innen...');
           cur_frm.save().then(function(){frappe.dom.unfreeze();});
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
                   frappe.msgprint('Der Export wurde gestartet. Sie können den Fortschritt <a href="/desk#background_jobs">hier</a> einsehen.');
                }
            });
        });
    }
});
