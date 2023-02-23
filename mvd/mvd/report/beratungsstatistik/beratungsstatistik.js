// Copyright (c) 2016, libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Beratungsstatistik"] = {
    "filters": [
        {
            'fieldname': "from",
            'label': __("Von"),
            'fieldtype': "Date",
            'reqd': 1,
            'default': frappe.datetime.year_start()
        },
        {
            'fieldname': "to",
            'label': __("Bis"),
            'fieldtype': "Date",
            'reqd': 1,
            'default': frappe.datetime.now_date()
        }
    ]
};
