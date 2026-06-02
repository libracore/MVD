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

frappe.ui.form.on("Dokumentenvorlage Mapping TBL", {
    d_type: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        frappe.call({
            method: "mvd.mvd.doctype.dokumentenvorlage.dokumentenvorlage.get_doc_fields",
            args: {
                doctype: row.d_type
            },
            callback: function(r) {
                let options = [""];

                (r.message || []).forEach(function(df) {
                    options.push(df.fieldname);
                });

                frappe.model.set_value(cdt, cdn, "field", "");

                let grid_row = frm.fields_dict.mapping_tbl.grid.grid_rows_by_docname[cdn];

                if (grid_row && grid_row.grid_form) {
                    let field_control = grid_row.grid_form.fields_dict.field;

                    field_control.df.options = options.join("\n");
                    field_control.refresh();
                }
            }
        });
    },

    form_render: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (!row.d_type) {
            return;
        }

        frappe.call({
            method: "mvd.mvd.doctype.dokumentenvorlage.dokumentenvorlage.get_doc_fields",
            args: {
                doctype: row.d_type
            },
            callback: function(r) {
                let options = [""];

                (r.message || []).forEach(function(df) {
                    options.push(df.fieldname);
                });

                let grid_row = frm.fields_dict.mapping_tbl.grid.grid_rows_by_docname[cdn];

                if (grid_row && grid_row.grid_form) {
                    let field_control = grid_row.grid_form.fields_dict.field;

                    field_control.df.options = options.join("\n");
                    field_control.refresh();
                }
            }
        });
    }
});