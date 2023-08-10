// Copyright (c) 2016, libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Beratungen MVZH"] = {
    "filters": [
        {
            'fieldname': "sektion",
            'label': __("Sektion"),
            'fieldtype': "Link",
            'options': 'Sektion',
            'default': 'MVZH'
        },
        {
            'fieldname': "von",
            'label': __("Datum >="),
            'fieldtype': "Date",
            'default': frappe.datetime.now_date(),
            'reqd': 1
        },
        {
            'fieldname': "bis",
            'label': __("Datum <="),
            'fieldtype': "Date",
            'default': frappe.datetime.now_date(),
            'reqd': 1
        }
    ]
};
