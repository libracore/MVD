// Copyright (c) 2021 - 2026, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sektion', {
    setup: function(frm) {
        [
            ['firmenverrechnung_verbindlichkeitskonto', 'Liability'],
            ['firmenverrechnung_forderungskonto', 'Asset']
        ].forEach(function(config) {
            frm.set_query(config[0], function() {
                return {
                    filters: {
                        company: frm.doc.company,
                        root_type: config[1],
                        is_group: 0,
                        disabled: 0,
                        account_type: ['not in', ['Bank', 'Cash', 'Receivable', 'Payable']]
                    }
                };
            });
        });
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
