// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['RSVMitglied'] = {
    add_fields: ["status", "dringend"],
    get_indicator: function(doc) {
        // Dringende RSV-Mitglieder rot hervorheben (#2199), sonst Standard-Indikator nach Status
        if (doc.dringend) {
            let label = doc.status ? __("Dringend") + ": " + __(doc.status) : __("Dringend");
            return [label, "red", "dringend,=,1"];
        }
    }
};
