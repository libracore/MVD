// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mitgliedschaft', {
    setup: function(frm) {
        // override_default_email_dialog
        override_default_email_dialog(frm);
    },
    refresh: function(frm) {
       if (!frm.doc.__islocal) {
            if ((!['Wegzug', 'Ausschluss', 'Online-Kündigung'].includes(cur_frm.doc.status_c))&&(cur_frm.doc.validierung_notwendig == 0)) {
                if ((!['Kündigung', 'Gestorben'].includes(cur_frm.doc.status_c))&&(cur_frm.doc.mitgliedtyp_c == 'Privat')) {
                    frm.add_custom_button(__("Sektionswechsel"),  function() {
                            if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                            } else {
                                sektionswechsel(frm);
                            }
                    }, __("Mutation"));
                }
                if (!['Kündigung', 'Gestorben'].includes(cur_frm.doc.status_c)) {
                    frm.add_custom_button(__("Kündigung"),  function() {
                            if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                            } else {
                                kuendigung(frm);
                            }
                    }, __("Mutation"));
                }
                frm.add_custom_button(__("Ausschluss"),  function() {
                        if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                            frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                        } else {
                            ausschluss(frm);
                        }
                }, __("Mutation"));
                if (!['Gestorben'].includes(cur_frm.doc.status_c)) {
                    frm.add_custom_button(__("Todesfall"),  function() {
                            if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                            } else {
                                todesfall(frm);
                            }
                    }, __("Mutation"));
                }
                if (!['Gestorben', 'Kündigung'].includes(cur_frm.doc.status_c)) {
                    frm.add_custom_button(__("Mitgliedschafts-Rechnung"),  function() {
                            if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                            } else {
                                erstelle_rechnung(frm);
                            }
                    }, __("Erstelle"));
                    frm.add_custom_button(__("Spenden-Rechnung"),  function() {
                            if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                            } else {
                                erstelle_spenden_rechnung(frm);
                            }
                    }, __("Erstelle"));
                    frm.add_custom_button(__("HV-Rechnung"),  function() {
                            if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                            } else {
                                erstelle_hv_rechnung(frm);
                            }
                    }, __("Erstelle"));
                    frm.add_custom_button(__("Korrespondenz"),  function() {
                            if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                            } else {
                                erstelle_korrespondenz(frm);
                            }
                    }, __("Erstelle"));
                }
            }
            frm.add_custom_button(__("Zahlungen"),  function() {
                frappe.route_options = {"party": cur_frm.doc.rg_kunde ? cur_frm.doc.rg_kunde:cur_frm.doc.kunde_mitglied}
                frappe.set_route("List", "Payment Entry", "List");
            });
            if (cur_frm.doc.validierung_notwendig) {
                if (cur_frm.doc.status_c == 'Online-Kündigung') {
                    frm.add_custom_button(__("Online-Kündigung verarbeiten"),  function() {
                            if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                            } else {
                                kuendigung(frm);
                            }
                    });
                } else {
                    frm.add_custom_button(__("Daten als validert bestätigen"),  function() {
                            if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                            } else {
                                daten_validiert(frm);
                            }
                    });
                }
            }
            if (cur_frm.doc.kuendigung_verarbeiten) {
                frm.add_custom_button(__("Von Massenlauf (Kündigung) entfernen"),  function() {
                        if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                            frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                        } else {
                            kuendigung_verarbeitet(frm);
                        }
                });
            }
            if (cur_frm.doc.interessent_innenbrief_mit_ez) {
                frm.add_custom_button(__("Interessent*Innenbrief mit EZ als erstellt bestätigen"),  function() {
                        if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                            frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                        } else {
                            interessent_innenbrief_mit_ez_verarbeitet(frm);
                        }
                });
            }
            if (cur_frm.doc.anmeldung_mit_ez) {
                frm.add_custom_button(__("Anmeldung mit EZ als erstellt bestätigen"),  function() {
                        if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                            frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                        } else {
                            anmeldung_mit_ez_verarbeitet(frm);
                        }
                });
            }
            if (cur_frm.doc.rg_massendruck_vormerkung) {
                frm.add_custom_button(__("Von Massenlauf (Mitgliedschaftsrechnung) entfernen"),  function() {
                        if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                            frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                        } else {
                            rg_massendruck_verarbeitet(frm);
                        }
                });
            }
            if (cur_frm.doc.begruessung_massendruck) {
                frm.add_custom_button(__("Von Massenlauf (Begrüssung Online-Beitritt) entfernen"),  function() {
                        if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                            frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                        } else {
                            begruessung_massendruck_verarbeitet(frm);
                        }
                });
            }
            
            frm.add_custom_button(__("Erstelle ToDo"),  function() {
                if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                    frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
                } else {
                    erstelle_todo(frm);
                }
            });
            
            // load html overview
            load_html_overview(frm);
            
            // assign hack
            $(".add-assignment.text-muted").remove();
        }
        
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
        // set nachname oder firma mandatory
        if (cur_frm.doc.kundentyp == 'Unternehmen') {
            cur_frm.set_df_property('nachname_1', 'reqd', 0);
            cur_frm.set_df_property('firma', 'reqd', 1);
        } else {
            cur_frm.set_df_property('nachname_1', 'reqd', 1);
            cur_frm.set_df_property('firma', 'reqd', 0);
        }
    },
    m_und_w: function(frm) {
        if (![0, 1].includes(cur_frm.doc.m_und_w)) {
            if (!frappe.user.has_role("System Manager")) {
                cur_frm.set_value("m_und_w", 1);
                frappe.msgprint("Sie dürfen als Anzahl nur '0' oder '1' auswählen");
            }
        }
    },
    postfach: function(frm) {
        if (!cur_frm.doc.postfach) {
            // kein Postfach -> Strasse pflicht
            cur_frm.set_df_property('strasse', 'reqd', 1);
            
            // kein Postfach -> abweichende_objektadresse bearbeitbar
            cur_frm.set_df_property('abweichende_objektadresse', 'read_only', 0);
            
            if (cur_frm.doc.abweichende_objektadresse) {
                var objekt_strassen_bez = cur_frm.doc.objekt_strasse + cur_frm.doc.objekt_hausnummer + cur_frm.doc.objekt_nummer_zu + cur_frm.doc.objekt_plz + cur_frm.doc.objekt_ort;
                var korrespondenz_strasse_bez = cur_frm.doc.strasse + cur_frm.doc.nummer + cur_frm.doc.nummer_zu + cur_frm.doc.plz + cur_frm.doc.ort;
                if (objekt_strassen_bez == korrespondenz_strasse_bez) {
                    // adressdetails korrespondenz == objekt -> objekt entfernen
                    cur_frm.set_value("abweichende_objektadresse", 0);
                    cur_frm.set_value("objekt_strasse", '');
                    cur_frm.set_value("objekt_hausnummer", '');
                    cur_frm.set_value("objekt_nummer_zu", '');
                    cur_frm.set_value("objekt_plz", '');
                    cur_frm.set_value("objekt_ort", '');
                }
            }
            
        } else {
            // mit postfach -> strasse nicht zwingend
            cur_frm.set_df_property('strasse', 'reqd', 0);
            
            // mit postfach -> objekt zwingend
            cur_frm.set_value("abweichende_objektadresse", 1);
            cur_frm.set_df_property('abweichende_objektadresse', 'read_only', 1);
            
            // übertrage korrespondenz werte zu objekt wenn objekt strasse noch leer
            if (!cur_frm.doc.objekt_strasse) {
                cur_frm.set_value("objekt_strasse", cur_frm.doc.strasse);
                cur_frm.set_value("objekt_hausnummer", cur_frm.doc.nummer);
                cur_frm.set_value("objekt_nummer_zu", cur_frm.doc.nummer_zu);
                cur_frm.set_value("objekt_plz", cur_frm.doc.plz);
                cur_frm.set_value("objekt_ort", cur_frm.doc.ort);
            }
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
    },
    kundentyp: function(frm) {
        if (cur_frm.doc.kundentyp == 'Unternehmen') {
            cur_frm.set_df_property('nachname_1', 'reqd', 0);
            cur_frm.set_df_property('firma', 'reqd', 1);
        } else {
            cur_frm.set_df_property('nachname_1', 'reqd', 1);
            cur_frm.set_df_property('firma', 'reqd', 0);
        }
    },
    validate: function(frm) {
        if (cur_frm.doc.kundentyp == 'Unternehmen') {
            if (cur_frm.doc.mitgliedtyp_c != 'Geschäft') {
                frappe.msgprint( "Unternehmen können nur Mitgliedschaften vom Typ Geschäft besitzen!", __("Validation") );
                frappe.validated=false;
            }
        }
        //cur_frm.set_value("sp_no_update", 0);
        cur_frm.set_value("letzte_bearbeitung_von", 'User');
    },
    plz: function(frm) {
        pincode_lookup(cur_frm.doc.plz, 'ort');
    },
    objekt_plz: function(frm) {
        pincode_lookup(cur_frm.doc.objekt_plz, 'objekt_ort');
    },
    rg_plz: function(frm) {
        pincode_lookup(cur_frm.doc.rg_plz, 'rg_ort');
    }
});

function load_html_overview(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_uebersicht_html",
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
        method: "mvd.mvd.doctype.druckvorlage.druckvorlage.get_druckvorlagen",
        args:{
                'sektion': cur_frm.doc.sektion_id,
                'dokument': 'Kündigung',
                'mitgliedtyp': cur_frm.doc.mitgliedtyp_c,
                'reduzierte_mitgliedschaft': cur_frm.doc.reduzierte_mitgliedschaft,
                'language': cur_frm.doc.language
        },
        async: false,
        callback: function(res)
        {
            var druckvorlagen = res.message;
            frappe.call({
                'method': "frappe.client.get",
                'args': {
                    'doctype': "Sektion",
                    'name': cur_frm.doc.sektion_id
                },
                'callback': function(response) {
                    var sektion_settings = response.message;

                    if (sektion_settings) {
                        var kuendigungs_stichtag = frappe.datetime.str_to_obj(sektion_settings.kuendigungs_stichtag);
                        var ks_month = kuendigungs_stichtag.getMonth();
                        var ks_day = kuendigungs_stichtag.getDate();
                        
                        if (cur_frm.doc.kuendigung) {
                            var now = frappe.datetime.str_to_obj(cur_frm.doc.kuendigung);
                        } else {
                            var now = frappe.datetime.str_to_obj(frappe.datetime.now_date());
                        }
                        
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
                            // Default Druckvorlage für den Moment deaktiviert!
                            //~ var field_list = [
                                //~ {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Kündigung erfolgt per', 'reqd': 1, 'default': cur_frm.doc.kuendigung ? cur_frm.doc.kuendigung:frappe.datetime.year_end()},
                                //~ {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage', 'default': druckvorlagen.default_druckvorlage, 
                                    //~ 'get_query': function() {
                                        //~ return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                                    //~ }
                                //~ },
                                //~ {'fieldname': 'massenlauf', 'fieldtype': 'Check', 'label': 'Für Massenlauf vormerken', 'default': 1}
                            //~ ];
                            var field_list = [
                                {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Kündigung erfolgt per', 'reqd': 1, 'default': cur_frm.doc.kuendigung ? cur_frm.doc.kuendigung:frappe.datetime.year_end()},
                                {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage',
                                    'get_query': function() {
                                        return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                                    }
                                },
                                {'fieldname': 'massenlauf', 'fieldtype': 'Check', 'label': 'Für Massenlauf vormerken', 'default': 1}
                            ];
                        } else {
                            // Default Druckvorlage für den Moment deaktiviert!
                            //~ var field_list = [
                                //~ {'fieldname': 'html_info', 'fieldtype': 'HTML', 'options': '<p style="color: red;">Achtung: Kündigungsfrist verpasst!</p>'},
                                //~ {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Kündigung erfolgt per', 'reqd': 1, 'default': frappe.datetime.add_months(frappe.datetime.year_end(), 12), 'read_only': 1},
                                //~ {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage', 'default': druckvorlagen.default_druckvorlage, 
                                    //~ 'get_query': function() {
                                        //~ return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                                    //~ }
                                //~ },
                                //~ {'fieldname': 'kulanz', 'fieldtype': 'Check', 'label': 'Kulanz anwenden', 'default': 0, 'change': function() {
                                        //~ if (cur_dialog.fields_dict.kulanz.get_value() == 1) {
                                            //~ cur_dialog.fields_dict.datum.df.read_only = 0;
                                            //~ cur_dialog.fields_dict.datum.refresh();
                                        //~ } else {
                                            //~ cur_dialog.fields_dict.datum.set_value(frappe.datetime.add_months(frappe.datetime.year_end(), 12));
                                            //~ cur_dialog.fields_dict.datum.df.read_only = 1;
                                            //~ cur_dialog.fields_dict.datum.refresh();
                                        //~ }
                                    //~ }
                                //~ },
                                //~ {'fieldname': 'massenlauf', 'fieldtype': 'Check', 'label': 'Für Massenlauf vormerken', 'default': 1}
                            //~ ];
                            var field_list = [
                                {'fieldname': 'html_info', 'fieldtype': 'HTML', 'options': '<p style="color: red;">Achtung: Kündigungsfrist verpasst!</p>'},
                                {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Kündigung erfolgt per', 'reqd': 1, 'default': frappe.datetime.add_months(frappe.datetime.year_end(), 12), 'read_only': 1},
                                {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage',
                                    'get_query': function() {
                                        return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                                    }
                                },
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
                                method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.make_kuendigungs_prozess",
                                args:{
                                        'mitgliedschaft': cur_frm.doc.name,
                                        'datum_kuendigung': values.datum,
                                        'massenlauf': values.massenlauf,
                                        'druckvorlage': values.druckvorlage
                                },
                                freeze: true,
                                freeze_message: 'Erstelle Kündigung inkl. Bestätigung...',
                                callback: function(r)
                                {
                                    cur_frm.reload_doc();
                                    cur_frm.timeline.insert_comment("Kündigung erfasst.");
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
    });
}

function todesfall(frm) {
    frappe.prompt([
        {'fieldname': 'verstorben_am', 'fieldtype': 'Date', 'label': 'Verstorben am', 'reqd': 0, 'default': frappe.datetime.get_today()},
        {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Todesfall bedingte Kündigung erfolgt per', 'reqd': 1, 'default': frappe.datetime.year_end()},
        {'fieldname': 'todesfall_uebernahme', 'fieldtype': 'Data', 'label': 'Übernommen durch'}
    ],
    function(values){
        cur_frm.set_value("kuendigung", values.datum);
        cur_frm.set_value("verstorben_am", values.verstorben_am);
        cur_frm.set_value("status_c", 'Gestorben');
        if (values.todesfall_uebernahme) {
            cur_frm.set_value("todesfall_uebernahme", values.todesfall_uebernahme);
        }
        cur_frm.save();
        cur_frm.timeline.insert_comment("Todesfall erfasst.");
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
        cur_frm.timeline.insert_comment("Ausschluss vollzogen.");
        frappe.msgprint("Der Ausschluss wurde per " + frappe.datetime.obj_to_user(values.datum) + " erfasst.");
    },
    'Ausschluss',
    'Erfassen'
    )
}

function sektionswechsel(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_sektionen_zur_auswahl",
        args:{},
        callback: function(r)
        {
            var sektionen_zur_auswahl = r.message;
            frappe.prompt([
                {'fieldname': 'sektion_neu', 'fieldtype': 'Select', 'label': 'Neue Sektion', 'reqd': 1, 'options': sektionen_zur_auswahl}  
            ],
            function(values){
                frappe.call({
                    method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.sektionswechsel",
                    args:{
                            'mitgliedschaft': cur_frm.doc.name,
                            'neue_sektion': values.sektion_neu,
                            'zuzug_per': frappe.datetime.get_today()
                    },
                    freeze: true,
                    freeze_message: 'Führe Sektionswechsel durch...',
                    callback: function(r)
                    {
                        if (r.message == 1) {
                            cur_frm.set_value("wegzug", frappe.datetime.get_today());
                            cur_frm.set_value("wegzug_zu", values.sektion_neu);
                            cur_frm.set_value("status_c", 'Wegzug');
                            cur_frm.save();
                            cur_frm.timeline.insert_comment("Sektionswechsel zu " + values.sektion_neu + " vollzogen.");
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
    });
}

function daten_validiert(frm) {
    frappe.confirm(
        'Haben Sie die Daten geprüft und möchten die Validierung bestätigen?',
        function(){
            // on yes
            if (cur_frm.doc.status_c == 'Zuzug') {
                frappe.confirm(
                    'Möchten Sie den Druck des Zuzugsdokument für den Massenlauf vormerken?',
                    function(){
                        // on yes
                        cur_frm.set_value("zuzug_massendruck", '1');
                        cur_frm.set_value("validierung_notwendig", '0');
                        cur_frm.set_value("status_c", 'Regulär');
                        cur_frm.save();
                        cur_frm.timeline.insert_comment("Validierung durchgeführt.");
                        frappe.msgprint("Die Daten wurden als validert bestätigt und der Druck des Zuzugsdokument für den Massenlauf vorgemerkt.");
                    },
                    function(){
                        // on no
                        cur_frm.set_value("validierung_notwendig", '0');
                        cur_frm.set_value("status_c", 'Regulär');
                        cur_frm.save();
                        cur_frm.timeline.insert_comment("Validierung durchgeführt.");
                        frappe.msgprint("Die Daten wurden als validert bestätigt.");
                    }
                )
            } else if (cur_frm.doc.status_c == 'Online-Anmeldung') {
                cur_frm.set_value("validierung_notwendig", '0');
                cur_frm.timeline.insert_comment("Validierung durchgeführt.");
                cur_frm.save();
                erstelle_rechnung(frm);
            } else if (cur_frm.doc.status_c == 'Online-Beitritt') {
                cur_frm.set_value("status_c", 'Regulär');
                cur_frm.save();
                cur_frm.timeline.insert_comment("Validierung durchgeführt.");
                erstelle_begruessungs_korrespondenz(frm);
            } else if (cur_frm.doc.status_c == 'Online-Mutation') {
                cur_frm.set_value("status_c", cur_frm.doc.status_vor_onl_mutation);
                cur_frm.set_value("status_vor_onl_mutation", '');
                cur_frm.set_value("validierung_notwendig", '0');
                cur_frm.save();
                cur_frm.timeline.insert_comment("Validierung durchgeführt.");
            } else {
                cur_frm.set_value("validierung_notwendig", '0');
                cur_frm.set_value("status_c", 'Regulär');
                cur_frm.save();
                cur_frm.timeline.insert_comment("Validierung durchgeführt.");
                frappe.msgprint("Die Daten wurden als validert bestätigt.");
            }
        },
        function(){
            // on no
        }
    )
}

function kuendigung_verarbeitet(frm) {
    frappe.confirm(
        'Haben Sie die Kündigung manuell gedruckt und möchten Sie sie aus dem Massenlauf entfernen?',
        function(){
            // on yes
            cur_frm.set_value("kuendigung_verarbeiten", '0');
            cur_frm.save();
            cur_frm.timeline.insert_comment("Kündigung verarbeitet.");
            frappe.msgprint("Die Kündigung wurde aus dem Massenlauf entfernt.");
        },
        function(){
            // on no
        }
    )
}

function interessent_innenbrief_mit_ez_verarbeitet(frm) {
    frappe.confirm(
        'Haben Sie den Interessent*Innenbrief mit EZ erstellt und möchten diesen als verarbeitet bestätigen?',
        function(){
            // on yes
            cur_frm.set_value("interessent_innenbrief_mit_ez", '0');
            cur_frm.save();
            cur_frm.timeline.insert_comment("Interessent*Innenbrief mit EZ erstellt.");
            frappe.msgprint("Der Interessent*Innenbrief mit EZ wurde als verarbeitet bestätigt.");
        },
        function(){
            // on no
        }
    )
}

function anmeldung_mit_ez_verarbeitet(frm) {
    frappe.confirm(
        'Haben Sie die Anmeldung mit EZ erstellt und möchten diesen als verarbeitet bestätigen?',
        function(){
            // on yes
            cur_frm.set_value("anmeldung_mit_ez", '0');
            cur_frm.save();
            cur_frm.timeline.insert_comment("Anmeldung mit EZ erstellt.");
            frappe.msgprint("Die Anmeldung mit EZ wurde als verarbeitet bestätigt.");
        },
        function(){
            // on no
        }
    )
}

function rg_massendruck_verarbeitet(frm) {
    frappe.confirm(
        'Haben Sie die Mitgliedschaftsrechnung manuell gedruckt und möchten Sie sie aus dem Massenlauf entfernen?',
        function(){
            // on yes
            cur_frm.set_value("rg_massendruck_vormerkung", '0');
            cur_frm.set_value("rg_massendruck", '');
            cur_frm.save();
            frappe.msgprint("Der Druck der Mitgliedschaftsrechnung wurde aus dem Massenlauf entfernt.");
        },
        function(){
            // on no
        }
    )
}

function begruessung_massendruck_verarbeitet(frm) {
    frappe.confirm(
        'Haben Sie das Begrüssungsschreiben manuell gedruckt und möchten Sie dies aus dem Massenlauf entfernen?',
        function(){
            // on yes
            cur_frm.set_value("begruessung_massendruck", '0');
            cur_frm.set_value("begruessung_massendruck_dokument", '');
            cur_frm.save();
            frappe.msgprint("Der Druck des Begrüssungsschreibens wurde aus dem Massenlauf entfernt.");
        },
        function(){
            // on no
        }
    )
}



function erstelle_rechnung(frm) {
    var dokument = 'Anmeldung mit EZ';
    if (cur_frm.doc.status_c == 'Interessent*in') {
        dokument = 'Interessent*Innenbrief mit EZ';
    }
    frappe.call({
        method: "mvd.mvd.doctype.druckvorlage.druckvorlage.get_druckvorlagen",
        args:{
                'sektion': cur_frm.doc.sektion_id,
                'dokument': dokument,
                'mitgliedtyp': cur_frm.doc.mitgliedtyp_c,
                'reduzierte_mitgliedschaft': cur_frm.doc.reduzierte_mitgliedschaft,
                'language': cur_frm.doc.language
        },
        async: false,
        callback: function(r)
        {
            var druckvorlagen = r.message
            // Default Druckvorlage für den Moment deaktiviert!
            //~ frappe.prompt([
                //~ {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage', 'default': druckvorlagen.default_druckvorlage, 
                    //~ 'get_query': function() {
                        //~ return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                    //~ }
                //~ },
                //~ {'fieldname': 'bar_bezahlt', 'fieldtype': 'Check', 'label': 'Barzahlung', 'reqd': 0, 'default': 0, 'hidden': cur_frm.doc.status_c != 'Online-Anmeldung' ? 0:1},
                //~ {'fieldname': 'hv_bar_bezahlt', 'fieldtype': 'Check', 'label': 'HV Barzahlung', 'reqd': 0, 'default': 0, 'depends_on': 'eval:doc.bar_bezahlt==1'},
                //~ {'fieldname': 'massendruck', 'fieldtype': 'Check', 'label': 'Für Massendruck vormerken', 'reqd': 0, 'default': 0}
            //~ ],
            frappe.prompt([
                {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage',
                    'get_query': function() {
                        return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                    }
                },
                {'fieldname': 'bar_bezahlt', 'fieldtype': 'Check', 'label': 'Barzahlung', 'reqd': 0, 'default': 0, 'hidden': cur_frm.doc.status_c != 'Online-Anmeldung' ? 0:1},
                {'fieldname': 'hv_bar_bezahlt', 'fieldtype': 'Check', 'label': 'HV Barzahlung', 'reqd': 0, 'default': 0, 'depends_on': 'eval:doc.bar_bezahlt==1'},
                {'fieldname': 'massendruck', 'fieldtype': 'Check', 'label': 'Für Massendruck vormerken', 'reqd': 0, 'default': 0}
            ],
            function(values){
                if (values.bar_bezahlt == 1) {
                    var bar_bezahlt = true;
                    if (values.hv_bar_bezahlt == 1) {
                        var hv_bar_bezahlt = true;
                    } else {
                        var hv_bar_bezahlt = null;
                    }
                } else {
                    var bar_bezahlt = null;
                    var hv_bar_bezahlt = null;
                }
                if (values.massendruck == 1) {
                    var massendruck = true;
                } else {
                    var massendruck = null;
                }
                frappe.call({
                    method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.create_mitgliedschaftsrechnung",
                    args:{
                            'mitgliedschaft': cur_frm.doc.name,
                            'bezahlt': bar_bezahlt,
                            'attach_as_pdf': true,
                            'submit': true,
                            'hv_bar_bezahlt': hv_bar_bezahlt,
                            'druckvorlage': values.druckvorlage,
                            'massendruck': massendruck
                    },
                    freeze: true,
                    freeze_message: 'Erstelle Rechnung...',
                    callback: function(r)
                    {
                        cur_frm.reload_doc();
                        cur_frm.timeline.insert_comment("Mitgliedschaftsrechnung " + r.message + " erstellt.");
                        if (massendruck) {
                            frappe.msgprint("Die Rechnung wurde erstellt und für den Massenlauf vorgemerkt, Sie finden sie in den Anhängen.");
                        } else {
                            frappe.msgprint("Die Rechnung wurde erstellt, Sie finden sie in den Anhängen.");
                        }
                    }
                });
            },
            'Rechnungs Erstellung',
            'Erstellen'
            )
        }
    });
}

function setze_read_only(frm) {
    var i = 0;
    for (i; i<cur_frm.fields.length; i++) {
        cur_frm.set_df_property(cur_frm.fields[i].df.fieldname,'read_only', 1);
    }
}

function erstelle_spenden_rechnung(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.druckvorlage.druckvorlage.get_druckvorlagen",
        args:{
                'sektion': cur_frm.doc.sektion_id,
                'dokument': 'Spende mit EZ',
                'mitgliedtyp': cur_frm.doc.mitgliedtyp_c,
                'reduzierte_mitgliedschaft': cur_frm.doc.reduzierte_mitgliedschaft,
                'language': cur_frm.doc.language
        },
        async: false,
        callback: function(res)
        {
            var druckvorlagen = res.message;
            // Default Druckvorlage für den Moment deaktiviert!
            //~ frappe.prompt([
                //~ {'fieldname': 'betrag', 'fieldtype': 'Currency', 'label': 'Vorgeschlagener Betrag', 'reqd': 1, 'default': 0.0},
                //~ {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage', 'default': druckvorlagen.default_druckvorlage, 
                    //~ 'get_query': function() {
                        //~ return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                    //~ }
                //~ }
            //~ ],
            frappe.prompt([
                {'fieldname': 'betrag', 'fieldtype': 'Currency', 'label': 'Vorgeschlagener Betrag', 'reqd': 1, 'default': 0.0},
                {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage',
                    'get_query': function() {
                        return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                    }
                }
            ],
            function(values){
                frappe.call({
                    method: "mvd.mvd.doctype.fakultative_rechnung.fakultative_rechnung.create_hv_fr",
                    args:{
                            'mitgliedschaft': cur_frm.doc.name,
                            'betrag_spende': values.betrag,
                            'druckvorlage': values.druckvorlage
                    },
                    freeze: true,
                    freeze_message: 'Erstelle Spendenrechnung...',
                    callback: function(r)
                    {
                        cur_frm.timeline.insert_comment("Spendenrechnung " + r.message + " erstellt.");
                        cur_frm.reload_doc();
                        frappe.msgprint("Die Spendenrechnung wurde erstellt, Sie finden sie in den Anhängen.");
                    }
                });
            },
            'Spendenrechnungs Erstellung',
            'Erstellen'
            )
        }
    });
}

function pincode_lookup(pincode, ort) {
    var filters = [['pincode','=', pincode]];
    // find cities
    if (pincode) {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Pincode',
                filters: filters,
                fields: ['name', 'pincode', 'city', 'canton_code']
            },
            async: false,
            callback: function(response) {
                if (response.message) {
                    if (response.message.length == 1) {
                        // got exactly one city
                        var city = response.message[0].city;
                        cur_frm.set_value(ort, city);
                    } else {
                        // multiple cities found, show selection
                        var cities = "";
                        response.message.forEach(function (record) {
                            cities += (record.city + "\n");
                        });
                        cities = cities.substring(0, cities.length - 1);
                        frappe.prompt([
                                {'fieldname': 'city', 
                                 'fieldtype': 'Select', 
                                 'label': 'City', 
                                 'reqd': 1,
                                 'options': cities,
                                 'default': response.message[0].city
                                }  
                            ],
                            function(values){
                                var city = values.city;
                                cur_frm.set_value(ort, city);
                            },
                            __('City'),
                            __('Set')
                        );
                    }
                } else {
                    // got no match
                    cur_frm.set_value(ort, city);
                }
            }
        });
    }
}

function override_default_email_dialog(frm) {
    $('.menu-item-label[data-label="Email"]').parent().off('click');
            $('.menu-item-label[data-label="E-Mail"]').parent().off('click');
    document.addEventListener('click',function(event) {
        // Replace email dialog to get a more sensible draft message and recipients
        var on_email_menutext = event.target.classList.contains('menu-item-label') && ['E-Mail','Email'].includes(event.target.innerText);
        var on_email_menuitem = event.target.children.length > 0
                                                 && event.target.children[0].classList.contains('menu-item-label')
                                                 && ['E-Mail','Email'].includes(event.target.children[0].innerText);
                                                 
      if(on_email_menutext || on_email_menuitem) {
          custom_email_dialog(event);
            $('.menu-item-label[data-label="Email"]').parent().off('click');
            $('.menu-item-label[data-label="E-Mail"]').parent().off('click');
        }
     
    }, true);
    
    // Catch Ctrl+E
    document.addEventListener('keydown',function(event) {
        if (event.key == 'e' && event.ctrlKey){
            custom_email_dialog(event);
            event.stopPropagation();
            event.preventDefault();
        }
    }, true);
}

function custom_email_dialog(e) {
    var cc = '';
    var bcc = '';
    frappe.last_edited_communication = {};
    localStorage.clear(); /* Not strictly necessary, just clear localStorage to avoid "drafts" showing up */
    var comcom = new frappe.views.CommunicationComposer({
        title: "Neues E-Mail",
        doc: cur_frm.doc,
        frm: cur_frm,
        subject: 'Ihre Mitgliedschaft: ' + cur_frm.doc.mitglied_nr,
        recipients: cur_frm.doc.e_mail_1 || '',
        cc: cc,
        bcc: bcc,
        attach_document_print: true, /* This tick is changed by JS along with the attachment ticks - which can't be passed as arguments */
        message: '', /* Gets overwritten by txt (txt must be passed to avoid loading draft messages from LocalStorage) */
        real_name: '', /* Do not pass this as it triggers automatic salutation with "Dear" */
        txt: '<div>' + cur_frm.doc.briefanrede + '</div>'
    });
}

function erstelle_hv_rechnung(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.druckvorlage.druckvorlage.get_druckvorlagen",
        args:{
                'sektion': cur_frm.doc.sektion_id,
                'dokument': 'HV mit EZ',
                'mitgliedtyp': cur_frm.doc.mitgliedtyp_c,
                'reduzierte_mitgliedschaft': cur_frm.doc.reduzierte_mitgliedschaft,
                'language': cur_frm.doc.language
        },
        async: false,
        callback: function(res)
        {
            var druckvorlagen = res.message;
            // Default Druckvorlage für den Moment deaktiviert!
            //~ frappe.prompt([
                //~ {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage', 'default': druckvorlagen.default_druckvorlage, 
                    //~ 'get_query': function() {
                        //~ return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                    //~ }
                //~ }
            //~ ],
            frappe.prompt([
                {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage',
                    'get_query': function() {
                        return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                    }
                }
            ],
            function(values){
                frappe.call({
                    method: "mvd.mvd.doctype.fakultative_rechnung.fakultative_rechnung.create_hv_fr",
                    args:{
                            'mitgliedschaft': cur_frm.doc.name,
                            'druckvorlage': values.druckvorlage,
                            'asap_print': true
                    },
                    freeze: true,
                    freeze_message: 'Erstelle HV-Rechnung...',
                    callback: function(r)
                    {
                        cur_frm.timeline.insert_comment("HV-Rechnung " + r.message + " erstellt.");
                        cur_frm.reload_doc();
                        frappe.msgprint("Die HV-Rechnung wurde erstellt, Sie finden sie in den Anhängen.");
                    }
                });
            },
            'HV-Rechnung Erstellung',
            'Erstellen'
            )
        }
    });
}

function erstelle_korrespondenz(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.druckvorlage.druckvorlage.get_druckvorlagen",
        args:{
                'sektion': cur_frm.doc.sektion_id,
                'dokument': 'Korrespondenz',
                'mitgliedtyp': cur_frm.doc.mitgliedtyp_c,
                'reduzierte_mitgliedschaft': cur_frm.doc.reduzierte_mitgliedschaft,
                'language': cur_frm.doc.language
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
                            'mitgliedschaft': cur_frm.doc.name,
                            'druckvorlage': druckvorlage,
                            'titel': values.titel
                    },
                    freeze: true,
                    freeze_message: 'Erstelle Korrespondenz...',
                    callback: function(r)
                    {
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

function erstelle_begruessungs_korrespondenz(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.druckvorlage.druckvorlage.get_druckvorlagen",
        args:{
                'sektion': cur_frm.doc.sektion_id,
                'dokument': 'Begrüssung mit Ausweis',
                'mitgliedtyp': cur_frm.doc.mitgliedtyp_c,
                'reduzierte_mitgliedschaft': cur_frm.doc.reduzierte_mitgliedschaft,
                'language': cur_frm.doc.language
        },
        async: false,
        callback: function(res)
        {
            var druckvorlagen = res.message;
            // Default Druckvorlage für den Moment deaktiviert!
            //~ frappe.prompt([
                //~ {'fieldname': 'titel', 'fieldtype': 'Data', 'label': 'Titel', 'reqd': 1, 'default': 'Begrüssung mit Ausweis'},
                //~ {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 0, 'options': 'Druckvorlage', 'default': druckvorlagen.default_druckvorlage, 
                    //~ 'get_query': function() {
                        //~ return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                    //~ }
                //~ }
            frappe.prompt([
                {'fieldname': 'titel', 'fieldtype': 'Data', 'label': 'Titel', 'reqd': 1, 'default': 'Begrüssung mit Ausweis'},
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
                            'mitgliedschaft': cur_frm.doc.name,
                            'druckvorlage': druckvorlage,
                            'titel': values.titel
                    },
                    freeze: true,
                    freeze_message: 'Erstelle Korrespondenz...',
                    callback: function(r)
                    {
                        frappe.confirm(
                            'Möchten Sie den Druck des Begrüssungsdokument für den Massenlauf vormerken?',
                            function(){
                                // on yes
                                cur_frm.set_value("begruessung_massendruck", '1');
                                cur_frm.set_value("begruessung_massendruck_dokument", r.message);
                                cur_frm.set_value("validierung_notwendig", '0');
                                cur_frm.save();
                                frappe.msgprint("Die Daten wurden als validert bestätigt und der Druck des Begrüssungsdokument für den Massenlauf vorgemerkt.");
                            },
                            function(){
                                // on no
                                cur_frm.set_value("validierung_notwendig", '0');
                                cur_frm.save();
                                frappe.msgprint("Die Daten wurden als validert bestätigt, das erstellte Begrüssungsdokument finden Sie unter Korrespondenz.");
                            }
                        )
                    }
                });
            },
            'Begrüssungsdokument Erstellung',
            'Erstellen'
            )
        }
    });
    if (cur_frm.is_dirty()) {
        cur_frm.set_value("validierung_notwendig", '0');
        cur_frm.save();
    }
}

function erstelle_todo(frm) {
    frappe.call({
        'method': "frappe.client.get",
        'args': {
            'doctype': "Sektion",
            'name': frm.doc.sektion_id
        },
        'callback': function(response) {
            var sektion = response.message;
            if (!sektion.virtueller_user) {
                frappe.throw("Es muss zuerst ein virtueller Sektions-User in den Sektionseinstellungen hinterlegt werden!");
            }
            frappe.prompt([
                {'fieldname': 'owner', 'fieldtype': 'Link', 'label': 'Benutzer', 'reqd': 0, 'options': 'User', 'depends_on': 'eval:!doc.virtueller_user&&!doc.me', 'filters': { 'user_type': 'System User', 'name': ['!=', frappe.session.user] }},
                {'fieldname': 'me', 'fieldtype': 'Check', 'label': 'An mich zuweisen', 'default': 0, 'depends_on': 'eval:!doc.virtueller_user', 'change': function() {
                        if(cur_dialog.fields_dict.me.get_value()) {
                            cur_dialog.fields_dict.owner.set_value(frappe.session.user);
                        } else {
                            cur_dialog.fields_dict.owner.set_value('');
                        }
                    }
                },
                {'fieldname': 'virtueller_user', 'fieldtype': 'Check', 'label': 'An virtueller Sektions-User zuweisen', 'default': 0, 'depends_on': 'eval:!doc.me', 'hidden': !sektion.virtueller_user ? 1:0, 'change': function() {
                        if(cur_dialog.fields_dict.virtueller_user.get_value()) {
                            cur_dialog.fields_dict.owner.set_value(sektion.virtueller_user);
                        } else {
                            cur_dialog.fields_dict.owner.set_value('');
                        }
                    }
                },
                {'fieldname': 'description', 'fieldtype': 'Text', 'label': 'Beschreibung', 'reqd': 1},
                {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Fertigstellen bis', 'reqd': 0},
                {'fieldname': 'notify', 'fieldtype': 'Check', 'label': 'Per E-Mail benachrichtigen', 'default': 0}
            ],
            function(values){
                frappe.call({
                    "method": "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.erstelle_todo",
                    "args": {
                        "owner": values.owner,
                        "doctype": "Mitgliedschaft",
                        "mitglied": frm.doc.name,
                        "description": values.description,
                        "datum": values.datum,
                        "notify": values.notify
                    },
                    "callback": function(response) {
                        cur_frm.reload_doc();
                        frappe.msgprint( "Das ToDo wurde erstellt." );
                    }
                });
            },
            'ToDo erstellen',
            'Erstellen'
            )
        }
    });
    //~ frappe.msgprint( "tbd" );
}

