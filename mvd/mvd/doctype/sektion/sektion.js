// Copyright (c) 2021, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sektion', {
    setup: function(frm) {
        frm.set_query('e_mail_vorlage', 'zahlungsbestaetigung_per_mail', function() {
            return {
                filters: {
                    'sektion_id': frm.doc.name
                }
            };
        });
    },
    refresh: function(frm) {
        // filter account
        cur_frm.fields_dict['account'].get_query = function(doc) {
            return {
                filters: {
                    'account_type': 'Bank',
                    'company': cur_frm.doc.company
                }
            }
        }
    }
});
