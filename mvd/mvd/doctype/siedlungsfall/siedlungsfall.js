// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Siedlungsfall', {
    refresh: function(frm) {
        if (cur_frm.doc.siedlung) {
            frm.add_custom_button(__("Mitgliedschaften laden"), function() {
                frm.call("get_mitgliedschaften", {'manually': 1}, (r) => {
                    cur_frm.reload_doc();
                    frappe.show_alert({message:__("Die betroffenen Mitgliedschaften wurden geladen"), indicator:'green'});
                });
            });
        }
    }
});
