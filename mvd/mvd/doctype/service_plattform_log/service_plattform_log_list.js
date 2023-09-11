// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['Service Plattform Log'] = {
    get_indicator: function(doc) {
        var status_color = {
            "New": "blue",
            "Ignore": "orange",
            "Failed": "red",
            "Done": "green"
        };
        return [__(doc.status), status_color[doc.status], "status,=,"+doc.status];
    }
};
