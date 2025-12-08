// Copyright (c) 2021-2022, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('User', {
    validate: function(frm) {
        if (frm.doc.user_type == 'System User') {
            deploy_user(frm);
        }
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
            let roles = [];
            let found_nextcloud_role = false;

            for (var i = 0; i < frm.doc.roles.length; i++) {
                let user_role = frm.doc.roles[i].role;
                switch (user_role) {
                    case 'SSO_NCLC_MVXX':
                        found_nextcloud_role = true;
                        break;
                    default:
                        roles.push(frm.doc.roles[i].role);
                }
            }

            if (found_nextcloud_role) {
                frappe.call({
                    "method": "mvd.mvd.utils.get_nextcloud_authzero_roles",
                    "args": {
                        "user": frm.doc.email
                    },
                    "callback": function(r) {
                        for (var i = 0; i < r.message.length; i++) {
                            roles.push(r.message[i]);
                        }
                        frappe.call({
                            "method": "mvd.mvd.service_plattform.api.assign_roles",
                            "args": {
                                "user": frm.doc.email,
                                "roles": roles
                            }
                        })
                    }
                });
            } else {
                frappe.call({
                    "method": "mvd.mvd.service_plattform.api.assign_roles",
                    "args": {
                        "user": frm.doc.email,
                        "roles": roles
                    }
                })
            }
        }
    });
}
