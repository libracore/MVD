// Copyright (c) 2025, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on("Kampagne", {
    refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("Erweiterte Zuordnung der Kampagnen"), function() {
                frappe.call({
                    method: "mvd.mvd.doctype.kampagne.kampagne.erweiterte_zuordnung",
                    args: {
                        docname: frm.doc.name
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            const data = r.message || {};
                            frappe.show_alert({
                                message: __(`Zuordnung abgeschlossen: ${data.assigned} von ${data.total} Kampagnen erfolgreich zugeordnet.`),
                                indicator: data.assigned > 0 ? 'green' : 'orange'
                            }, 5);
                            frm.reload_doc();
                        }
                    }
                });
            });
        }
    }
});



