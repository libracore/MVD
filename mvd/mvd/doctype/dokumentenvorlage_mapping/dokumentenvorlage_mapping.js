// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Dokumentenvorlage Mapping', {
    refresh: function(frm) {
        frm.add_custom_button(__("Mail-IN DMC Platzhalter-Bild"), function() {
            window.open('/assets/mvd/img/dmc_dummy_bild.png', '_blank');
        }, "Download");
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