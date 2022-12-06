// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['MW Export'] = {
    add_fields: ["status"],
    get_indicator: function(doc) {
        if (doc.status == "CSV Erstellung") {
            return [__("CSV Erstellung"), "blue", "status,=," + "CSV Erstellung"]
        }
        
        if (doc.status == "Abgeschlossen") {
            return [__("Abgeschlossen"), "green", "status,=," + "Abgeschlossen"]
        }
        
        if (doc.status == "Fehlgeschlagen") {
            return [__("Fehlgeschlagen"), "red", "status,=," + "Fehlgeschlagen"]
        }
        
        if (doc.status == "Neu") {
            return [__("Neu"), "orange", "status,=," + "Neu"]
        }
    }
};
