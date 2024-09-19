// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['Rechnungs Jahresversand'] = {
    add_fields: ["status"],
    get_indicator: function(doc) {
        if (doc.status == "Bereit zur Ausführung") {
            return [__("Bereit zur Ausführung"), "orange", "status,=," + "Bereit zur Ausführung"]
        }
        
        if (doc.status == "Rechnungsdaten in Arbeit") {
            return [__("Rechnungsdaten in Arbeit"), "blue", "status,=," + "Rechnungsdaten in Arbeit"]
        }
        
        if (doc.status == "CSV in Arbeit") {
            return [__("CSV in Arbeit"), "blue", "status,=," + "CSV in Arbeit"]
        }

        if (doc.status == "Rechnungsdaten und CSV erstellt") {
            return [__("Rechnungsdaten und CSV erstellt"), "orange", "status,=," + "Rechnungsdaten und CSV erstellt"]
        }
        
        if (doc.status == "Vorgemerkt für Rechnungsverbuchung") {
            return [__("Vorgemerkt für Rechnungsverbuchung"), "blue", "status,=," + "Vorgemerkt für Rechnungsverbuchung"]
        }
        
        if (doc.status == "Rechnungsverbuchung in Arbeit") {
            return [__("Rechnungsverbuchung in Arbeit"), "blue", "status,=," + "Rechnungsverbuchung in Arbeit"]
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
