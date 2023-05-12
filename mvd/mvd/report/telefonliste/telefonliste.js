// Copyright (c) 2016, libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Telefonliste"] = {
    "filters": [
        {
            'fieldname': "sektion",
            'label': __("Sektion"),
            'fieldtype': "Link",
            'options': "Sektion"
        }
    ]
};
