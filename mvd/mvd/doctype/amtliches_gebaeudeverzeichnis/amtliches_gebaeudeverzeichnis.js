// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Amtliches Gebaeudeverzeichnis', {
    refresh: function(frm) {
        frm.add_custom_button(__('Daten aktualisieren'), function() {
            frappe.call({
                method: "mvd.mvd.doctype.amtliches_gebaeudeverzeichnis.amtliches_gebaeudeverzeichnis.trigger_upload_job",
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                        frm.reload_doc();
                    }
                }
            });
        }).addClass('btn-primary');

        frm.add_custom_button(__("<i class='fa fa-map'></i> SwissTopo"),  function(){
            frappe.mvd.get_swisstopo_url(cur_frm.doc.name);
        });

    }
});