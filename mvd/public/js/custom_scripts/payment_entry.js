// Copyright (c) 2021, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Entry', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            if (cur_frm.doc.unallocated_amount > 0) {
                frm.add_custom_button(__("Mitgliedschafts-Korrespondenz erstellen"), function() {
                    frappe.msgprint("Muss noch programmiert werden!");
                });
                if ((cur_frm.doc.paid_amount / cur_frm.doc.unallocated_amount) == 2) {
                    frm.add_custom_button(__("Mit Folgejahr-Mitgliedschaft ausgleichen"), function() {
                        frappe.msgprint("Muss noch programmiert werden!");
                    });
                }
                frm.add_custom_button(__("Mit Spende ausgleichen"), function() {
                    frappe.msgprint("Muss noch programmiert werden!");
                });
                frm.add_custom_button(__("Mit Rückzahlung ausgleichen"), function() {
                    frappe.msgprint("Muss noch programmiert werden!");
                });
            }
        }
    }
});
