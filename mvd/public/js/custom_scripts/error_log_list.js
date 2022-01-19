// Copyright (c) 2021-2022, libracore AG and contributors
// For license information, please see license.txt

frappe.listview_settings['Error Log'] = {
    onload: function(listview) {
        listview.page.add_menu_item(__("Analyse SP API Logs"), function() {
            analyse();
        });
    }
}

function analyse() {
    frappe.call({
        "method": "mvd.mvd.utils.api_error_analysis.analyse_error_log",
        "args": {},
        "freeze": true,
        "freeze_message": 'Analysiere Error Log...',
        "callback": function(r) {
            frappe.msgprint("Die Resultate befinden sich in der Web-Konsole");
            console.log("Analyse Bericht:");
            console.log(r.message);
        }
    });
}
