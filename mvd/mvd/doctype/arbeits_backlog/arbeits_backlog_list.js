// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['Arbeits Backlog'] = {
    get_indicator: function(doc) {
        var status_color = {
            "Completed": "green",
            "Open": "red"
        };
        return [__(doc.status), status_color[doc.status], "status,=,"+doc.status];
    }
};
