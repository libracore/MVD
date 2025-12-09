// Copyright (c) 2024, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Postretouren Log', {
    refresh: function(frm) {
        if (frappe.user.has_role("System Manager") && cur_frm.doc.status == 'Open') {
            frm.add_custom_button(__("Manuelle Verabreitung starten"), function() {
                manual_start(frm);
            }).addClass("btn-warning")
        }
    }
});

function manual_start(frm) {
    frm.call("manual_start", {}, (r) => {
        cur_frm.reload_doc();
    });
}
