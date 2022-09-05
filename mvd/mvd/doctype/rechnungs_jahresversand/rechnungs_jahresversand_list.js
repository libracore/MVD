// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['Rechnungs Jahresversand'] = {
    add_fields: ["status"],
    get_indicator: function(doc) {
        if (doc.status == "Vorgemerkt") {
            return [__("Vorgemerkt"), "orange", "status,=," + "Vorgemerkt"]
        }
        
        if (doc.status == "In Arbeit") {
            return [__("In Arbeit"), "blue", "status,=," + "In Arbeit"]
        }
        
        if (doc.status == "Abgeschlossen") {
            return [__("Abgeschlossen"), "green", "status,=," + "Abgeschlossen"]
        }
        
        if (doc.status == "Fehlgeschlagen") {
            return [__("Fehlgeschlagen"), "red", "status,=," + "Fehlgeschlagen"]
        }
        
        if (doc.status == "Storniert") {
            return [__("Storniert"), "red", "status,=," + "Storniert"]
        }
    }
};
