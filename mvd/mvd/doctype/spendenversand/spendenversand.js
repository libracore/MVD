// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Spendenversand', {
    show_own_sql_data: function(frm) {
        frappe.call({
            method: 'show_own_sql_data',
            doc: frm.doc,
            callback: function(r) {
                console.log(r.message.list);
                frappe.msgprint(r.message.string);
            }
        });

    }
});
