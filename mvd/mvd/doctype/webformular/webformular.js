// Copyright (c) 2025, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('WebFormular', {
	refresh: function(frm) {
	frm.add_custom_button("Export JSON as CSV", function() {
		if (!frm.doc.form_id) {
			frappe.msgprint("Please set a FormID first.");
			return;
		}
		
		frappe.call({
			method: "mvd.mvd.doctype.webformular.webformular.export_form_data_as_csv", // backend method (see below)
			args: {
				form_id: frm.doc.form_id
			},
			callback: function(r) {
				if (r.message) {
					let blob = new Blob([r.message], { type: "text/csv;charset=utf-8;" });
					let link = document.createElement("a");
					link.href = URL.createObjectURL(blob);
					link.download = `WebFormular_${frm.doc.form_id}.csv`;
					link.click();
				}
			}
		});
	});
}
});

