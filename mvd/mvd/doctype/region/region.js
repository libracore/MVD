// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Region', {
    refresh: function(frm) {
        if (!cur_frm.doc.disabled&&!cur_frm.doc.auto_zuordnung) {
            frm.add_custom_button(__("Automatisch Zuordnen"), function() {
                zuordnung(frm);
            });
        }
    }
});

function zuordnung(frm) {
    frappe.call({
        method: 'mvd.mvd.doctype.region.region.zuordnung',
        args: {
            region: cur_frm.doc.name
        },
        callback: function(r) {
            cur_frm.reload_doc();
            frappe.msgprint("Die automatische Zuordnung aller Regionen der Sektion " + cur_frm.doc.sektion_id + " wird über Nacht ausgeführt.");
        }
    });
}
