// Copyright (c) 2025, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('WebFormular', {
        refresh: function(frm) {
        frm.add_custom_button("Export JSON as CSV", function() {
            if (!frm.doc.form_id) {
                frappe.msgprint("Please set a FormID first.");
                return;
            }
            
            frappe.call({
                method: "mvd.mvd.doctype.webformular.webformular.export_form_data_as_csv",
                args: {
                    form_id: frm.doc.form_id,
                    webformular: frm.doc.name
                },
                callback: function(r) {
                    frappe.msgprint("Der Exportvorgang wurde gestartet.<br>Sie können den Fortschritt <a href='/desk#background_jobs'>hier</a> verfolgen.");
                }
            });
        });
    }
});

