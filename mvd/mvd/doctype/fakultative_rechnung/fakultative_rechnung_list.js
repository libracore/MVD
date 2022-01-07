// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['Fakultative Rechnung'] = {
    add_fields: ["status"],
    get_indicator: function(doc) {
        if (doc.status== "Unpaid") {
            return [__("Unpaid"), "orange", "status,=," + "Unpaid"]
        }
        
        if (doc.status== "Paid") {
            return [__("Paid"), "green", "status,=," + "Paid"]
        }
    }
};
