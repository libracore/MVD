// Copyright (c) 2016, libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Email an Coop senden"] = {
"filters": [
    ],
    "onload": function(report) {
        report.page.main.on("click", ".btn-send-coop-email", function() {
            let docname = $(this).attr("data-name");

            frappe.call({
                method: "mvd.mvd.doctype.rsvmitglied.rsvmitglied.get_coop_email_data",
                args: { "docname": docname },
                freeze: true,
                freeze_message: __('E-Mail-Daten werden geladen (ZIP wird erstellt)...'),
                callback: function(r) {
                    if (!r.exc && r.message) {
                        var mail_data = r.message;

                        let d = new frappe.ui.Dialog({
                            title: __('E-Mail an Coop: ' + docname),
                            size: 'large',
                            fields: [
                                {fieldtype: 'Data', fieldname: 'recipients', label: 'An', reqd: 1, default: mail_data.recipients},
                                {fieldtype: 'Data', fieldname: 'cc', label: 'CC', default: mail_data.cc},
                                {fieldtype: 'Data', fieldname: 'subject', label: 'Betreff', reqd: 1, default: mail_data.subject},
                                {fieldtype: 'Text Editor', fieldname: 'content', label: 'Nachricht', reqd: 1, default: mail_data.content}
                            ],
                            primary_action_label: __('Senden'),
                            primary_action: function(values) {
                                d.get_primary_btn().prop('disabled', true);

                                frappe.call({
                                    method: "mvd.mvd.doctype.rsvmitglied.rsvmitglied.send_coop_email_custom",
                                    args: {
                                        docname: docname,
                                        recipients: values.recipients,
                                        cc: values.cc,
                                        subject: values.subject,
                                        content: values.content
                                    },
                                    freeze: true,
                                    freeze_message: __('E-Mail wird versendet...'),
                                    callback: function(send_r) {
                                        if (!send_r.exc) {
                                            frappe.show_alert({
                                                message: __('E-Mail für {0} erfolgreich gesendet.', [docname]), 
                                                indicator: 'green'
                                            });
                                            d.hide();
                                            report.refresh();
                                        } else {
                                            d.get_primary_btn().prop('disabled', false);
                                        }
                                    }
                                });
                            }
                        });
                        d.show();
                    }
                }
            });
        });
    }
};