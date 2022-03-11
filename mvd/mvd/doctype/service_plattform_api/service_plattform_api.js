// Copyright (c) 2021-2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Plattform API', {
    flush_queue: function(frm) {
        frappe.call({
            method: 'mvd.mvd.doctype.service_plattform_api.service_plattform_api.flush_complete_queue'
        });
    }
});

frappe.ui.form.on('Service Plattform API Connection', {
    get_token: function(frm, cdt, cdn) {
        frappe.call({
            method: 'mvd.mvd.service_plattform.api.get_token',
            args: {
                scope: locals[cdt][cdn].connection
            },
            callback: function(response) {
               frappe.show_alert( __("Token updated") );
               cur_frm.reload_doc();
            }
        });
    }
});
