// Copyright (c) 2016, libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Beratungs Termine"] = {
    "filters": [
        {
            'fieldname': "_assign",
            'label': __("Zugewiesen"),
            'fieldtype': "Data"
        },
        {
            'fieldname': "von",
            'label': __("Datum >"),
            'fieldtype': "Date",
            'default': frappe.datetime.now_date()
        }
    ]
};
