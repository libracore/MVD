// Copyright (c) 2021, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Entry', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            if (cur_frm.doc.mv_mitgliedschaft) {
                if (!cur_frm.doc.korrespondenz) {
                    frm.add_custom_button(__("Mitgliedschafts-Korrespondenz erstellen"), function() {
                        erstelle_korrespondenz(frm);
                    });
                }
                if (cur_frm.doc.unallocated_amount > 0) {
                    frm.add_custom_button(__("Mitgliedschaft"), function() {
                        mit_folgejahr_ausgleichen(frm);
                    }, __("Verbuchen als ..."));
                    
                    if (cur_frm.doc.unallocated_amount >= 10) {
                        frm.add_custom_button(__("HV Zahlung"), function() {
                            als_hv_verbuchen(frm);
                        }, __("Verbuchen als ..."));
                    }
                    
                    frm.add_custom_button(__("Spende"), function() {
                        mit_spende_ausgleichen(frm);
                    }, __("Verbuchen als ..."));
                    
                    frm.add_custom_button(__("Rückzahlung"), function() {
                        rueckzahlung(frm);
                    }, __("Ausgleichen mit ..."));
                    
                }
                if (check_underpaid(frm)) {
                    frm.add_custom_button(__("Differenz als Kulanz ausgleichen"), function() {
                        kulanz_ausgleich(frm);
                    });
                }
            }
            if (cur_frm.doc.docstatus == 0) {
                frm.add_custom_button(__("Mitgliedschaft"), function() {
                    mitgliedschaft_zuweisen(frm);
                }, __("Zuweisung von ..."));
                frm.add_custom_button(__("Faktura Kunde"), function() {
                    faktura_kunde_zuweisen(frm);
                }, __("Zuweisung von ..."));
            }
            
            if ((cur_frm.doc.docstatus == 2)&&(frappe.user.has_role("System Manager"))) {
                frm.add_custom_button(__("Storno Rollback"), function() {
                    storno_rollback(frm);
                });
            }
        }
    }
});

function storno_rollback(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.camt_import.utils.reopen_payment_as_admin",
        args:{
                'pe': cur_frm.doc.name
        },
        callback: function(r)
        {
            cur_frm.reload_doc();
        }
    });
}

function mitgliedschaft_zuweisen(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.camt_import.utils.suche_mitgliedschaft_aus_pe",
        args:{
                'payment_entry': cur_frm.doc.name
        },
        freeze: true,
        freeze_message: 'Suche nach möglichen Mitgliedschaften...',
        callback: function(r)
        {
            var field_list = [
                {'fieldname': 'mitgliedschaft', 'fieldtype': 'Link', 'label': 'Mitgliedschaft', 'reqd': 1, 'options': 'Mitgliedschaft'},
                {'fieldname': 'section_vorschlaege', 'fieldtype': 'Section Break', 'label': 'Vorschläge'}
            ];
            r.message.forEach(function(entry) {
                field_list.push({
                    'fieldname': 'html_' + entry.mitgliedschaft,
                    'fieldtype': 'HTML',
                    'options': '<p>' + entry.vorname + " " + entry.nachname + " / " + entry.mitgliedschaft + " (" + entry.sektion + ": " + entry.status + "), Quelle: " + entry.quelle
                })
            });
            
            frappe.prompt(field_list,
            function(values){
                frappe.call({
                    method: "mvd.mvd.doctype.camt_import.utils.mitgliedschaft_zuweisen",
                    args:{
                            'mitgliedschaft': values.mitgliedschaft,
                            'pe_sektion': cur_frm.doc.sektion_id
                    },
                    freeze: true,
                    freeze_message: 'Weise Mitgliedschaft zu...',
                    callback: function(r)
                    {
                        cur_frm.set_value("mv_mitgliedschaft", r.message.mitgliedschaft);
                        cur_frm.set_value("party", r.message.customer);
                        cur_frm.set_value("camt_status", 'Zugewiesen');
                        cur_frm.set_value("mv_kunde", '');
                        cur_frm.save();
                    }
                });
            },
            'Mitgliedschaft zuweisen',
            'Zuweisen'
            )
        }
    });
}

function faktura_kunde_zuweisen(frm) {
    var field_list = [
        {'fieldname': 'faktura_kunde', 'fieldtype': 'Link', 'label': 'Faktura Kunde', 'reqd': 1, 'options': 'Kunden'}
    ];
    
    frappe.prompt(field_list,
    function(values){
        frappe.call({
            method: "mvd.mvd.doctype.camt_import.utils.mitgliedschaft_zuweisen",
            args:{
                    'mitgliedschaft': values.faktura_kunde,
                    'faktura': 1
            },
            freeze: true,
            freeze_message: 'Weise Faktura Kunde zu...',
            callback: function(r)
            {
                cur_frm.set_value("mv_mitgliedschaft", r.message.mitgliedschaft);
                cur_frm.set_value("party", r.message.customer);
                cur_frm.set_value("camt_status", 'Zugewiesen');
                cur_frm.set_value("mv_kunde", r.message.faktura);
                
                cur_frm.save();
            }
        });
    },
    'Faktura Kunde zuweisen',
    'Zuweisen'
    )
}

function erstelle_korrespondenz(frm) {
    if (frappe.user.has_role("MV_RW")) {
        frappe.call({
            method: 'frappe.client.get',
            args: {
                'doctype': 'Mitgliedschaft',
                'name': cur_frm.doc.mv_mitgliedschaft
            },
            async: false,
            callback: function(response) {
                if (response.message) {
                    var mitgliedschaft = response.message;
                    frappe.call({
                        method: "mvd.mvd.doctype.druckvorlage.druckvorlage.get_druckvorlagen",
                        args:{
                                'sektion': mitgliedschaft.sektion_id,
                                'dokument': 'Korrespondenz',
                                'mitgliedtyp': mitgliedschaft.mitgliedtyp_c,
                                'reduzierte_mitgliedschaft': mitgliedschaft.reduzierte_mitgliedschaft,
                                'language': mitgliedschaft.language
                        },
                        async: false,
                        callback: function(res)
                        {
                            var druckvorlagen = res.message;
                            // Default Druckvorlage für den Moment deaktiviert!
                            //~ frappe.prompt([
                                //~ {'fieldname': 'titel', 'fieldtype': 'Data', 'label': 'Titel', 'reqd': 1},
                                //~ {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 0, 'options': 'Druckvorlage', 'default': druckvorlagen.default_druckvorlage, 
                                    //~ 'get_query': function() {
                                        //~ return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                                    //~ }
                                //~ }
                            //~ ],
                            frappe.prompt([
                                {'fieldname': 'titel', 'fieldtype': 'Data', 'label': 'Titel', 'reqd': 1},
                                {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 0, 'options': 'Druckvorlage',
                                    'get_query': function() {
                                        return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                                    }
                                }
                            ],
                            function(values){
                                if (values.druckvorlage) {
                                    var druckvorlage = values.druckvorlage;
                                } else {
                                    var druckvorlage = 'keine'
                                }
                                frappe.call({
                                    method: "mvd.mvd.doctype.mitgliedschaft.utils.create_korrespondenz",
                                    args:{
                                            'mitgliedschaft': mitgliedschaft.name,
                                            'druckvorlage': druckvorlage,
                                            'titel': values.titel
                                    },
                                    freeze: true,
                                    freeze_message: 'Erstelle Korrespondenz...',
                                    callback: function(r)
                                    {
                                        cur_frm.set_value("korrespondenz", r.message);
                                        cur_frm.save();
                                        frappe.set_route("Form", "Korrespondenz", r.message);
                                    }
                                });
                            },
                            'Korrespondenz Erstellung',
                            'Erstellen'
                            )
                        }
                    });
                }
            }
        });
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function als_hv_verbuchen(frm) {
    if (frappe.user.has_role("MV_RW")) {
        frappe.confirm(
            'Wollen Sie die Zahlung als HV-Zahlung verbuchen?',
            function(){
                // on yes
                frappe.call({
                    method: "mvd.mvd.doctype.camt_import.utils.als_hv_verbuchen",
                    args:{
                        'pe': cur_frm.doc.name
                    },
                    freeze: true,
                    freeze_message: 'Verbuche als HV-Zahlung...',
                    callback: function(r)
                    {
                        cur_frm.reload_doc();
                    }
                });
            },
            function(){
                // on no
            }
        )
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function mit_spende_ausgleichen(frm) {
    if (frappe.user.has_role("MV_RW")) {
        frappe.prompt([
            {'fieldname': 'spendenlauf_referenz', 'fieldtype': 'Link', 'label': 'Zuweisung zu Spendenversand', 'reqd': 0, 'options': 'Spendenversand', 'description': 'Sie können hier optional eine Referenz auf einen Spendenversand vornehmen'}
        ],
        function(values){
            if (values.spendenlauf_referenz) {
                var spendenlauf_referenz = values.spendenlauf_referenz;
            } else {
                var spendenlauf_referenz = null
            }
            frappe.call({
                method: "mvd.mvd.doctype.camt_import.utils.mit_spende_ausgleichen",
                args:{
                    'pe': cur_frm.doc.name,
                    'spendenlauf_referenz': spendenlauf_referenz
                },
                freeze: true,
                freeze_message: 'Gleiche Zahlung mit Spende aus...',
                callback: function(r)
                {
                    cur_frm.reload_doc();
                }
            });
        },
        'Wollen Sie die Zahlung mit einer Spende ausgleichen?',
        'Mit Spende ausgleichen'
        )
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function mit_folgejahr_ausgleichen(frm) {
    if (frappe.user.has_role("MV_RW")) {
        frappe.confirm(
            'Wollen Sie die Zahlung mit einer Folgejahr-Mitgliedschaft ausgleichen?',
            function(){
                // on yes
                frappe.call({
                    method: "mvd.mvd.doctype.camt_import.utils.mit_folgejahr_ausgleichen",
                    args:{
                        'pe': cur_frm.doc.name
                    },
                    freeze: true,
                    freeze_message: 'Gleiche Zahlung mit Folgejahr-Mitgliedschaft aus...',
                    callback: function(r)
                    {
                        cur_frm.reload_doc();
                    }
                });
            },
            function(){
                // on no
            }
        )
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function rueckzahlung(frm) {
    if (frappe.user.has_role("MV_RW")) {
        frappe.confirm(
            'Wollen Sie die Zahlung mit einer Rückzahlung ausgleichen?',
            function(){
                // on yes
                frappe.call({
                    method: "mvd.mvd.doctype.camt_import.utils.rueckzahlung",
                    args:{
                        'pe': cur_frm.doc.name
                    },
                    freeze: true,
                    freeze_message: 'Gleiche Zahlung mittels Rückzahlung aus...',
                    callback: function(r)
                    {
                        cur_frm.reload_doc();
                    }
                });
            },
            function(){
                // on no
            }
        )
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function kulanz_ausgleich(frm) {
    if (frappe.user.has_role("MV_RW")) {
        frappe.confirm(
            'Wollen Sie die Zahlung aus Kulanz ausgleichen?',
            function(){
                // on yes
                frappe.call({
                    method: "mvd.mvd.doctype.camt_import.utils.kulanz_ausgleich",
                    args:{
                        'pe': cur_frm.doc.name
                    },
                    freeze: true,
                    freeze_message: 'Gleiche Zahlung mittels Kulanz aus...',
                    callback: function(r)
                    {
                        cur_frm.reload_doc();
                    }
                });
            },
            function(){
                // on no
            }
        )
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function check_underpaid(frm) {
    var underpaid = false;
    cur_frm.doc.references.forEach(function(entry) {
       if (entry.allocated_amount < entry.outstanding_amount) {
           underpaid = true;
       }
    });
    return underpaid
}
