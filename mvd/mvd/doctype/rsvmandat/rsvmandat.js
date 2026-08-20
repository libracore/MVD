// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('RSVMandat', {
    refresh: function(frm) {
        // check for TimestampMismatchError and reload
        if (!frm.doc.__islocal) {
            frappe.db.get_value(cur_frm.doctype, cur_frm.docname, 'modified').then(r => {
                if (r.message.modified != cur_frm.doc.modified) {
                    cur_frm.reload_doc();
                }
            });
        };

        cur_frm.fields_dict['thema'].get_query = function(doc) {
             return {
                 filters: {
                     "rsv": 1
                 }
             }
        }
        cur_frm.fields_dict['anwalt'].get_query = function(doc) {
             return {
                 filters: {
                     "ist_vertrauensanwaeltin": 1
                 }
             }
        }
        
        frm.add_custom_button(__("Vergabeliste"),  function() {
            var domain = window.location.origin;
            window.open(`${domain}/va/vergabeliste`, '_blank');
        }, "Öffne");
        frm.add_custom_button(__("Meine-Mandate"),  function() {
            var domain = window.location.origin;
            window.open(`${domain}/va/meine-mandate`, '_blank');
        }, "Öffne");
    }
});
