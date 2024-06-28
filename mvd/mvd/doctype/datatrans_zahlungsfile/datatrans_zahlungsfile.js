// Copyright (c) 2023, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Datatrans Zahlungsfile', {
    btn_file_einlesen: function(frm) {
        if (frm.doc.datatrans_entries.length > 0) {
            frappe.msgprint("Das File wurde bereits eingelesen");
        } else {
            frappe.call({
                method: 'read_file',
                doc: frm.doc,
                freeze: true,
                freeze_message: "Bitte warten, das File wird eingelesen...",
                callback: function(response) {
                    frappe.show_alert( __("Done!") );
                    cur_frm.reload_doc();
                }
            });
        }
    },
    btn_daten_verarbeiten: function(frm) {
        frappe.call({
            method: 'process_data',
            doc: frm.doc,
            freeze: true,
            freeze_message: "Bitte warten, die Daten werden verarbeitet...",
            callback: function(response) {
                frappe.show_alert( __("Done!") );
                cur_frm.reload_doc();
            }
        });
    },
    btn_reset: function(frm) {
        frappe.call({
            method: 'reset_data',
            doc: frm.doc,
            freeze: true,
            freeze_message: "Bitte warten, die Daten werden zurückgesetzt...",
            callback: function(response) {
                frappe.show_alert( __("Done!") );
                cur_frm.reload_doc();
            }
        });
    },
    btn_single_report: function(frm) {
        frm.set_value("ignore_missing_files", 1);
        frm.save().then(() => {
            frappe.call({
                method: 'create_single_report',
                doc: frm.doc,
                freeze: true,
                freeze_message: "Bitte warten, der Report wird erzeugt...",
                callback: function(response) {
                    frappe.show_alert( __("Done!") );
                    cur_frm.reload_doc();
                }
            });
        });
    },
    btn_erzeuge_reports: function(frm) {
        frm.set_value("ignore_missing_files", 0);
        frm.save().then(() => {
            frappe.prompt([
                {'fieldname': 'year', 'fieldtype': 'Int', 'label': 'Jahr', 'reqd': 1},
                {'fieldname': 'month', 'fieldtype': 'Select', 'label': 'Monat', 'reqd': 1, 'options': 'Januar\nFebruar\nMärz\nApril\nMai\nJuni\nJuli\nAugust\nSeptember\nOktober\nNovember\nDezember'},
                {'fieldname': 'kommissions_prozent', 'fieldtype': 'Percent', 'label': 'Kommissions Prozent', 'reqd': 1}
            ],
            function(values){
                frm.set_value("report_year", values.year);
                frm.set_value("report_month", values.month);
                frm.set_value("kommissions_prozent", values.kommissions_prozent);
                frm.save().then(() => {
                    frappe.call({
                        method: 'create_reports',
                        doc: frm.doc,
                        freeze: true,
                        freeze_message: "Bitte warten, die Reporte werden erzeugt...",
                        callback: function(response) {
                            if (response.message == 'missing_files') {
                                cur_frm.reload_doc();
                                frappe.confirm(
                                    `Nachfolgende Zahlungsfiles wurden noch nicht eingelesen,<br>möchten Sie <b>trotzdem fortfahren?</b><br><br>${cur_frm.doc.missing_files}`,
                                    function(){
                                        // on yes
                                        frm.set_value("ignore_missing_files", 1);
                                        frm.save().then(() => {
                                            frappe.call({
                                                method: 'create_reports',
                                                doc: frm.doc,
                                                freeze: true,
                                                freeze_message: "Bitte warten, die Reporte werden erzeugt...",
                                                callback: function(response) {
                                                    frappe.show_alert({message:'Done!', indicator:'green'});
                                                    cur_frm.reload_doc();
                                                }
                                            });
                                        });
                                    },
                                    function(){
                                        // on no
                                        frappe.show_alert({message:'Die Report Erzeugung wurde abgebrochen', indicator:'red'});
                                    }
                                )
                            } else {
                                frappe.show_alert({message:'Done!', indicator:'green'});
                                cur_frm.reload_doc();
                            }
                        }
                    });
                });
            },
            'Auswahl Report Datenbasis',
            'Report generieren'
            )
        });
    }
});
