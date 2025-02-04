// Copyright (c) 2024, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Digitalrechnung', {
    refresh: function(frm) {
        if(cur_frm.doc.email_changed == 1) {
            cur_frm.add_custom_button(__("E-Mail kontrolliert"),  function() { cur_frm.set_value("email_changed", 0) });
            cur_frm.save();
        }
    }
});
