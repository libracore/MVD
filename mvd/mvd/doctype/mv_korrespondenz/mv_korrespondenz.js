// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('MV Korrespondenz', {
     sektion_id: function(frm) {
        frappe.call({
            'method': "frappe.client.get",
            'args': {
                'doctype': "Sektion",
                'name': cur_frm.doc.sektion_id
            },
            'callback': function(response) {
                var sektion_settings = response.message;

                if (sektion_settings) {
                    cur_frm.set_value('kopf_fusszeile', sektion_settings.default_kopf_fusszeile);
                    cur_frm.set_value('ort', sektion_settings.default_ort);
                }
            }
        });
     },
     setup: function(frm) {
         if (!cur_frm.doc.ansprechperson && !cur_frm.doc.tel_ma && !cur_frm.doc.email_ma) {
             frappe.call({
                'method': "frappe.client.get",
                'args': {
                    'doctype': "User",
                    'name': frappe.session.user
                },
                'callback': function(response) {
                    var user = response.message;

                    if (user) {
                        cur_frm.set_value('ansprechperson', user.full_name);
                        cur_frm.set_value('tel_ma', user.phone);
                        cur_frm.set_value('email_ma', user.email);
                    }
                }
            });
         }
     }
});
