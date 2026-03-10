// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['MVD Email Queue'] = {
    add_fields: ["status"],
    get_indicator: function(doc) {
        if (doc.blocked) {
            return [__("Gesperrt"), "red", "blocked,=,1"]
        }
        
        if (doc.status == "Not send") {
            return [__("In Warteschlange"), "orange", "status,=," + "Not send"]
        }
        
        if (doc.status == "Partially send") {
            return [__("Partially send"), "blue", "status,=," + "In Arbeit"]
        }
        
        if (doc.status == "Sending finished with errors") {
            return [__("Fehlerhaft"), "red", "status,=,Sending finished with errors"]
        }
        
        if (doc.status == "Send") {
            return [__("Gesendet"), "green", "status,=," + "Send"]
        }
    }
};
