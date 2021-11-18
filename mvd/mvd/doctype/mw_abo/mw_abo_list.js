// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['MW Abo'] = {
    add_fields: ["status"],
    get_indicator: function(doc) {
        var colors = {
            "Aktiv terminiert": "orange",
            "Aktiv": "green",
            "Inaktiv": "red"
        };
        return [doc.status, colors[doc.status], "status,=," + doc.status];
    }
};
