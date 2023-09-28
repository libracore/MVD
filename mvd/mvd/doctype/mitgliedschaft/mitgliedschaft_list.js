// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['Mitgliedschaft'] = {
    onload: function(listview) {
        listview.page.add_action_item(__("Erstelle Serienbrief"), function() {
                var selected = listview.get_checked_items();
                if (selected.length > 0) {
                    create_serienbrief(selected);
                } else {
                    frappe.msgprint("Bitte markieren Sie zuerst die gewünschten Mitgliedschaften");
                }
        });
        listview.page.add_action_item(__("Erstelle Serien E-Mail"), function() {
                var selected = listview.get_checked_items();
                if (selected.length > 0) {
                    create_serienmail(selected);
                } else {
                    frappe.msgprint("Bitte markieren Sie zuerst die gewünschten Mitgliedschaften");
                }
        });
    }
};

function create_serienbrief(mitgliedschaften) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.call({
            method: "mvd.mvd.doctype.druckvorlage.druckvorlage.get_druckvorlagen",
            args:{
                    'sektion': mitgliedschaften[0].name,
                    'serienbrief': 1
            },
            async: false,
            callback: function(res)
            {
                var druckvorlagen = res.message;
                frappe.prompt([
                    {'fieldname': 'titel', 'fieldtype': 'Data', 'label': 'Titel', 'reqd': 1},
                    {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage', 
                        'get_query': function() {
                            return { 'filters': { 'name': ['in', eval(druckvorlagen)] } };
                        }
                    }
                ],
                function(values){
                    frappe.call({
                        method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.create_korrespondenz_massenlauf",
                        args:{
                                'mitgliedschaften': mitgliedschaften,
                                'druckvorlage': values.druckvorlage,
                                'titel': values.titel
                        },
                        freeze: true,
                        freeze_message: 'Erstelle Serienbrief...',
                        callback: function(r)
                        {
                            frappe.msgprint("Die Serienbriefe wurden als Korrespondenzen erzeugt und können einzeln via Mitgliedschaft oder als Sammel-PDF via Verarbeitungszentrale gedruckt werden.");
                        }
                    });
                    
                },
                'Serienbrief Erstellung',
                'Erstellen'
                )
            }
        });
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function create_serienmail(mitgliedschaften) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.call({
            method: "mvd.mvd.page.mvd_suchmaske.mvd_suchmaske.create_serien_email",
            args:{
                    'mitglied_selektion': mitgliedschaften
            },
            freeze: true,
            freeze_message: 'Erstelle Serien E-Mail Datensatz...',
            callback: function(r)
            {
                frappe.set_route("Form", "Serien Email", r.message);
            }
        });
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

