// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('MV Mitgliedschaft', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            if (cur_frm.doc.status_c != 'Wegzug') {
                frm.add_custom_button(__("Sektionswechsel"),  function() {
                        sektionswechsel(frm);
                }, __("Mutation"));
                frm.add_custom_button(__("Kündigung"),  function() {
                        kuendigung(frm);
                }, __("Mutation"));
                frm.add_custom_button(__("Ausschluss"),  function() {
                        ausschluss(frm);
                }, __("Mutation"));
                frm.add_custom_button(__("Todesfall"),  function() {
                        todesfall(frm);
                }, __("Mutation"));
                frm.add_custom_button(__("Mitgliedschafts-Rechnung"),  function() {
                        erstelle_rechnung(frm);
                }, __("Erstelle"));
            }
            
            get_adressdaten(frm);
        }
        
        remove_sinv_plus(frm);
        remove_backlog_plus(frm);
        
        if (['Wegzug', 'Ausschluss'].includes(cur_frm.doc.status_c)) {
            setze_read_only(frm);
            frm.disable_save();
        } else {
            frm.enable_save();
        }
        
        // set strasse mandatory
        if (!cur_frm.doc.postfach) {
            cur_frm.set_df_property('strasse', 'reqd', 1);
        }
    },
    postfach: function(frm) {
        // set strasse mandatory
        if (!cur_frm.doc.postfach) {
            cur_frm.set_df_property('strasse', 'reqd', 1);
            cur_frm.set_df_property('abweichende_objektadresse', 'read_only', 0);
        } else {
            cur_frm.set_df_property('strasse', 'reqd', 0);
            cur_frm.set_value("abweichende_objektadresse", 1);
            cur_frm.set_df_property('abweichende_objektadresse', 'read_only', 1);
        }
    },
    abweichende_objektadresse: function(frm) {
        if (!cur_frm.doc.abweichende_objektadresse) {
            cur_frm.set_df_property('objekt_strasse', 'reqd', 0);
            cur_frm.set_df_property('objekt_plz', 'reqd', 0);
            cur_frm.set_df_property('objekt_ort', 'reqd', 0);
        } else {
            cur_frm.set_df_property('objekt_strasse', 'reqd', 1);
            cur_frm.set_df_property('objekt_plz', 'reqd', 1);
            cur_frm.set_df_property('objekt_ort', 'reqd', 1);
        }
    },
    abweichende_rechnungsadresse: function(frm) {
        if (!cur_frm.doc.abweichende_rechnungsadresse) {
            cur_frm.set_df_property('rg_strasse', 'reqd', 0);
            cur_frm.set_df_property('rg_plz', 'reqd', 0);
            cur_frm.set_df_property('rg_ort', 'reqd', 0);
        } else {
            cur_frm.set_df_property('rg_strasse', 'reqd', 1);
            cur_frm.set_df_property('rg_plz', 'reqd', 1);
            cur_frm.set_df_property('rg_ort', 'reqd', 1);
        }
    },
    rg_postfach: function(frm) {
        if (cur_frm.doc.rg_postfach) {
            cur_frm.set_df_property('rg_strasse', 'reqd', 0);
        } else {
            cur_frm.set_df_property('rg_strasse', 'reqd', 1);
        }
    },
    unabhaengiger_debitor: function(frm) {
        if (!cur_frm.doc.unabhaengiger_debitor) {
            cur_frm.set_df_property('rg_nachname', 'reqd', 0);
        } else {
            cur_frm.set_df_property('rg_nachname', 'reqd', 1);
        }
    },
    hat_solidarmitglied: function(frm) {
        if (!cur_frm.doc.hat_solidarmitglied) {
            cur_frm.set_df_property('nachname_2', 'reqd', 0);
        } else {
            cur_frm.set_df_property('nachname_2', 'reqd', 1);
        }
    }
});

function get_adressdaten(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft.get_uebersicht_html",
        args:{
                'name': cur_frm.doc.name
        },
        callback: function(r)
        {
            cur_frm.set_df_property('uebersicht_html','options', r.message);
        }
    });
}

function kuendigung(frm) {
    frappe.call({
        'method': "frappe.client.get",
        'args': {
            'doctype': "Sektion",
            'name': cur_frm.doc.sektion_id
        },
        'callback': function(response) {
            var sektion_settings = response.message;

            if (sektion_settings) {
                console.log();
                var kuendigungs_stichtag = frappe.datetime.str_to_obj(sektion_settings.kuendigungs_stichtag);
                var ks_month = kuendigungs_stichtag.getMonth();
                var ks_day = kuendigungs_stichtag.getDate();
                
                var now = frappe.datetime.str_to_obj(frappe.datetime.now_date());
                var now_month = now.getMonth();
                var now_day = now.getDate();
                
                var fristgerecht = true;
                
                if (now_month > ks_month) {
                    fristgerecht = false;
                } else {
                    if (now_month == ks_month) {
                        if (now_day == ks_day) {
                            fristgerecht = false;
                        }
                    }
                }
                
                if (fristgerecht) {
                    var field_list = [
                        {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Kündigung erfolgt per', 'reqd': 1, 'default': frappe.datetime.year_end()},
                        {'fieldname': 'massenlauf', 'fieldtype': 'Check', 'label': 'Für Massenlauf vormerken', 'default': 1}
                    ];
                } else {
                    var field_list = [
                        {'fieldname': 'html_info', 'fieldtype': 'HTML', 'options': '<p style="color: red;">Achtung: Kündigungsfrist verpasst!</p>'},
                        {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Kündigung erfolgt per', 'reqd': 1, 'default': frappe.datetime.add_months(frappe.datetime.year_end(), 12), 'read_only': 1},
                        {'fieldname': 'kulanz', 'fieldtype': 'Check', 'label': 'Kulanz anwenden', 'default': 0, 'change': function() {
                                if (cur_dialog.fields_dict.kulanz.get_value() == 1) {
                                    cur_dialog.fields_dict.datum.df.read_only = 0;
                                    cur_dialog.fields_dict.datum.refresh();
                                } else {
                                    cur_dialog.fields_dict.datum.set_value(frappe.datetime.add_months(frappe.datetime.year_end(), 12));
                                    cur_dialog.fields_dict.datum.df.read_only = 1;
                                    cur_dialog.fields_dict.datum.refresh();
                                }
                            }
                        },
                        {'fieldname': 'massenlauf', 'fieldtype': 'Check', 'label': 'Für Massenlauf vormerken', 'default': 1}
                    ];
                }
                
                frappe.prompt(field_list,
                function(values){
                    frappe.call({
                        method: "mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft.make_kuendigungs_prozess",
                        args:{
                                'mitgliedschaft': cur_frm.doc.name,
                                'datum_kuendigung': values.datum,
                                'massenlauf': values.massenlauf
                        },
                        freeze: true,
                        freeze_message: 'Erstelle Kündigung inkl. Bestätigung...',
                        callback: function(r)
                        {
                            cur_frm.reload_doc();
                            frappe.msgprint("Die Kündigung wurde per " + frappe.datetime.obj_to_user(values.datum) + " erfasst.<br>Die Kündigungsbestätigung finden Sie in den Anhängen.");
                        }
                    });
                    
                },
                'Kündigung',
                'Erfassen'
                )
            }
        }
    });
    
    
}

function todesfall(frm) {
    frappe.prompt([
        {'fieldname': 'verstorben_am', 'fieldtype': 'Date', 'label': 'Verstorben am', 'reqd': 0, 'default': frappe.datetime.get_today()},
        {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Todesfall bedingte Kündigung erfolgt per', 'reqd': 1, 'default': frappe.datetime.year_end()},
        {'fieldname': 'todesfall_uebernahme', 'fieldtype': 'Data', 'label': 'Übernahem durch'}
    ],
    function(values){
        cur_frm.set_value("kuendigung", values.datum);
        cur_frm.set_value("verstorben_am", values.verstorben_am);
        cur_frm.set_value("status_c", 'Gestorben');
        if (values.todesfall_uebernahme) {
            cur_frm.set_value("todesfall_uebernahme", values.todesfall_uebernahme);
        }
        cur_frm.save();
        frappe.msgprint("Der Todesfall sowie die damit verbundene Kündigung wurde per " + frappe.datetime.obj_to_user(values.datum) + " erfasst.");
    },
    'Todesfall',
    'Erfassen'
    )
}

function ausschluss(frm) {
    frappe.prompt([
        {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Ausschluss per', 'reqd': 1, 'default': frappe.datetime.get_today()},
        {'fieldname': 'grund', 'fieldtype': 'Text', 'label': 'Ausschluss Begründung'}
    ],
    function(values){
        cur_frm.set_value("austritt", values.datum);
        cur_frm.set_value("status_c", 'Ausschluss');
        if (values.grund) {
            var alte_infos = cur_frm.doc.wichtig;
            var neue_infos = "Ausschluss:\n" + values.grund + "\n\n";
            neue_infos = neue_infos + alte_infos;
            cur_frm.set_value("wichtig", neue_infos);
        }
        cur_frm.set_value("adressen_gesperrt", 1);
        cur_frm.save();
        frappe.msgprint("Der Ausschluss wurde per " + frappe.datetime.obj_to_user(values.datum) + " erfasst.");
    },
    'Ausschluss',
    'Erfassen'
    )
}

function sektionswechsel(frm) {
    frappe.prompt([
        {'fieldname': 'sektion_neu', 'fieldtype': 'Link', 'label': 'Neue Sektion', 'reqd': 1, 'options': 'Sektion'}  
    ],
    function(values){
        frappe.call({
            method: "mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft.sektionswechsel",
            args:{
                    'mitgliedschaft': cur_frm.doc.name,
                    'neue_sektion': values.sektion_neu,
                    'zuzug_per': frappe.datetime.get_today()
            },
            callback: function(r)
            {
                if (r.message == 1) {
                    cur_frm.set_value("wegzug", frappe.datetime.get_today());
                    cur_frm.set_value("wegzug_zu", values.sektion_neu);
                    cur_frm.set_value("status_c", 'Wegzug');
                    cur_frm.save();
                    frappe.msgprint("Der Wechsel zur Sektion " + values.sektion_neu + " erfolgt.");
                } else {
                    frappe.msgprint("oops, da ist etwas schiefgelaufen!");
                }
            }
        });
    },
    'Sektionswechsel',
    'Übertragen'
    )
}

function erstelle_rechnung(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft.create_mitgliedschaftsrechnung",
        args:{
                'mitgliedschaft': cur_frm.doc.name
        },
        callback: function(r)
        {
            cur_frm.reload_doc();
        }
    });
}

function remove_sinv_plus(frm) {
    $(":button[data-doctype='Sales Invoice']").remove();
}
function remove_backlog_plus(frm) {
    $(":button[data-doctype='Arbeits Backlog']").remove();
}

function setze_read_only(frm) {
    var i = 0;
    for (i; i<cur_frm.fields.length; i++) {
        cur_frm.set_df_property(cur_frm.fields[i].df.fieldname,'read_only', 1);
    }
}
