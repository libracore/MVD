// Copyright (c) 2021, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Invoice', {
    validate: function(frm) {
        get_sektions_code(frm);
        if (!frm.doc.__islocal) {
            get_qrr_reference(frm);
        }
    }
});


function get_qrr_reference(frm) {
    frappe.call({
        "method": "mvd.mvd.utils.qrr_reference.get_qrr_reference",
        "args": {
            "sales_invoice": cur_frm.doc.name
        },
        "async": false,
        "callback": function(response) {
            var qrr_reference = response.message;
            cur_frm.set_value('esr_reference', qrr_reference);
        }
    });
}

function get_sektions_code(frm) {
    frappe.call({
        "method": "mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft.get_sektions_code",
        "args": {
            "company": cur_frm.doc.company
        },
        "async": false,
        "callback": function(response) {
            var sektions_code = response.message;
            cur_frm.set_value('sektions_code', sektions_code);
        }
    });
}
