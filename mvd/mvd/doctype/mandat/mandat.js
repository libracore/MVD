// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mandat', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('Suche Vertrauensanwält*in'), function() {
                frappe.call({
                    method: 'mvd.mvd.doctype.mandat.mandat.suche_vertrauensanwaeltin',
                    args: {
                        "mandat_id": frm.doc.name,
						"sektion_id": frm.doc.sektion_id
                    },
                    freeze: true,
                    callback: function(r) {
                        if (!r.exc && r.message) {
                            frappe.msgprint(__("Benachrichtigung wurde erfolgreich an {0} Vertrauensanwält*in(nen) gesendet.").replace('{0}', r.message));
                        }
                    }
                });

            });
        }
    }
});
