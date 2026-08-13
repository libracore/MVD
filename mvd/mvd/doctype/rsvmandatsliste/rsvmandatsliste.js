// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('RSVMandatsliste', {
    refresh: function(frm) {
        frm.add_custom_button(__("Vergabeliste"),  function() {
            var domain = window.location.origin;
            window.open(`${domain}/va/vergabeliste`, '_blank');
        }, "Öffne");
        frm.add_custom_button(__("Meine-Mandate"),  function() {
            var domain = window.location.origin;
            window.open(`${domain}/va/meine-mandate`, '_blank');
        }, "Öffne");
    }
});
