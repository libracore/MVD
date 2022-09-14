// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fakultative Rechnung', {
    onload: function(frm) {
        if (frm.doc.__islocal) {
           frappe.call({
               method: "frappe.client.get",
               args: {
                    "doctype": "Mitgliedschaft",
                    "name": cur_frm.doc.mv_mitgliedschaft
               },
               callback: function(response) {
                    var mvm = response.message;
                    if (mvm) {
                       frappe.call({
                           method: "frappe.client.get",
                           args: {
                                "doctype": "Sektion",
                                "name": mvm.sektion_id
                           },
                           callback: function(response) {
                                var sektion = response.message;
                                if (sektion) {
                                   cur_frm.set_value("sektions_code", String(sektion.sektion_id));
                                   cur_frm.refresh_field("sektions_code");
                                }
                           }
                        });
                    }
               }
            });
        }
    },
    refresh(frm) {
        if (!frm.doc.__islocal) {
            if (cur_frm.doc.status == 'Unpaid') {
                frm.add_custom_button(__("Bezahlt mit EZS"), function() {
                    bezahlt_mit_ezs(frm);
                });
                frm.add_custom_button(__("Bezahlt in Bar"), function() {
                    bezahlt_in_bar(frm);
                });
            }
        }
    }
});

function bezahlt_in_bar(frm) {
    frappe.prompt([
        {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Zahlungsdatum', 'reqd': 1},
        {'fieldname': 'betrag', 'fieldtype': 'Currency', 'label': 'Betrag', 'reqd': 1, 'default': cur_frm.doc.typ == 'HV' ? 10:0, 'read_only': cur_frm.doc.typ == 'HV' ? 1:0}
    ],
    function(values){
        frappe.call({
            method:"mvd.mvd.doctype.camt_import.camt_import.fr_bez_bar",
            'args': {
                'fr': cur_frm.doc.name,
                'datum': values.datum,
                'betrag': values.betrag
            },
            'async': true,
            'freeze': true,
            'freeze_message': 'Verbuche Zahlung...',
            'callback': function(r) {
                cur_frm.reload_doc();
            }
        });
    },
    'Zahlungsdatum',
    'Ausführen'
    )
}

function bezahlt_mit_ezs(frm) {
    frappe.prompt([
        {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Zahlungsdatum', 'reqd': 1},
        {'fieldname': 'betrag', 'fieldtype': 'Currency', 'label': 'Betrag', 'reqd': 1, 'default': cur_frm.doc.typ == 'HV' ? 10:0, 'read_only': cur_frm.doc.typ == 'HV' ? 1:0}
    ],
    function(values){
        frappe.call({
            method:"mvd.mvd.doctype.camt_import.camt_import.fr_bez_ezs",
            'args': {
                'fr': cur_frm.doc.name,
                'datum': values.datum,
                'betrag': values.betrag
            },
            'async': true,
            'freeze': true,
            'freeze_message': 'Verbuche Zahlung...',
            'callback': function(r) {
                cur_frm.reload_doc();
            }
        });
    },
    'Zahlungsdatum',
    'Ausführen'
    )
}
