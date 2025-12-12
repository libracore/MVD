// Copyright (c) 2016, libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Mitglieder ohne Jahresrechnung"] = {
    "filters": [
        {
            'fieldname': "sektion_id",
            'label': __("Sektion"),
            'fieldtype': "Link",
            'options': 'Sektion',
            'reqd': 1
        },
        {
            'fieldname': "jahr",
            'label': __("Mitgliedschaftsjahr"),
            'fieldtype': "Int",
            'reqd': 1
        }
    ]
};
