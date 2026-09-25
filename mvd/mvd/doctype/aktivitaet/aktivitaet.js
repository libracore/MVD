// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Aktivitaet', {
    refresh: function(frm) {
        frappe.mvd.render_nextcloud_files_tree(frm);
    },
    mv_mitgliedschaft: function(frm) {
        frappe.mvd.render_nextcloud_files_tree(frm);
    },
    sektion_id: function(frm) {
        frappe.mvd.render_nextcloud_files_tree(frm);
    },
    refresh_files_tree: function(frm) {
        frappe.mvd.render_nextcloud_files_tree(frm);
    }
});
