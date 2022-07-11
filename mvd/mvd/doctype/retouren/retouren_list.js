frappe.listview_settings['Retouren'] = {
    get_indicator: function (doc) {
        if (doc.status === "Offen") {
            return [__("Offen"), "red", "status,=,Offen"];
        } else if (doc.status === "In Bearbeitung") {
            return [__("In Bearbeitung"), "orange", "status,=,In Bearbeitung"];

        } else if (doc.status === "Abgeschlossen") {
            return [__("Abgeschlossen"), "green", "status,=,Abgeschlossen"];
        }
    }
};
