// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Region', {
    refresh: function(frm) {
        frm.add_custom_button(__("Automatisch Zuordnen"), function() {
            zuordnung(frm);
        });
    }
});

function zuordnung(frm) {
    frappe.call({
        method: 'mvd.mvd.doctype.region.region.zuordnung',
        args: {
            region: cur_frm.doc.name
        },
        freeze: true,
        freeze_message: 'Bitte warten, Zuordnung erfolgt...',
        callback: function(r) {
            cur_frm.reload_doc();
        }
    });
}
