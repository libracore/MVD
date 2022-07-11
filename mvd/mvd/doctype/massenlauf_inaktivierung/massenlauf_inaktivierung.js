// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Massenlauf Inaktivierung', {
    refresh: function(frm) {
        if (!cur_frm.doc.sektion_id) {
            cur_frm.set_value("sektion_id", frappe.boot.default_sektion);
        }
    }
});
