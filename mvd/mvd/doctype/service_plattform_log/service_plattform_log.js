// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Plattform Log', {
    refresh: function(frm) {
        if (['New', 'Failed'].includes(cur_frm.doc.status)) {
            frm.add_custom_button(__("Request ausführen"), function() {
                execute_request(frm);
            });
        }
    },
    open_mitglied: function(frm) {
        location.href = `/desk#Form/Mitgliedschaft/${cur_frm.doc.mv_mitgliedschaft}`
    }
});

function execute_request(frm) {
    frappe.call({
        "method": "mvd.mvd.service_plattform.request_worker.execute_sp_log",
        "args": {
            "sp_log": frm.doc.name,
            "manual_execution": true
        },
        "freeze": true,
        "freeze_message": "Bitte warten...",
        "callback": function(r) {
            var execution_status = r.message;
            if (execution_status == 1) {
                cur_frm.reload_doc();
            } else {
                frappe.msgprint('Es gibt zu dieser Mitgliedschaft ältere, unverarbeitete Requests. Diese müssen zuerst verarbeitet werden.', 'Nicht verarbeitet');
            }
        }
    });
}
