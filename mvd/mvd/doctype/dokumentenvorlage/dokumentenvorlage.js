// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Dokumentenvorlage', {
    refresh: function(frm) {
        frm.add_custom_button(__("Teste mich"), function() {
            frappe.prompt([
                {'fieldname': 'json', 'fieldtype': 'Code', 'label': 'Replacement JSON', 'reqd': 1}
            ],
            function(values){
                show_alert(values, 5);
                frappe.call({
                    method: "mvd.mvd.utils.document_template_handler.use_template",
                    args:{
                            'template': cur_frm.doc.name,
                            'replacements': values.json,
                            'test': true
                    },
                    freeze: true,
                    freeze_message: 'Verarbeite Vorlage...',
                    callback: function(r)
                    {
                        cur_frm.reload_doc();
                    }
                });
            },
            'Vorlagen Test',
            'Go'
            );
        });
    }
});
