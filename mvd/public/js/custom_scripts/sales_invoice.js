// Copyright (c) 2021, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        if (cur_frm.doc.outstanding_amount > 0) {
            check_for_hv(frm);
        }
        // hack to default buttons
        setTimeout(function(){
            $("[data-label='Create']").remove();
        }, 500);
    },
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
        "method": "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_sektions_code",
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

function bezahlt_mit_ezs(frm, hv_check) {
    if (frappe.user.has_role("MV_RW")) {
        if (hv_check) {
            frappe.prompt([
                {'fieldname': 'hv', 'fieldtype': 'Check', 'label': 'Inkl. HV?', 'reqd': 0, 'default': 0}  
            ],
            function(values){
                if (values.hv) {
                    erstelle_zahlung(hv_check, true);
                } else {
                    erstelle_zahlung(false, true);
                }
            },
            'Mit oder ohne HV',
            'Ausführen'
            )
        } else {
            erstelle_zahlung(false, true);
        }
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function bezahlt_in_bar(frm, hv_check) {
    if (frappe.user.has_role("MV_RW")) {
        if (hv_check) {
            frappe.prompt([
                {'fieldname': 'hv', 'fieldtype': 'Check', 'label': 'Inkl. HV?', 'reqd': 0, 'default': 0}  
            ],
            function(values){
                if (values.hv) {
                    erstelle_zahlung(hv_check, false);
                } else {
                    erstelle_zahlung(false, false);
                }
            },
            'Mit oder ohne HV',
            'Ausführen'
            )
        } else {
            erstelle_zahlung(false, false);
        }
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function check_for_hv(frm) {
    frappe.call({
        method:"frappe.client.get_list",
        args:{
            doctype:"Fakultative Rechnung",
            filters: [
                ["typ","=","HV"],
                ["status","=","Unpaid"],
                ["sales_invoice","=", cur_frm.doc.name]
            ],
            fields: ["name"]
        },
        async: false,
        callback: function(r) {
            if (r.message.length > 0) {
                frm.add_custom_button(__("Bezahlt mit EZS"), function() {
                    bezahlt_mit_ezs(frm, r.message[0].name);
                });
                frm.add_custom_button(__("Bezahlt in Bar"), function() {
                    bezahlt_in_bar(frm, r.message[0].name);
                });
            } else {
                frm.add_custom_button(__("Bezahlt mit EZS"), function() {
                    bezahlt_mit_ezs(frm, false);
                });
                frm.add_custom_button(__("Bezahlt in Bar"), function() {
                    bezahlt_in_bar(frm, false);
                });
            }
        }
    });
}

function erstelle_zahlung(hv, ezs) {
    console.log(hv);
    console.log(ezs);
    var args;
    if (ezs) {
        if (hv) {
            args = {
                'sinv': cur_frm.doc.name,
                'hv': hv,
                'ezs': 1
            }
        } else {
            args = {
                'sinv': cur_frm.doc.name,
                'ezs': 1
            }
        }
    } else {
        if (hv) {
            args = {
                'sinv': cur_frm.doc.name,
                'hv': hv,
                'bar': 1
            }
        } else {
            args = {
                'sinv': cur_frm.doc.name,
                'bar': 1
            }
        }
    }
    frappe.call({
        method:"mvd.mvd.doctype.camt_import.camt_import.sinv_bez_mit_ezs_oder_bar",
        'args': args,
        'async': false,
        'callback': function(r) {
            //
        }
    });
}
