// Copyright (c) 2016, libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Spendenuebersicht"] = {
    "filters": [
        {
            'fieldname': "grundlage",
            'label': __("Auswertungsgrundlage"),
            'fieldtype': "Select",
            'options': '\nSektionsspezifisch\nSpendenversand\nAlles',
            'reqd': 1,
            'change': function() {
                if (frappe.query_report.get_filter("grundlage").get_value() == 'Spendenversand') {
                    frappe.query_report.get_filter("spendenversand").toggle(true);
                } else {
                    frappe.query_report.get_filter("spendenversand").toggle(false);
                }
                if (frappe.query_report.get_filter("grundlage").get_value() == 'Sektionsspezifisch') {
                    frappe.query_report.get_filter("sektion_id").toggle(true);
                } else {
                    frappe.query_report.get_filter("sektion_id").toggle(false);
                }
            }
        },
        {
            'fieldname': "spendenversand",
            'label': __("Spendenversand"),
            'fieldtype': "Link",
            'options': 'Spendenversand',
            'hidden': 1
        },
        {
            'fieldname': "sektion_id",
            'label': __("Sektion"),
            'fieldtype': "Link",
            'options': 'Sektion',
            'hidden': 1
        }
    ]
};
