// Copyright (c) 2025, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('WebFormular', {
    onload: function(frm) {
        let fieldname = "form_data";
        try {
            if (frm.doc[fieldname]) {
                let parsed = JSON.parse(frm.doc[fieldname]);
                frm.set_value(fieldname, JSON.stringify(parsed, null, 2));
            }
        } catch (e) {
            console.log("Invalid JSON in " + fieldname, e);
        }
    }
});

