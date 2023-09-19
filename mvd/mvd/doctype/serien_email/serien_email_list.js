// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['Serien Email'] = {
    get_indicator: function(doc) {
        var status_color = {
            "Complete": "green",
            "New": "orange",
            "Sending": "blue",
            "Cancelled": "red"
        };
        return [__(doc.status), status_color[doc.status], "status,=,"+doc.status];
    }
};
