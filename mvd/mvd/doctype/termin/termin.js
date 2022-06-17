// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Termin', {
    refresh: function(frm) {
        cur_frm.fields_dict['kategorie'].get_query = function(doc) {
             return {
                 filters: {
                     "disabled": ['!=', 1],
                     "sektion_id": cur_frm.doc.sektion_id
                 }
             }
        }
    }
});
