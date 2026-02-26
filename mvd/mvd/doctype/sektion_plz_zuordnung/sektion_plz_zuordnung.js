// Copyright (c) 2025, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sektion PLZ Zuordnung', {
    refresh: function(frm) {
    
        frm.add_custom_button(__('Daten aktualisieren'), function() {
			// Loading dialog with a spinner
            var d = new frappe.ui.Dialog({
                title: __('Daten werden aktualisiert'),
            });
            d.show();
            d.$wrapper.find('.modal-body').html('<div class="text-center">' + __('Bitte warten...') + '</div>');
			// Call the backend function
            frappe.call({
                method: 'mvd.mvd.doctype.sektion_plz_zuordnung.sektion_plz_zuordnung.trigger_upload_job',
                args: {},
                callback: function(r) {
					d.hide();
                    if (r.message) {
                        frappe.msgprint(__('Data uploaded successfully!'));
                    } else {
                        frappe.msgprint(__('Data upload failed.'));
                    }
                }
            });
        });
    }
});

