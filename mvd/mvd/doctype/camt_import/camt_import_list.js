// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['CAMT Import'] = {
    add_fields: ["status"],
    get_indicator: function(doc) {
        if (doc.status == "Verarbeitet") {
            return [__("Verarbeitet"), "blue", "status,=," + "Verarbeitet"]
        }
        
        if (doc.status == "In Verarbeitung") {
            return [__("In Verarbeitung"), "orange", "status,=," + "In Verarbeitung"]
        }
        
        if (doc.status == "Zahlungen eingelesen - verbuche Matches") {
            return [__("Zahlungen eingelesen - verbuche Matches"), "orange", "status,=," + "Zahlungen eingelesen - verbuche Matches"]
        }
        
        if (doc.status == "Closed") {
            return [__("Closed"), "green", "status,=," + "Closed"]
        }
        
        if (doc.status == "Failed") {
            return [__("Failed"), "red", "status,=," + "Failed"]
        }
        
        if (doc.status == "Open") {
            return [__("Open"), "red", "status,=," + "Open"]
        }
    }
};
