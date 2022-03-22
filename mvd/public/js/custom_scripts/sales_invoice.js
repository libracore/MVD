// Copyright (c) 2021, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        if (cur_frm.doc.outstanding_amount > 0) {
            check_for_hv(frm);
        }
        if ((cur_frm.doc.docstatus == 2)&&(frappe.user.has_role("Administrator"))) {
            frm.add_custom_button(__("Storno Rollback"), function() {
                storno_rollback(frm);
            });
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
                {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Zahlungsdatum', 'reqd': 1},
                {'fieldname': 'betrag', 'fieldtype': 'Currency', 'label': 'Betrag (exkl. HV)', 'reqd': 1, 'default': cur_frm.doc.outstanding_amount},
                {'fieldname': 'hv', 'fieldtype': 'Check', 'label': 'Inkl. HV?', 'reqd': 0, 'default': 0}
            ],
            function(values){
                if (values.hv) {
                    erstelle_zahlung(hv_check, true, values.datum, values.betrag);
                } else {
                    erstelle_zahlung(false, true, values.datum, values.betrag);
                }
            },
            'Zahlungsdetails',
            'Ausführen'
            )
        } else {
            frappe.prompt([
                {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Zahlungsdatum', 'reqd': 1},
                {'fieldname': 'betrag', 'fieldtype': 'Currency', 'label': 'Betrag (exkl. HV)', 'reqd': 1, 'default': cur_frm.doc.outstanding_amount}
            ],
            function(values){
                erstelle_zahlung(false, true, values.datum, values.betrag);
            },
            'Zahlungsdetails',
            'Ausführen'
            )
        }
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function bezahlt_in_bar(frm, hv_check) {
    if (frappe.user.has_role("MV_RW")) {
        if (hv_check) {
            frappe.prompt([
                {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Zahlungsdatum', 'reqd': 1, 'default': frappe.datetime.get_today()},
                {'fieldname': 'betrag', 'fieldtype': 'Currency', 'label': 'Betrag (exkl. HV)', 'reqd': 1, 'default': cur_frm.doc.outstanding_amount},
                {'fieldname': 'hv', 'fieldtype': 'Check', 'label': 'Inkl. HV?', 'reqd': 0, 'default': 0}  
            ],
            function(values){
                if (values.hv) {
                    erstelle_zahlung(hv_check, false, values.datum, values.betrag);
                } else {
                    erstelle_zahlung(false, false, values.datum, values.betrag);
                }
            },
            'Zahlungsdetails',
            'Ausführen'
            )
        } else {
            frappe.prompt([
                {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Zahlungsdatum', 'reqd': 1, 'default': frappe.datetime.get_today()},
                {'fieldname': 'betrag', 'fieldtype': 'Currency', 'label': 'Betrag (exkl. HV)', 'reqd': 1, 'default': cur_frm.doc.outstanding_amount}
            ],
            function(values){
                erstelle_zahlung(false, false, values.datum, values.betrag);
            },
            'Zahlungsdetails',
            'Ausführen'
            )
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

function erstelle_zahlung(hv, ezs, datum=false, betrag=false) {
    var args;
    if (ezs) {
        if (hv) {
            args = {
                'sinv': cur_frm.doc.name,
                'hv': hv,
                'ezs': 1,
                'datum': datum,
                'betrag': betrag
            }
        } else {
            args = {
                'sinv': cur_frm.doc.name,
                'ezs': 1,
                'datum': datum,
                'betrag': betrag
            }
        }
    } else {
        if (hv) {
            args = {
                'sinv': cur_frm.doc.name,
                'hv': hv,
                'bar': 1,
                'datum': datum,
                'betrag': betrag
            }
        } else {
            args = {
                'sinv': cur_frm.doc.name,
                'bar': 1,
                'datum': datum,
                'betrag': betrag
            }
        }
    }
    frappe.call({
        method:"mvd.mvd.doctype.camt_import.camt_import.sinv_bez_mit_ezs_oder_bar",
        'args': args,
        'async': true,
        'freeze': true,
        'freeze_message': 'Verbuche Zahlung...',
        'callback': function(r) {
            cur_frm.reload_doc();
        }
    });
}

//~ function ask_for_date(hv, ezs) {
    //~ frappe.prompt([
        //~ {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Zahlungsdatum', 'reqd': 1}  
    //~ ],
    //~ function(values){
        //~ var datum = values.datum;
        //~ var args;
        //~ if (ezs) {
            //~ if (hv) {
                //~ args = {
                    //~ 'sinv': cur_frm.doc.name,
                    //~ 'hv': hv,
                    //~ 'ezs': 1,
                    //~ 'datum': datum
                //~ }
            //~ } else {
                //~ args = {
                    //~ 'sinv': cur_frm.doc.name,
                    //~ 'ezs': 1,
                    //~ 'datum': datum
                //~ }
            //~ }
        //~ } else {
            //~ if (hv) {
                //~ args = {
                    //~ 'sinv': cur_frm.doc.name,
                    //~ 'hv': hv,
                    //~ 'bar': 1,
                    //~ 'datum': datum
                //~ }
            //~ } else {
                //~ args = {
                    //~ 'sinv': cur_frm.doc.name,
                    //~ 'bar': 1,
                    //~ 'datum': datum
                //~ }
            //~ }
        //~ }
        //~ frappe.call({
            //~ method:"mvd.mvd.doctype.camt_import.camt_import.sinv_bez_mit_ezs_oder_bar",
            //~ 'args': args,
            //~ 'async': true,
            //~ 'freeze': true,
            //~ 'freeze_message': 'Verbuche Zahlung...',
            //~ 'callback': function(r) {
                //~ cur_frm.reload_doc();
            //~ }
        //~ });
    //~ },
    //~ 'Zahlungsdatum',
    //~ 'Ausführen'
    //~ )
//~ }

function storno_rollback(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.camt_import.camt_import.reopen_sinv_as_admin",
        args:{
                'sinv': cur_frm.doc.name
        },
        callback: function(r)
        {
            cur_frm.reload_doc();
        }
    });
}
