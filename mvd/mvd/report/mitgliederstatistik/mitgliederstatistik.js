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
            'reqd': 1,
            'on_change': function() {
                var sektion_id = frappe.query_report.get_filter_value('sektion_id');
                var region_filter = frappe.query_report.get_filter('region');
                
                if (sektion_id) {
                    // Lade Regionen basierend auf der ausgewählten Sektion
                    frappe.call({
                        method: "frappe.client.get_list",
                        args: {
                            doctype: "Region",
                            fields: ["name"],
                            filters: {
                                "sektion_id": sektion_id
                            },
                            order_by: "name asc",
                            limit_page_length: 0
                        },
                        async: false,
                        callback: function(r) {
                            var options = ['Alle Regionen', 'Ohne Region'];
                            if (r.message) {
                                r.message.forEach(function(region) {
                                    options.push(region.name);
                                });
                            }
                            region_filter.df.options = options.join('\n');
                            region_filter.set_input('Alle Regionen');
                            region_filter.refresh();
                        }
                    });
                } else {
                    region_filter.df.options = 'Alle Regionen\nOhne Region';
                    region_filter.set_input('Alle Regionen');
                    region_filter.refresh();
                }
            }
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
        },
        {
            'fieldname': "mitgliedschafts_typ",
            'label': __("Mitgliedtyp"),
            'fieldtype': "Select",
            'options': 'Privat und Geschäft\nPrivat\nGeschäft',
            'default': 'Privat und Geschäft'
        },
        {
            'fieldname': "region",
            'label': __("Region"),
            'fieldtype': "Select",
            'options': 'Alle Regionen\nOhne Region',
            'default': 'Alle Regionen'
        }
    ],
    "onload": function(report) {
        // Lade Regionen initial wenn Sektion bereits gesetzt ist
        setTimeout(function() {
            var sektion_id = frappe.query_report.get_filter_value('sektion_id');
            if (sektion_id) {
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Region",
                        fields: ["name"],
                        filters: {
                            "sektion_id": sektion_id
                        },
                        order_by: "name asc",
                        limit_page_length: 0
                    },
                    async: false,
                    callback: function(r) {
                        var region_filter = frappe.query_report.get_filter('region');
                        var options = ['Alle Regionen', 'Ohne Region'];
                        if (r.message) {
                            r.message.forEach(function(region) {
                                options.push(region.name);
                            });
                        }
                        region_filter.df.options = options.join('\n');
                        region_filter.refresh();
                    }
                });
            }
        }, 500);
    },
    "formatter":function (value, row, column, data, default_formatter) {
        if (['Stand', 'Total', 'Zwischentotal'].includes(data["mitglieder"])||['in obiger Aufstellung bereits enthalten:', 'in obiger Aufstellung nicht enthalten:'].includes(data["berechnung"])) {
            value = $(`<span>${value}</span>`);
            var $value = $(value).css("font-weight", "bold", "important");
            value = $value.wrap("<p></p>").parent().html();
        }
        return value;
    }
};
