// Copyright (c) 2025, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on("Webshop Order Download Link", {
    refresh(frm) {
        frm.add_custom_button("Generate/Update Links", function() {
            frappe.call({
                method: "mvd.mvd.doctype.webshop_order_download_link.webshop_order_download_link.generate_download_links",
                callback: function(r) {
                    frappe.msgprint(r.message);
                    frm.reload_doc();
                }
            });
        });
    }
});
