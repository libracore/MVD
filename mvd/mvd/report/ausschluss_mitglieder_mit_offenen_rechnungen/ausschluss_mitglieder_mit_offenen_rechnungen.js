// Copyright (c) 2016, libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Ausschluss Mitglieder mit offenen Rechnungen"] = {
	"filters": [
        {
            'fieldname': "sektion_id",
            'label': __("Sektion"),
            'fieldtype': "Link",
            'options': 'Sektion',
            'reqd': 1
        }
    ]
};
