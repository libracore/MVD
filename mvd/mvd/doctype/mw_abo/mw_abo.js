// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('MW Abo', {
    ende: function(frm) {
        if (cur_frm.doc.ende) {
            if (cur_frm.doc.ende > frappe.datetime.nowdate()) {
                cur_frm.set_value("status", "Aktiv terminiert");
            } else {
                cur_frm.set_value("status", "Inaktiv");
            }
        } else {
            cur_frm.set_value("status", "Aktiv");
        }
    },
    customer: function(frm) {
        cur_frm.fields_dict['contact'].get_query = function(doc) {
            return {
                filters: {
                    "link_doctype": "Customer",
                    "link_name": cur_frm.doc.customer
                }
            }
        }
        cur_frm.fields_dict['address'].get_query = function(doc) {
            return {
                filters: {
                    "link_doctype": "Customer",
                    "link_name": cur_frm.doc.customer
                }
            }
        }
    },
    contact: function(frm) {
        if (cur_frm.doc.contact) {
            frappe.call({
                'method': "frappe.client.get",
                'args': {
                    'doctype': "Contact",
                    'name': cur_frm.doc.contact
                },
                'callback': function(response) {
                    var contact = response.message;
                    if (contact) {
                        cur_frm.set_value('address', contact.address);
                    }
                }
            });
        }
    }
});
