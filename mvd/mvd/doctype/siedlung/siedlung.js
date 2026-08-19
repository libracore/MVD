// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Siedlung', {
    after_save: function(frm) {
        frm.reload_doc();
    }
});
