// Copyright (c) 2021, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Issue', {
	refresh: function(frm) {
        if (cur_frm.doc.gitlab_issue) {
            frm.add_custom_button(__("GitLab Issue öffnen"), function() {
                window.open(`https://git.libracore.io/libracore/MVD/-/issues/${cur_frm.doc.gitlab_issue}`, '_blank').focus();
            }).addClass("btn-success");
        } else {
            frm.add_custom_button(__("GitLab Issue anlegen"), function() {
                create_gitlab_issue(frm);
            }).addClass("btn-warning");
        }
    }
});

function create_gitlab_issue(frm) {
    if (frm.doc.__islocal) {
        frappe.msgprint("Bitte zuerst speichern.");
     } else {
        frappe.call({
            "method": "erpnextswiss.erpnextswiss.doctype.gitlab_settings.gitlab_settings.create_new_issue",
            "args": {
                "title": cur_frm.doc.subject,
                "description": cur_frm.doc.description
            },
            "callback": function(r) {
                if (r.message.iid) {
                    frappe.db.set_value("Issue", cur_frm.doc.name, "gitlab_issue", r.message.iid);
                    cur_frm.reload_doc();
                } else {
                    frappe.msgprint("Es ist etwas schief gelaufen.<br>Bitte im Error-Log nachsehen.")
                }
            }
        });
     }
}