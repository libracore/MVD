// Copyright (c) 2023, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Arbeitsplan Beratung', {
    refresh: function(frm) {
        if (cur_frm.doc.docstatus == 0 && cur_frm.doc.einteilung.length < 1) {
            frm.add_custom_button(__("Hole Berater*innen"), function() {
                frm.call("get_personen", {}, (r) => {
                    frm.reload_doc();
                });
            });
        }
    }
});
