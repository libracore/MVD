frappe.listview_settings['SP Data Transfer Log'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Transfer starten"), function() {
            open_transfer_service_plattform_logs_dialog();
        });
    }
}

function open_transfer_service_plattform_logs_dialog() {
    const dialog = new frappe.ui.Dialog({
        title: __('Service Plattform Logs übertragen'),
        fields: [
            {
                fieldname: 'target_url',
                fieldtype: 'Data',
                label: __('Ziel-URL'),
                reqd: 1,
                description: __('URL der Zielinstanz')
            },
            {
                fieldname: 'api_key',
                fieldtype: 'Data',
                label: __('API Key'),
                reqd: 1
            },
            {
                fieldname: 'api_secret',
                fieldtype: 'Password',
                label: __('API Secret'),
                reqd: 1
            },
            {
                fieldname: 'from_date',
                fieldtype: 'Date',
                label: __('Ab Datum'),
                reqd: 1,
                default: frappe.datetime.add_days(frappe.datetime.get_today(), -7)
            },
            {
                fieldname: 'limit',
                fieldtype: 'Int',
                label: __('Limit'),
                description: __('Maximale Anzahl zu übertragender Logs'),
                reqd: 1,
                default: 1000
            }
        ],
        primary_action_label: __('Übertragung starten'),
        primary_action(values) {
            frappe.call({
                method: 'mvd.mvd.doctype.sp_data_transfer_log.sp_data_transfer_log.request_transfer_service_plattform_logs',
                args: {
                    target_url: values.target_url,
                    api_key: values.api_key || null,
                    api_secret: values.api_secret || null,
                    from_date: values.from_date || null,
                    limit: values.limit || null
                },
                freeze: true,
                freeze_message: __('Übertragung wird gestartet...'),
                callback: function(r) {
                    if (!r.exc) {
                        dialog.hide();

                        frappe.show_alert({
                            message: __('Übertragung wurde als Background Job gestartet.'),
                            indicator: 'green'
                        });
                    }
                }
            });
        }
    });

    dialog.show();
}