// Copyright (c) 2021-2022, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('User', {
    validate: function(frm) {
        deploy_user(frm);
    }
});

// this function will deploy this role to auth0
function deploy_user(frm) {
    console.log("Deploy user to auth0");
    frappe.call({
        "method": "mvd.mvd.service_plattform.api.create_user",
        "args": {
            "email": frm.doc.email,
            "first_name": (frm.doc.first_name || ""),
            "last_name": (frm.doc.last_name || "")
        },
        "callback": function(response) {
            // collect roles
            var roles = [];
            for (var i = 0; i < frm.doc.roles.length; i++) {
                roles.push(frm.doc.roles[i].role);
            }
            console.log("assign roles");
            console.log(roles);
            frappe.call({
                "method": "mvd.mvd.service_plattform.api.assign_roles",
                "args": {
                    "user": frm.doc.email,
                    "roles": roles
                }
            })
        }
    });
}
