// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Massenlauf', {
    refresh: function(frm) {
        cur_frm.disable_save();
    },
    start: function(frm) {
        cur_frm.set_value("status", "In Arbeit");
        cur_frm.save().then(function(){
            frappe.call({
                method: 'mvd.mvd.doctype.massenlauf.massenlauf.verarbeitung_massenlauf',
                args: {
                    'massenlauf': cur_frm.doc.name
                },
                callback: function(r) {
                    frappe.dom.freeze('Bitte warten, das Sammel-PDF wird erzeugt...');
                    let import_refresher = setInterval(import_refresh_handler, 3000);
                    function import_refresh_handler() {
                        if (cur_frm.doc.status == 'In Arbeit') {
                            cur_frm.reload_doc();
                        } else {
                            clearInterval(import_refresher);
                            frappe.dom.unfreeze();
                            cur_frm.reload_doc();
                        }
                    }
                    
                }
            });
        });
    }
});
