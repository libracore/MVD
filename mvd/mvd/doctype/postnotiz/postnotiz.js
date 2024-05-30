// Copyright (c) 2024, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Postnotiz', {
    refresh: function(frm) {
        if (frappe.user.has_role("System Manager")) {
            frm.add_custom_button(__("An SP senden"), function() {
                frappe.confirm(
                    'Wollen Sie die Daten an die SP senden?',
                    function(){
                        frappe.call({
                            doc: frm.doc,
                            method: "send_to_sp",
                        });
                    },
                    function(){
                        // on no
                    }
                )
            }).addClass("btn-warning")
        }
    }
});
