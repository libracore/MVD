// Copyright (c) 2023, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Webshop Order', {
    refresh: function(frm) {
        if (cur_frm.doc.faktura_kunde&&cint(cur_frm.doc.faktura_kunde_aktuell)==1) {
            if (!cur_frm.doc.online_payment_id) {
                // Anlage RG aka "Lieferschein"
                frm.add_custom_button(__('Lieferschein erzeugen'), function() {
                    if (cur_frm.is_dirty()) {
                        frappe.msgprint("Bitte speichern Sie zuerst");
                    } else {
                        frappe.call({
                            method:"create_dn",
                            doc: frm.doc,
                            callback: function(response) {
                                cur_frm.reload_doc();
                            }
                        });
                    }
                }).addClass("btn-success");
            } else {
                // Anlage Rechnung
                frm.add_custom_button(__('Rechnung erzeugen'), function() {
                    if (cur_frm.is_dirty()) {
                        frappe.msgprint("Bitte speichern Sie zuerst");
                    } else {
                        frappe.call({
                            method:"create_sinv",
                            doc: frm.doc,
                            callback: function(response) {
                                cur_frm.reload_doc();
                            }
                        });
                    }
                }).addClass("btn-success");
            }
        } else {
            if (cur_frm.doc.faktura_kunde) {
                // Update Faktura Kunde
                frm.add_custom_button(__('Faktura Kunden Stammdaten updaten'), function() {
                    if (cur_frm.is_dirty()) {
                        frappe.msgprint("Bitte speichern Sie zuerst");
                    } else {
                        frappe.call({
                            method:"update_faktura_kunde",
                            doc: frm.doc,
                            callback: function(response) {
                                cur_frm.reload_doc();
                                frappe.msgprint("Der Faktura Kunde wurde angepasst.");
                            }
                        });
                    }
                }).addClass("btn-warning");
            } else {
                // Neuanlage Faktura Kunde
                frm.add_custom_button(__('Neuanlage Faktura Kunde'), function() {
                    if (cur_frm.is_dirty()) {
                        frappe.msgprint("Bitte speichern Sie zuerst");
                    } else {
                        frappe.call({
                            method:"create_faktura_kunde",
                            doc: frm.doc,
                            callback: function(response) {
                                cur_frm.reload_doc();
                            }
                        });
                    }
                }).addClass("btn-warning");
            }
        }
    }
});
