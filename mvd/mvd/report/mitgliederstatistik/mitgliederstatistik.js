// Copyright (c) 2016, libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Mitgliederstatistik"] = {
    "filters": [
        {
            'fieldname': "sektion_id",
            'label': __("Sektion"),
            'fieldtype': "Link",
            'options': 'Sektion',
            'reqd': 1
        },
        {
            'fieldname': "from_date",
            'label': __("Datum von"),
            'fieldtype': "Date",
            'default': frappe.datetime.add_months(frappe.datetime.month_start(), -1),
            'reqd': 1
        },
        {
            'fieldname': "to_date",
            'label': __("Datum bis"),
            'fieldtype': "Date",
            'default': frappe.datetime.add_months(frappe.datetime.month_end(), -1),
            'reqd': 1
        }
    ],
    "formatter":function (value, row, column, data, default_formatter) {
        if (['Stand', 'Total', 'Zwischentotal'].includes(data["mitglieder"])||['in obiger Aufstellung bereits enthalten:', 'in obiger Aufstellung nicht enthalten:'].includes(data["berechnung"])) {
            value = $(`<span>${value}</span>`);
            var $value = $(value).css("font-weight", "bold", "important");
            value = $value.wrap("<p></p>").parent().html();
        }
        return value;
    }
};
