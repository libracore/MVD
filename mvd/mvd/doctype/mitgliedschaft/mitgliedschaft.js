// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mitgliedschaft', {
    setup: function(frm) {
        // override_default_email_dialog
        override_default_email_dialog(frm);
    },
    refresh: function(frm) {
       if (!frm.doc.__islocal) {
            if (!['Wegzug', 'Ausschluss'].includes(cur_frm.doc.status_c)) {
                if (!['Kündigung', 'Gestorben'].includes(cur_frm.doc.status_c)) {
                    frm.add_custom_button(__("Sektionswechsel"),  function() {
                            sektionswechsel(frm);
                    }, __("Mutation"));
                }
                if (!['Kündigung', 'Gestorben'].includes(cur_frm.doc.status_c)) {
                    frm.add_custom_button(__("Kündigung"),  function() {
                            kuendigung(frm);
                    }, __("Mutation"));
                }
                frm.add_custom_button(__("Ausschluss"),  function() {
                        ausschluss(frm);
                }, __("Mutation"));
                if (!['Gestorben'].includes(cur_frm.doc.status_c)) {
                    frm.add_custom_button(__("Todesfall"),  function() {
                            todesfall(frm);
                    }, __("Mutation"));
                }
                if (!['Gestorben', 'Kündigung'].includes(cur_frm.doc.status_c)) {
                    frm.add_custom_button(__("Mitgliedschafts-Rechnung"),  function() {
                            erstelle_rechnung(frm);
                    }, __("Erstelle"));
                    frm.add_custom_button(__("Spenden-Rechnung"),  function() {
                            erstelle_spenden_rechnung(frm);
                    }, __("Erstelle"));
                }
            }
            if (cur_frm.doc.validierung_notwendig) {
                frm.add_custom_button(__("Daten als validert bestätigen"),  function() {
                        daten_validiert(frm);
                });
            }
            if (cur_frm.doc.kuendigung_verarbeiten) {
                frm.add_custom_button(__("Kündigung als verarbeitet bestätigen"),  function() {
                        kuendigung_verarbeitet(frm);
                });
            }
            if (cur_frm.doc.interessent_innenbrief_mit_ez) {
                frm.add_custom_button(__("Interessent*Innenbrief mit EZ als verarbeitet bestätigen"),  function() {
                        interessent_innenbrief_mit_ez_verarbeitet(frm);
                });
            }
            if (cur_frm.doc.anmeldung_mit_ez) {
                frm.add_custom_button(__("Anmeldung mit EZ als verarbeitet bestätigen"),  function() {
                        anmeldung_mit_ez_verarbeitet(frm);
                });
            }
            
            // load html overview
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

function get_adressdaten(frm) {
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
                                {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage', 'default': druckvorlagen.default_druckvorlage, 
                                    'get_query': function() {
                                        return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                                    }
                                },
                                {'fieldname': 'massenlauf', 'fieldtype': 'Check', 'label': 'Für Massenlauf vormerken', 'default': 1}
                            ];
                        } else {
                            var field_list = [
                                {'fieldname': 'html_info', 'fieldtype': 'HTML', 'options': '<p style="color: red;">Achtung: Kündigungsfrist verpasst!</p>'},
                                {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Kündigung erfolgt per', 'reqd': 1, 'default': frappe.datetime.add_months(frappe.datetime.year_end(), 12), 'read_only': 1},
                                {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage', 'default': druckvorlagen.default_druckvorlage, 
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
            cur_frm.set_value("validierung_notwendig", '0');
            if (cur_frm.doc.status_c == 'Zuzug') {
                cur_frm.set_value("status_c", 'Regulär');
            }
            cur_frm.save();
            cur_frm.timeline.insert_comment("Validierung durchgeführt.");
            frappe.msgprint("Die Daten wurden als validert bestätigt.");
        },
        function(){
            // on no
        }
    )
}

function kuendigung_verarbeitet(frm) {
    frappe.confirm(
        'Haben Sie alle notwendigen Aktionen getroffen und möchten die Kündigung als verarbeitet bestätigen?',
        function(){
            // on yes
            cur_frm.set_value("kuendigung_verarbeiten", '0');
            cur_frm.save();
            cur_frm.timeline.insert_comment("Kündigung verarbeitet.");
            frappe.msgprint("Die Kündigung wurde als verarbeitet bestätigt.");
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

function erstelle_rechnung(frm) {
    var dokument = 'Anmeldung mit EZ mit EZ';
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
            frappe.prompt([
                {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage', 'default': druckvorlagen.default_druckvorlage, 
                    'get_query': function() {
                        return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                    }
                },
                {'fieldname': 'bar_bezahlt', 'fieldtype': 'Check', 'label': 'Barzahlung', 'reqd': 0, 'default': 0},
                {'fieldname': 'hv_bar_bezahlt', 'fieldtype': 'Check', 'label': 'HV Barzahlung', 'reqd': 0, 'default': 0, 'depends_on': 'eval:doc.bar_bezahlt==1'}
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
                frappe.call({
                    method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.create_mitgliedschaftsrechnung",
                    args:{
                            'mitgliedschaft': cur_frm.doc.name,
                            'bezahlt': bar_bezahlt,
                            'attach_as_pdf': true,
                            'submit': true,
                            'hv_bar_bezahlt': hv_bar_bezahlt,
                            'druckvorlage': values.druckvorlage
                    },
                    freeze: true,
                    freeze_message: 'Erstelle Rechnung...',
                    callback: function(r)
                    {
                        cur_frm.timeline.insert_comment("Mitgliedschaftsrechnung " + r.message + " erstellt.");
                        cur_frm.reload_doc();
                        frappe.msgprint("Die Rechnung wurde erstellt, Sie finden sie in den Anhängen.");
                    }
                });
            },
            'Rechnungs Erstellung',
            'Erstellen'
            )
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
            frappe.prompt([
                {'fieldname': 'betrag', 'fieldtype': 'Currency', 'label': 'Vorgeschlagener Betrag', 'reqd': 1, 'default': 0.0},
                {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage', 'default': druckvorlagen.default_druckvorlage, 
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

