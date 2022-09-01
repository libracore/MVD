// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Rechnungs Jahresversand', {
    refresh: function(frm) {

    },
    download_draft: function(frm) {
        frappe.call({
            'method': "mvd.mvd.doctype.rechnungs_jahresversand.rechnungs_jahresversand.get_draft_csv",
            'args': {
                'jahresversand': cur_frm.doc.name
            },
            'freeze': true,
            'freeze_message': 'Erstelle Entwurfs CSV...',
            'callback': function(response) {
                var csv = response.message;

                if (csv == 'done') {
                    cur_frm.reload_doc();
                }
            }
        });
    }
});
