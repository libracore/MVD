// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Massenlauf Inaktivierung', {
    refresh: function(frm) {
        if (!cur_frm.doc.sektion_id) {
            cur_frm.set_value("sektion_id", frappe.boot.default_sektion);
        }
        if (frm.doc.docstatus === 1 && frm.doc.status !== 'Abgeschlossen' && frm.perm[0].write) {
            frm.add_custom_button(__('Fortsetzen'), function() {
                var message = 'Offene und fehlgeschlagene Mitgliedschafts-Inaktivierungen fortsetzen? Bereits vollständig verarbeitete werden übersprungen.';
                frappe.confirm(
                    message,
                    function() {
                        frappe.call({
                            method: 'mvd.mvd.doctype.massenlauf_inaktivierung.massenlauf_inaktivierung.fortsetzen',
                            args: {doc: frm.doc.name},
                            freeze: true,
                            callback: function(r) {
                                if (!r.exc) {
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            });
        }
    }
});
