// Copyright (c) 2021, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Entry', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            if (cur_frm.doc.unallocated_amount > 0) {
                if (!cur_frm.doc.korrespondenz) {
                    frm.add_custom_button(__("Mitgliedschafts-Korrespondenz erstellen"), function() {
                        erstelle_korrespondenz(frm);
                    });
                }
                if ((cur_frm.doc.paid_amount / cur_frm.doc.unallocated_amount) == 2) {
                    frm.add_custom_button(__("Mit Folgejahr-Mitgliedschaft ausgleichen"), function() {
                        mit_folgejahr_ausgleichen(frm);
                    });
                }
                frm.add_custom_button(__("Mit Spende ausgleichen"), function() {
                    mit_spende_ausgleichen(frm);
                });
                frm.add_custom_button(__("Mit Rückzahlung ausgleichen"), function() {
                    rueckzahlung(frm);
                });
            }
        }
    }
});


function erstelle_korrespondenz(frm) {
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
                                method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.create_korrespondenz",
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
}

function mit_spende_ausgleichen(frm) {
    frappe.confirm(
        'Wollen Sie die Zahlung mit einer Spende ausgleichen?',
        function(){
            // on yes
            frappe.call({
                method: "mvd.mvd.doctype.camt_import.camt_import.mit_spende_ausgleichen",
                args:{
                    'pe': cur_frm.doc.name
                },
                freeze: true,
                freeze_message: 'Gleiche Zahlung mit Spende aus...',
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
}

function mit_folgejahr_ausgleichen(frm) {
    frappe.confirm(
        'Wollen Sie die Zahlung mit einer Folgejahr-Mitgliedschaft ausgleichen?',
        function(){
            // on yes
            frappe.call({
                method: "mvd.mvd.doctype.camt_import.camt_import.mit_folgejahr_ausgleichen",
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
}

function rueckzahlung(frm) {
    frappe.confirm(
        'Wollen Sie die Zahlung mit einer Rückzahlung ausgleichen?',
        function(){
            // on yes
            frappe.call({
                method: "mvd.mvd.doctype.camt_import.camt_import.rueckzahlung",
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
}
