// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Platform Queue', {
    refresh: function(frm) {
        if (cur_frm.doc.status == 'Failed') {
            frm.add_custom_button(__("Zeige Error Log"), function() {
                frappe.route_options = {"error": ['like', `%${cur_frm.doc.mv_mitgliedschaft}%`]}
                frappe.set_route("List", "Error Log", "List");
            });
        }
    },
    open_mitglied: function(frm) {
        location.href = `/desk#Form/Mitgliedschaft/${cur_frm.doc.mv_mitgliedschaft}`
    }
});
