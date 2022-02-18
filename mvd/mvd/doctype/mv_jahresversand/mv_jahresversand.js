// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('MV Jahresversand', {
    refresh: function(frm) {
        
    },
    start: function(frm) {
        cur_frm.set_value("start_on", frappe.datetime.now_datetime());
        cur_frm.save();
    },
    before_submit: function(frm) {
        check_end(frm);
    },
    download_draft: function(frm) {
        frappe.call({
            'method': "mvd.mvd.doctype.mv_jahresversand.mv_jahresversand.get_csv",
            'args': {
                'jahresversand': cur_frm.doc.name
            },
            'callback': function(response) {
                var csv = response.message;

                if (csv == 'done') {
                    cur_frm.reload_doc();
                }
            }
        });
    }
});

function check_end(frm) {
    if (!cur_frm.doc.end_on) {
        frappe.validated = false;
        frappe.msgprint( "Die Rechnungen wurden noch nicht erstellt.", "Rechnungen nicht erstellt" );
    }
}
