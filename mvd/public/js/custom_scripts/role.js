// Copyright (c) 2021-2022, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Role', {
    validate: function(frm) {
        deploy_role(frm);
    }
});

// this function will deploy this role to auth0
function deploy_role(frm) {
    console.log("Deploy role to auth0");
    frappe.call({
        "method": "mvd.mvd.service_plattform.api.create_role",
        "args": {
            "role": frm.doc.role_name,
            "description": (frm.doc.description || "")
        }
    });
}
