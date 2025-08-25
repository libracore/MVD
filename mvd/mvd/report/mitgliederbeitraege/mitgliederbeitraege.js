// Copyright (c) 2016, libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Mitgliederbeitraege"] = {
    "filters": [
        {
            'fieldname': "sektion_id",
            'label': __("Sektion"),
            'fieldtype': "Link",
            'options': 'Sektion',
            'reqd': 1
        },
        {
            'fieldname': "zahlstatus",
            'label': __("Zahlungsstatus"),
            'fieldtype': "Select",
            'options': 'Offen\nBeglichen\nAlle',
            'default': 'Alle'
        },
        {
            'fieldname': "jahr",
            'label': __("Mitgliedschaftsjahr"),
            'fieldtype': "Data"
        }
    ]
};
