// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Druckvorlage', {
    refresh: function(frm) {
        if (cur_frm.doc.dokument == 'Geschenkmitgliedschaft') {
            cur_frm.set_df_property('seite_1_ausweis','read_only',1);
            cur_frm.set_df_property('doppelseitiger_druck','read_only',1);
            if (cur_frm.doc.geschenkmitgliedschaft_dok_empfaenger == 'Schenkende*r') {
                cur_frm.set_df_property('seite_1_referenzblock_ausblenden','read_only',0);
            }
        }
        
        // Add BTN Testen
        frm.add_custom_button(__("Druckvorlage Test-Druck"),  function() {
            if (!cur_frm.is_dirty()) {
                frappe.prompt([
                    {'fieldname': 'test_dt', 'fieldtype': 'Link', 'label': 'Doctype', 'reqd': 1, 'options': 'DocType',
                        'get_query': function() { return { filters: {'name': ['in', ['Mahnung', 'Sales Invoice', 'Fakultative Rechnung', 'Korrespondenz']] } } }
                    },
                    {'fieldname': 'test_dn', 'fieldtype': 'Dynamic Link', 'label': 'Datensatz', 'reqd': 1, 'options': 'test_dt'}
                ],
                function(values){
                    frm.call("test_druck", {
                        test_dt: values.test_dt,
                        test_dn: values.test_dn
                    }, (r) => {
                        frm.reload_doc();
                        var url = '/api/method/frappe.utils.print_format.download_pdf?doctype=Druckvorlage&name=' + cur_frm.doc.name + '&format=Testdruck&no_letterhead=0&_lang=de';
                        window.open(url, '_blank').focus();
                    });
                    
                },
                'Testdruck erstellen',
                'Drucken'
                )
            } else {
                frappe.msgprint("Bitte zuerst speichern.");
            }
        });
    },
    dokument: function(frm) {
        if (cur_frm.doc.dokument == 'Mahnung') {
            cur_frm.set_value('anzahl_seiten', '1');
            cur_frm.set_value('qrr_ez_folgeseite_mahnung', null);
        }
        if (cur_frm.doc.dokument == 'Geschenkmitgliedschaft') {
            cur_frm.set_value('anzahl_seiten', '1');
            cur_frm.set_value('geschenkmitgliedschaft_dok_empfaenger', 'Beschenkte*r');
            cur_frm.set_value('seite_1_ausweis', 1);
            cur_frm.set_df_property('seite_1_ausweis','read_only',1);
            cur_frm.set_value('doppelseitiger_druck', 0);
            cur_frm.set_df_property('doppelseitiger_druck','read_only',1);
        }
    },
    geschenkmitgliedschaft_dok_empfaenger: function(frm) {
        if (cur_frm.doc.dokument == 'Geschenkmitgliedschaft') {
            if (cur_frm.doc.geschenkmitgliedschaft_dok_empfaenger == 'Schenkende*r') {
                cur_frm.set_value('seite_1_ausweis', 0);
                cur_frm.set_value('doppelseitiger_druck', 0);
                cur_frm.set_df_property('seite_1_referenzblock_ausblenden','read_only',0);
            } else {
                cur_frm.set_value('seite_1_ausweis', 1);
                cur_frm.set_value('doppelseitiger_druck', 1);
                cur_frm.set_value('seite_1_referenzblock_ausblenden', 1);
                cur_frm.set_df_property('seite_1_referenzblock_ausblenden','read_only',1);
            }
        }
    },
    anzahl_seiten: function(frm) {
        //~ if (cur_frm.doc.dokument == 'Mahnung') {
            //~ if (cur_frm.doc.anzahl_seiten == '3') {
                //~ cur_frm.set_value('anzahl_seiten', '2');
                //~ frappe.msgprint("Die Anzahl Blätter wurde auf 2 zurückgesetzt weil es sich um eine Mahnungs Druckvorlage handelt.");
            //~ }
        //~ }
        if (cur_frm.doc.dokument == 'Geschenkmitgliedschaft') {
            if (cur_frm.doc.anzahl_seiten != '1') {
                cur_frm.set_value('anzahl_seiten', '1');
                frappe.msgprint("Die Anzahl Blätter wurde auf 1 zurückgesetzt weil es sich um eine Geschenkmitgliedschafts Druckvorlage handelt.");
            }
        }
    },
    qrr_ez_folgeseite_mahnung: function(frm) {
        if (cur_frm.doc.qrr_ez_folgeseite_mahnung) {
            cur_frm.set_value('anzahl_seiten', '2');
        } else {
            cur_frm.set_value('anzahl_seiten', '1');
        }
    }
});
