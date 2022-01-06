// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fakultative Rechnung', {
    onload: function(frm) {
        if (frm.doc.__islocal) {
           frappe.call({
               method: "frappe.client.get",
               args: {
                    "doctype": "MV Mitgliedschaft",
                    "name": cur_frm.doc.mv_mitgliedschaft
               },
               callback: function(response) {
                    var mvm = response.message;
                    if (mvm) {
                       frappe.call({
                           method: "frappe.client.get",
                           args: {
                                "doctype": "Sektion",
                                "name": mvm.sektion_id
                           },
                           callback: function(response) {
                                var sektion = response.message;
                                if (sektion) {
                                   cur_frm.set_value("sektions_code", String(sektion.sektion_id));
                                   cur_frm.refresh_field("sektions_code");
                                }
                           }
                        });
                    }
               }
            });
        }
    }
});
