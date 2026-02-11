// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Addresschange', {
	refresh: function(frm) {
		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.set_intro(__("Die Adressänderung ist gespeichert und automatisch am angegebenen Datum (Gültig ab) gebucht/wirksam. Buchen führt die Änderung sofort aus!"), "blue");
		}
	}
});
