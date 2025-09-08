// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mitgliedschaft', {
    refresh: function(frm) {
        // override_default_email_dialog
        override_default_email_dialog(frm);
        
       // Datensatz-Titel ergänzen
       mitglied_name_anzeigen(frm);
       
       // orange Navbar wenn form dirty
       dirty_observer(frm);

       // check for running_update_job
       check_for_running_job(frm);
       
       if (!frm.doc.__islocal&&cur_frm.doc.status_c == 'Inaktiv'&&!cur_frm.doc.wegzug_zu) {
           frappe.call({
                'method': "frappe.client.get",
                'args': {
                    'doctype': "MVD Settings",
                    'name': "MVD Settings"
                },
                'callback': function(response) {
                    var settings = response.message;
                    if (settings.reaktivierung_von_inaktiven) {
                       frm.add_custom_button(__("Reaktivieren"), function() {
                            mitglied_reaktivieren(frm);
                        }).addClass("btn-danger")
                    }
                }
            });
       }
       
       if (frappe.user.has_role("MV_MVD")) {
            frm.add_custom_button(__("Erstellung Faktura Kunde"), function() {
                erstellung_faktura_kunde(frm);
            }).addClass("btn-warning")
        }

        if (frappe.user.has_role("System Manager")) {
            frm.add_custom_button(__("SP > ERPNext"), function() {
                frappe.set_route("List", "Service Plattform Log", {'mv_mitgliedschaft': cur_frm.doc.name});
            }, __("Öffne SP Queue"))
            frm.add_custom_button(__("ERPNext > SP"), function() {
                frappe.set_route("List", "Service Platform Queue", {'mv_mitgliedschaft': cur_frm.doc.name});
            }, __("Öffne SP Queue"))
        }
        
       if (!frm.doc.__islocal&&cur_frm.doc.status_c != 'Inaktiv') {
            if (frappe.user.has_role("MV_beta")) {
                frm.add_custom_button(__("Vermieterkündigung erfassen"), function() {
                    erfassung_vermieterkuendigung(frm);
                }, __("Statistik"))
            }

            if (((cur_frm.doc.status_c != 'Inaktiv')&&(frappe.user.has_role("System Manager")))||(['Online-Anmeldung', 'Anmeldung', 'Interessent*in'].includes(cur_frm.doc.status_c))) {
                frm.add_custom_button(__("Inaktivieren"), function() {
                    mitglied_inaktivieren(frm);
                }).addClass("btn-danger")
            }
            
            if (frappe.user.has_role("System Manager")) {
                frm.add_custom_button(__("Status Historie ergänzen"), function() {
                    status_historie_ergaenzen(frm);
                }).addClass("btn-warning")
            }
            
            if ((!['Wegzug', 'Ausschluss', 'Online-Kündigung'].includes(cur_frm.doc.status_c))&&(cur_frm.doc.validierung_notwendig == 0)) {
                
                frm.add_custom_button(__("Beratung"),  function() {
                    erstelle_beratung_only(frm);
                }, __("Erstelle"));

                frm.add_custom_button(__("Beratungs Termin"),  function() {
                    erstelle_beratung(frm);
                }, __("Erstelle"));
                
                if ((!['Gestorben', 'Anmeldung', 'Online-Anmeldung'].includes(cur_frm.doc.status_c))&&(!cur_frm.doc.kuendigung)) {
                    frm.add_custom_button(__("Sektionswechsel"),  function() {
                        if (cur_frm.doc.mitgliedtyp_c == 'Geschäft') {
                            frappe.msgprint("Für Geschäftsmitglieder ist kein automatischer Sektionswechsel möglich.");
                        } else {
                            sektionswechsel(frm);
                        }
                    }, __("Mutation"));
                }
                
                if (cur_frm.doc.status_c == 'Anmeldung') {
                    if (((frappe.datetime.get_day_diff(frappe.datetime.now(), cur_frm.doc.creation)) <= 7)||(frappe.user.has_role("System Manager"))) {
                        frm.add_custom_button(__("Zuzug aus virtueller Sektion"),  function() {
                            sektionswechsel_pseudo_sektion(frm);
                        }, __("Mutation"));
                    }
                }
                
                if (!['Gestorben'].includes(cur_frm.doc.status_c)&&(!cur_frm.doc.kuendigung)) {
                    frm.add_custom_button(__("Kündigung"),  function() {
                        kuendigung(frm);
                    }, __("Mutation"));
                } else {
                    if (!['Gestorben'].includes(cur_frm.doc.status_c)&&(cur_frm.doc.kuendigung)) {
                        frm.add_custom_button(__("Kündigung zurückziehen"),  function() {
                            kuendigung_rueckzug(frm);
                        }, __("Mutation"));
                    }
                }
                
                frm.add_custom_button(__("Ausschluss"),  function() {
                    ausschluss(frm);
                }, __("Mutation"));
                
                if (!['Gestorben'].includes(cur_frm.doc.status_c)) {
                    frm.add_custom_button(__("Todesfall"),  function() {
                        todesfall(frm);
                    }, __("Mutation"));
                }
                
                if (!['Gestorben'].includes(cur_frm.doc.status_c)&&(!cur_frm.doc.kuendigung)) {
                    if (!cur_frm.doc.ist_geschenkmitgliedschaft) {
                        frm.add_custom_button(__("Mitgliedschafts-Rechnung"),  function() {
                            erstelle_rechnung(frm);
                        }, __("Erstelle"));
                    } else {
                        frm.add_custom_button(__("Mitgliedschafts-Rechnung (Geschenk)"),  function() {
                            erstelle_rechnung(frm);
                        }, __("Erstelle"));
                    }
                    
                    frm.add_custom_button(__("Spenden-Rechnung"),  function() {
                        erstelle_spenden_rechnung(frm);
                    }, __("Erstelle"));
                    
                    frm.add_custom_button(__("HV-Rechnung"),  function() {
                        erstelle_hv_rechnung(frm);
                    }, __("Erstelle"));
                }
                
                if (!['Gestorben'].includes(cur_frm.doc.status_c)) {
                    frm.add_custom_button(__("Korrespondenz"),  function() {
                        erstelle_korrespondenz(frm);
                    }, __("Erstelle"));
                }
                
                if (cur_frm.doc.ist_geschenkmitgliedschaft) {
                    frm.add_custom_button(__("Geschenk-Korrespondenz"),  function() {
                        erstelle_geschenk_korrespondenz(frm);
                    }, __("Erstelle"));
                }
            }
            
            if (cur_frm.doc.validierung_notwendig) {
                if (cur_frm.doc.status_c == 'Online-Kündigung') {
                    frm.add_custom_button(__("Online-Kündigung verarbeiten"),  function() {
                        kuendigung(frm);
                    });
                } else {
                    frm.add_custom_button(__("Daten als validert bestätigen"),  function() {
                        daten_validiert(frm);
                    });
                }
                
                // open sections
                cur_frm.fields_dict.section_allgemein.collapse();
                cur_frm.fields_dict.section_personen_daten.collapse();
                cur_frm.fields_dict.section_korrespondenz_adresse.collapse();
            }
            
            if (cur_frm.doc.kuendigung_verarbeiten) {
                frm.add_custom_button(__("Von Massenlauf (Kündigung) entfernen"),  function() {
                    kuendigung_verarbeitet(frm);
                });
            }
            
            if (cur_frm.doc.interessent_innenbrief_mit_ez) {
                frm.add_custom_button(__("Interessent*Innenbrief mit EZ als erstellt bestätigen"),  function() {
                    interessent_innenbrief_mit_ez_verarbeitet(frm);
                });
            }
            
            if (cur_frm.doc.anmeldung_mit_ez) {
                frm.add_custom_button(__("Anmeldung mit EZ als erstellt bestätigen"),  function() {
                    anmeldung_mit_ez_verarbeitet(frm);
                });
            }
            
            if (cur_frm.doc.rg_massendruck_vormerkung) {
                frm.add_custom_button(__("Von Massenlauf (Mitgliedschaftsrechnung) entfernen"),  function() {
                    rg_massendruck_verarbeitet(frm);
                });
            }
            
            if (cur_frm.doc.begruessung_massendruck) {
                if (!cur_frm.doc.begruessung_via_zahlung) {
                    frm.add_custom_button(__("Von Massenlauf (Begrüssung Online-Beitritt) entfernen"),  function() {
                        begruessung_massendruck_verarbeitet(frm);
                    });
                } else {
                    frm.add_custom_button(__("Von Massenlauf (Begrüssung Bezahlte Mitgliedschaft) entfernen"),  function() {
                        begruessung_massendruck_verarbeitet(frm);
                    });
                }
            }
        }
        
        if (!frm.doc.__islocal) {
            // load html overview
            load_html_overview(frm);
            
            // load retouren overview
            frappe.call({
                'method': "frappe.client.get",
                'args': {
                    'doctype': "MVD Settings",
                    'name': "MVD Settings"
                },
                'callback': function(response) {
                    var settings = response.message;

                    if (settings.retouren_management) {
                        load_retouren_overview(frm);
                    }
                }
            });
            
            load_beratungen_overview(frm);
            
            // assign hack
            $(".add-assignment.text-muted").remove();
            
            // hack to remove "+" in dashboard
            $(":button[data-doctype='Sales Invoice']").remove();
            $(":button[data-doctype='Fakultative Rechnung']").remove();
            $(":button[data-doctype='Payment Entry']").remove();
            $(":button[data-doctype='PayrexxWebhooks']").remove();
            $(":button[data-doctype='Beratung']").remove();
            $(":button[data-doctype='Termin']").remove();
            $(":button[data-doctype='Mahnung']").remove();
            $(":button[data-doctype='Service Plattform Log']").remove();
            $(":button[data-doctype='Korrespondenz']").remove();
            $(":button[data-doctype='Arbeits Backlog']").remove();
            $(":button[data-doctype='Retouren']").remove();
            $(":button[data-doctype='Kampagne']").remove();
            
            // button für Rechnung Sonstiges
            frm.add_custom_button(__("Rechnung (Sonstiges)"),  function() {
                erstelle_rechnung_sonstiges(frm);
            }, __("Erstelle"));
            
            // button für Aufhebung M+W Sperre
            if (cur_frm.doc.retoure_in_folge && cur_frm.doc.m_und_w == 0) {
                cur_frm.set_df_property('m_und_w', 'read_only', 1);
                frm.add_custom_button(__("M+W Sperre aufheben"),  function() {
                    m_und_w_sperre_aufheben(frm);
                });
            }
            // button für ToDo
            frm.add_custom_button(__("Erstelle ToDo"),  function() {
                erstelle_todo(frm);
            });
        }
        
        if (['Wegzug', 'Ausschluss', 'Inaktiv'].includes(cur_frm.doc.status_c)) {
            setze_read_only(frm);
            frm.disable_save();
            frm.add_custom_button(__("Wieder Beitritt"), function() {
                wieder_beitritt(frm);
            }).addClass("btn-danger")
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
        
        cur_frm.fields_dict['region'].get_query = function(doc) {
            return {
                filters: {
                    "disabled": ["!=", 1],
                    "sektion_id": cur_frm.doc.sektion_id
                }
            }
        }
        
        if (cint(cur_frm.doc.region_manuell)==1) {
            cur_frm.set_df_property('region', 'read_only', 0);
        } else {
            cur_frm.set_df_property('region', 'read_only', 1);
        }
        // freigabe Felder der Sektion "Daten" sowie Feld "status_c" für entsprechende Rolle
        if (frappe.user.has_role("System Manager")) {
            cur_frm.set_df_property('status_c', 'read_only', 0);
            cur_frm.set_df_property('zuzug', 'read_only', 0);
            cur_frm.set_df_property('wegzug', 'read_only', 0);
            cur_frm.set_df_property('zahlung_hv', 'read_only', 0);
            cur_frm.set_df_property('datum_hv_zahlung', 'read_only', 0);
            cur_frm.set_df_property('datum_zahlung_mitgliedschaft', 'read_only', 0);
            cur_frm.set_df_property('bezahltes_mitgliedschaftsjahr', 'read_only', 0);
            cur_frm.set_df_property('austritt', 'read_only', 0);
            cur_frm.set_df_property('zuzug_von', 'read_only', 0);
            cur_frm.set_df_property('wegzug_zu', 'read_only', 0);
            cur_frm.set_df_property('kuendigung', 'read_only', 0);
            cur_frm.set_df_property('verstorben_am', 'read_only', 0);
        }
        
        // Kündigungs-Mail-Button für MVBE
        if (cur_frm.doc.kuendigung && cur_frm.doc.status_c != 'Inaktiv' && cur_frm.doc.e_mail_1) {
            frm.add_custom_button(__("K-Best. E-Mail"),  function() {
                sende_k_best_email(frm);
            });
        }

        // deleted_by_admin hint
        if (cur_frm.doc.deleted_by_admin) {
            frm.set_intro("Dieser Eintrag wurde von einem Administrator inaktiviert/«gelöscht».");
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
            cur_frm.set_value("unabhaengiger_debitor", 0);
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
    rg_kundentyp: function(frm) {
        if (cur_frm.doc.rg_kundentyp == 'Unternehmen') {
            cur_frm.set_df_property('rg_nachname', 'reqd', 0);
            cur_frm.set_df_property('rg_firma', 'reqd', 1);
        } else {
            cur_frm.set_df_property('rg_nachname', 'reqd', 1);
            cur_frm.set_df_property('rg_firma', 'reqd', 0);
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
        // aktivierung sync
        cur_frm.set_value("letzte_bearbeitung_von", 'User');
        
        // E-Mail Adressen Validierung
        if (!locals.dont_check_email) {
            frm.call("email_validierung", {check: 1}, (r) => {
                if (r.message != 1) {
                    frappe.validated=false;
                    frappe.prompt([
                        {'fieldname': 'message', 'fieldtype': 'HTML', 'label': '', 'options': "Diese Mitgliedschaft enthält nachfolgende E-Mail-Adressen welche als fehlerhaft erkannt wurden:<br>" + r.message + "<br>Wenn Sie diese entfernen lass möchten, können Sie oben auf " + '"Entfernen" klicken.<br>Um die Adressen manuell zu korrigieren, klicken Sie auf "Schliessen".'}  
                    ],
                    function(values){
                        locals.dont_check_email = true;
                        cur_frm.save();
                    },
                    'Fehlerhafte E-Mail-Adressen',
                    'Entfernen'
                    );
                }
            });
        } else {
            locals.dont_check_email = false;
        }
        
        if (cur_frm.doc.kundentyp == 'Unternehmen') {
            if (cur_frm.doc.mitgliedtyp_c != 'Geschäft') {
                frappe.msgprint( "Unternehmen können nur Mitgliedschaften vom Typ Geschäft besitzen!", __("Validation") );
                frappe.validated=false;
            }
        }
        
        // Maximale Zeichenlängen Prüfung (SP lehnt sonst die Updates ab)
        if (cur_frm.doc.zusatz_adresse) {
            if (cur_frm.doc.zusatz_adresse.length > 40) {
                frappe.msgprint( "Die Serviceplatform lässt nur Adresszusätze bis zu einer Zeichenlänge von <b>40</b> zu.<br><br><b>Zeichenlänge " + cur_frm.doc.zusatz_adresse.length + ":</b><br>" + cur_frm.doc.zusatz_adresse, __("Validation") );
                frappe.validated=false;
            }
        }
        if (cur_frm.doc.strasse) {
            if (cur_frm.doc.strasse.length > 30) {
                frappe.msgprint( "Die Serviceplatform lässt nur Strassen bis zu einer Zeichenlänge von <b>30</b> zu.<br><br><b>Zeichenlänge " + cur_frm.doc.strasse.length + ":</b><br>" + cur_frm.doc.strasse, __("Validation") );
                frappe.validated=false;
            }
        }
        if (cur_frm.doc.objekt_zusatz_adresse) {
            if (cur_frm.doc.objekt_zusatz_adresse.length > 40) {
                frappe.msgprint( "Die Serviceplatform lässt nur Adresszusätze bis zu einer Zeichenlänge von <b>40</b> zu.<br><br><b>Zeichenlänge " + cur_frm.doc.objekt_zusatz_adresse.length + ":</b><br>" + cur_frm.doc.objekt_zusatz_adresse, __("Validation") );
                frappe.validated=false;
            }
        }
        if (cur_frm.doc.objekt_strasse) {
            if (cur_frm.doc.objekt_strasse.length > 30) {
                frappe.msgprint( "Die Serviceplatform lässt nur Strassen bis zu einer Zeichenlänge von <b>30</b> zu.<br><br><b>Zeichenlänge " + cur_frm.doc.objekt_strasse.length + ":</b><br>" + cur_frm.doc.objekt_strasse, __("Validation") );
                frappe.validated=false;
            }
        }
        if (cur_frm.doc.rg_zusatz_adresse) {
            if (cur_frm.doc.rg_zusatz_adresse.length > 40) {
                frappe.msgprint( "Die Serviceplatform lässt nur Adresszusätze bis zu einer Zeichenlänge von <b>40</b> zu.<br><br><b>Zeichenlänge " + cur_frm.doc.rg_zusatz_adresse.length + ":</b><br>" + cur_frm.doc.rg_zusatz_adresse, __("Validation") );
                frappe.validated=false;
            }
        }
        if (cur_frm.doc.rg_strasse) {
            if (cur_frm.doc.rg_strasse.length > 30) {
                frappe.msgprint( "Die Serviceplatform lässt nur Strassen bis zu einer Zeichenlänge von <b>30</b> zu.<br><br><b>Zeichenlänge " + cur_frm.doc.rg_strasse.length + ":</b><br>" + cur_frm.doc.rg_strasse, __("Validation") );
                frappe.validated=false;
            }
        }
        if (cur_frm.doc.firma) {
            if (cur_frm.doc.firma.length > 36) {
                frappe.msgprint( "Die Serviceplatform lässt nur Firmennamen bis zu einer Zeichenlänge von <b>36</b> zu.<br><br><b>Zeichenlänge " + cur_frm.doc.firma.length + ":</b><br>" + cur_frm.doc.firma, __("Validation") );
                frappe.validated=false;
            }
        }
        if (cur_frm.doc.rg_firma) {
            if (cur_frm.doc.rg_firma.length > 36) {
                frappe.msgprint( "Die Serviceplatform lässt nur Firmennamen bis zu einer Zeichenlänge von <b>36</b> zu.<br><br><b>Zeichenlänge " + cur_frm.doc.rg_firma.length + ":</b><br>" + cur_frm.doc.rg_firma, __("Validation") );
                frappe.validated=false;
            }
        }
        if (cur_frm.doc.status_c == 'Regulär'&&!cur_frm.doc.eintrittsdatum) {
            frappe.msgprint("Der Status Regulär ist nur in Kombination mit einem gesetzten Eintrittsdatum erlaubt.", __("Validation") );
            frappe.validated=false;
        }
    },
    after_save: function(frm) {
        // Abfrage ob M+W Retouren geschlossen werden sollen
        frappe.call({
            'method': "frappe.client.get",
            'args': {
                'doctype': "MVD Settings",
                'name': "MVD Settings"
            },
            'callback': function(response) {
                var settings = response.message;

                if (settings.retouren_management) {
                    if (cur_frm.doc.m_w_retouren_offen || cur_frm.doc.m_w_retouren_in_bearbeitung) {
                        frappe.confirm(
                            'Dieses Mitglied besitzt offene M+W Retouren. Möchten Sie diese als Abgeschlossen markieren?',
                            function(){
                                frappe.show_alert('Die offenen M+W Retouren werden geschlossen...', 5);
                                // on yes
                                frappe.call({
                                    method: "mvd.mvd.doctype.retouren.retouren.close_open_retouren",
                                    args:{
                                            'mitgliedschaft': cur_frm.doc.name
                                    },
                                    freeze: true,
                                    freeze_message: 'Die offenen M+W Retouren werden geschlossen...',
                                    callback: function(r){
                                        var resolve_reload = new Promise(function(resolve) {
                                            cur_frm.reload_doc();
                                            resolve(true);
                                        });
                                        resolve_reload.then(function(resolve_reload) {
                                            frappe.show_alert('Die M+W Retouren sind geschlossen...', 5);
                                        });
                                    }
                                });
                            },
                            function(){
                                // on no
                            }
                        )
                    }
                }
            }
        });
    },
    plz: function(frm) {
        pincode_lookup(cur_frm.doc.plz, 'ort');
    },
    objekt_plz: function(frm) {
        pincode_lookup(cur_frm.doc.objekt_plz, 'objekt_ort');
    },
    rg_plz: function(frm) {
        pincode_lookup(cur_frm.doc.rg_plz, 'rg_ort');
    },
    tel_p_1: function(frm) {
        is_valid_phone(cur_frm.doc.tel_p_1);
    },
    tel_m_1: function(frm) {
        is_valid_phone(cur_frm.doc.tel_m_1);
    },
    tel_g_1: function(frm) {
        is_valid_phone(cur_frm.doc.tel_g_1);
    },
    tel_p_2: function(frm) {
        is_valid_phone(cur_frm.doc.tel_p_2);
    },
    tel_m_2: function(frm) {
        is_valid_phone(cur_frm.doc.tel_m_2);
    },
    tel_g_2: function(frm) {
        is_valid_phone(cur_frm.doc.tel_g_2);
    },
    rg_tel_p: function(frm) {
        is_valid_phone(cur_frm.doc.rg_tel_p);
    },
    rg_tel_m: function(frm) {
        is_valid_phone(cur_frm.doc.rg_tel_m);
    },
    rg_tel_g: function(frm) {
        is_valid_phone(cur_frm.doc.rg_tel_g);
    },
    region_manuell: function(frm) {
        if (cint(cur_frm.doc.region_manuell)==1) {
            cur_frm.set_df_property('region', 'read_only', 0);
        } else {
            cur_frm.set_df_property('region', 'read_only', 1);
        }
    },
    digitalrechnung_button: function(frm) {
        frappe.route_options = {'mitglied_id' : cur_frm.doc.name};
        frappe.set_route("List", "Digitalrechnung");
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

function load_retouren_overview(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_returen_dashboard",
        args:{
                'mitgliedschaft': cur_frm.doc.name
        },
        callback: function(r)
        {
            var retouren = r.message;
            var info = '';
            var color = 'green';
            var show = false;
            if (retouren.anz_offen > 0) {
                info += retouren.anz_offen + " Offene ";
                color = 'red';
                show = true;
            }
            if (retouren.anz_in_bearbeitung > 0) {
                if (!show) {
                    info += retouren.anz_in_bearbeitung + " M+W Retoure(n) in Bearbeitung";
                    color = 'orange';
                    show = true;
                } else {
                    info += 'M+W Retoure(n) und ' + retouren.anz_in_bearbeitung + " in Bearbeitung";
                }
            } else {
                info += 'M+W Retoure(n)';
            }
            if (show) {
                cur_frm.dashboard.add_indicator(info, color);
            }
        }
    });
}

function load_beratungen_overview(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_beratungen_dashboard",
        args:{
                'mitgliedschaft': cur_frm.doc.name
        },
        callback: function(r)
        {
            var datas = r.message;
            var info = '';
            var color = 'red';
            var show = false;
            if (datas.anz_offen > 1) {
                info += "Offene Beratungen: " + datas.anz_offen;
                show = true;
            } else if (datas.anz_offen > 0) {
                info += "Offene Beratung";
                show = true;
            }
            if (datas.anz_termine > 0) {
                info += datas.termine;
            }
            if (show) {
                cur_frm.dashboard.add_indicator(info, color);
            }
            if (datas.ungelesen_qty > 0) {
                cur_frm.set_intro("Dieses Mitglied besitzt ungelesene Beratungen");
            }
        }
    });
}

function kuendigung(frm) {
    if (frappe.user.has_role("MV_MA")) {
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
                            
                            var kuendigungs_referenzdatum = frappe.datetime.str_to_obj(frappe.datetime.now_date());
                            var default_grund = '';
                            var abw_grund = '';
                            
                            cur_frm.doc.status_change.forEach(function(entry) {
                                if (entry.status_neu == 'Online-Kündigung') {
                                    if (entry.grund){
                                        if (entry.grund.includes("Andere Gründe")&&entry.idx == cur_frm.doc.status_change.length) {
                                            default_grund = 'Andere Gründe';
                                            if (entry.grund.split("Andere Gründe: ").length > 1) {
                                                abw_grund = entry.grund.split("Andere Gründe: ")[1];
                                            }
                                            kuendigungs_referenzdatum = frappe.datetime.str_to_obj(entry.datum);
                                        } else if (entry.idx == cur_frm.doc.status_change.length) {
                                            if (entry.grund) {
                                                default_grund = entry.grund;
                                                kuendigungs_referenzdatum = frappe.datetime.str_to_obj(entry.datum);
                                            } else {
                                                default_grund = 'Keine Angabe';
                                                kuendigungs_referenzdatum = frappe.datetime.str_to_obj(entry.datum);
                                            }
                                        }
                                    } else if (entry.idx == cur_frm.doc.status_change.length) {
                                        if (entry.grund) {
                                            default_grund = entry.grund;
                                            kuendigungs_referenzdatum = frappe.datetime.str_to_obj(entry.datum);
                                        } else {
                                            default_grund = 'Keine Angabe';
                                            kuendigungs_referenzdatum = frappe.datetime.str_to_obj(entry.datum);
                                        }
                                    }
                                }
                            });
                            
                            var kuendigungs_referenzdatum_month = kuendigungs_referenzdatum.getMonth();
                            var kuendigungs_referenzdatum_day = kuendigungs_referenzdatum.getDate();
                            
                            var fristgerecht = true;
                            
                            if (kuendigungs_referenzdatum_month > ks_month) {
                                fristgerecht = false;
                            } else {
                                if (kuendigungs_referenzdatum_month == ks_month) {
                                    if (kuendigungs_referenzdatum_day > ks_day) {
                                        fristgerecht = false;
                                    }
                                }
                            }
                            
                            
                            
                            
                            if (fristgerecht) {
                                var field_list = [
                                    {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Kündigung erfolgt per', 'reqd': 1, 'default': cur_frm.doc.kuendigung ? cur_frm.doc.kuendigung:frappe.datetime.year_end()},
                                    {'fieldname': 'grund', 'fieldtype': 'Select', 'label': 'Kündigungsgrund', 'reqd': 1, 'options': 'Wohneigentum gekauft habe\nins Altersheim/Genossenschaft umziehe\nkeine Probleme mit dem Vermieter habe\nder Mitgliederbeitrag zu hoch ist\nmit den MV-Dienstleistungen nicht zufrieden bin\nmit den MV-Positionen nicht einverstanden bin\neine andere Rechtsschutzversicherung erworben habe\nAndere Gründe\nKeine Angabe', 'default': default_grund, 'change': function() {
                                            if (cur_dialog.fields_dict.grund.get_value() == 'Andere Gründe') {
                                                cur_dialog.fields_dict.abw_grund.df.hidden = 0;
                                                cur_dialog.fields_dict.abw_grund.refresh();
                                            } else {
                                                cur_dialog.fields_dict.abw_grund.df.hidden = 1;
                                                cur_dialog.fields_dict.abw_grund.refresh();
                                            }
                                        }
                                    },
                                    {'fieldname': 'abw_grund', 'fieldtype': 'Data', 'label': 'Andere Gründe', 'hidden': default_grund.includes("Andere Gründe") ? 0:1, 'default': abw_grund},
                                    {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage',
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
                                    {'fieldname': 'grund', 'fieldtype': 'Select', 'label': 'Kündigungsgrund', 'reqd': 1, 'options': 'Wohneigentum gekauft habe\nins Altersheim/Genossenschaft umziehe\nkeine Probleme mit dem Vermieter habe\nder Mitgliederbeitrag zu hoch ist\nmit den MV-Dienstleistungen nicht zufrieden bin\nmit den MV-Positionen nicht einverstanden bin\neine andere Rechtsschutzversicherung erworben habe\nAndere Gründe', 'default': default_grund, 'change': function() {
                                            if (cur_dialog.fields_dict.grund.get_value() == 'Andere Gründe') {
                                                cur_dialog.fields_dict.abw_grund.df.hidden = 0;
                                                cur_dialog.fields_dict.abw_grund.refresh();
                                            } else {
                                                cur_dialog.fields_dict.abw_grund.df.hidden = 1;
                                                cur_dialog.fields_dict.abw_grund.refresh();
                                            }
                                        }
                                    },
                                    {'fieldname': 'abw_grund', 'fieldtype': 'Data', 'label': 'Andere Gründe', 'hidden': default_grund.includes("Andere Gründe") ? 0:1, 'default': abw_grund},
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
                                var _grund = values.grund ? values.grund:'Ohne Begründung'
                                if (values.grund == 'Andere Gründe') {
                                    _grund = values.grund + ": " + values.abw_grund;
                                }
                                frappe.call({
                                    method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.make_kuendigungs_prozess",
                                    args:{
                                            'mitgliedschaft': cur_frm.doc.name,
                                            'datum_kuendigung': values.datum,
                                            'massenlauf': values.massenlauf,
                                            'druckvorlage': values.druckvorlage,
                                            'grund': _grund
                                    },
                                    freeze: true,
                                    freeze_message: 'Erstelle Kündigung inkl. Bestätigung...',
                                    callback: function(r)
                                    {
                                        cur_frm.reload_doc();
                                        cur_frm.timeline.insert_comment("Kündigung");
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
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function kuendigung_rueckzug(frm) {
    frappe.confirm(
        'Wollen Sie die Kündigung zurückziehen?',
        function(){
            cur_frm.set_value("kuendigung", '');
            var status_change_log = cur_frm.add_child('status_change');
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'datum', frappe.datetime.get_today());
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_alt', 'Regulär &dagger;');
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_neu', 'Regulär');
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'grund', "Kündigungs Rückzug");
            cur_frm.refresh_field('status_change');
            cur_frm.save().then(function(){
                frappe.msgprint("Die Kündigung wurde zurückgezogen.");
            });
        },
        function(){
            // on no
        }
    )
    
}

function todesfall(frm) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.prompt([
            {'fieldname': 'verstorben_am', 'fieldtype': 'Date', 'label': 'Verstorben am (oder Meldung)', 'reqd': 1, 'default': frappe.datetime.get_today()},
            {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Todesfallbedingte inaktivierung erfolgt per', 'reqd': 1, 'default': frappe.datetime.get_today()},
            {'fieldname': 'todesfall_uebernahme', 'fieldtype': 'Data', 'label': 'Übernommen durch'}
        ],
        function(values){
            cur_frm.set_value("austritt", values.datum);
            cur_frm.set_value("verstorben_am", values.verstorben_am);
            
            cur_frm.set_value("m_und_w", 0);
            cur_frm.set_value("adressen_gesperrt", 1);
            
            var status_change_log = cur_frm.add_child('status_change');
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'datum', frappe.datetime.get_today());
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_alt', cur_frm.doc.status_c);
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_neu', 'Gestorben');
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'grund', "Gestorben");
            cur_frm.refresh_field('status_change');
            cur_frm.set_value("status_c", 'Gestorben');
            if (values.todesfall_uebernahme) {
                cur_frm.set_value("todesfall_uebernahme", values.todesfall_uebernahme);
            }
            cur_frm.save().then(function(){
                cur_frm.timeline.insert_comment("Todesfall erfasst.");
                frappe.msgprint("Der Todesfall sowie der damit verbundene Austritt wurde per " + frappe.datetime.obj_to_user(values.datum) + " erfasst.");
            });
        },
        'Todesfall',
        'Erfassen'
        )
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function ausschluss(frm) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.prompt([
            {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Ausschluss per', 'reqd': 1, 'default': frappe.datetime.get_today()},
            {'fieldname': 'grund', 'fieldtype': 'Text', 'label': 'Ausschluss Begründung'}
        ],
        function(values){
            cur_frm.set_value("austritt", values.datum);
            var status_change_log = cur_frm.add_child('status_change');
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'datum', frappe.datetime.get_today());
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_alt', cur_frm.doc.status_c);
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_neu', 'Ausschluss');
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'grund', "Ausschluss: " + values.grund);
            cur_frm.refresh_field('status_change');
            cur_frm.set_value("status_c", 'Ausschluss');
            if (values.grund) {
                var alte_infos = cur_frm.doc.wichtig;
                var neue_infos = "Ausschluss:\n" + values.grund + "\n\n";
                neue_infos = neue_infos + alte_infos;
                cur_frm.set_value("wichtig", neue_infos);
            }
            cur_frm.set_value("adressen_gesperrt", 1);
            cur_frm.save().then(function(){
                cur_frm.timeline.insert_comment("Ausschluss vollzogen.");
                frappe.msgprint("Der Ausschluss wurde per " + frappe.datetime.obj_to_user(values.datum) + " erfasst.");
            });
        },
        'Ausschluss',
        'Erfassen'
        )
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function sektionswechsel_pseudo_sektion(frm) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.call({
            method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_pseudo_sektionen_zur_auswahl",
            args:{},
            callback: function(r)
            {
                var sektionen_zur_auswahl = r.message;
                frappe.prompt([
                    {'fieldname': 'sektion_neu', 'fieldtype': 'Select', 'label': 'Zuzug von', 'reqd': 1, 'options': sektionen_zur_auswahl},
                    {'fieldname': 'eintrittsdatum', 'fieldtype': 'Date', 'label': 'Eintrittsdatum', 'reqd': 1, 'default': frappe.datetime.get_today()},
                    {'fieldname': 'mitgliedschaft_bezahlt', 'fieldtype': 'Int', 'label': 'Mitgliedschaft bezahlt', 'reqd': 1, 'default': '0', 'description': 'Jahr für das die Mitgliedschaft bezahlt wurde, oder 0 falls Rechnung offen'},
                    {'fieldname': 'zuzug_datum', 'fieldtype': 'Date', 'label': 'Zuzug Datum', 'reqd': 1, 'default': frappe.datetime.get_today()}
                ],
                function(values){
                    frappe.call({
                        method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.sektionswechsel_pseudo_sektion",
                        args:{
                                'mitgliedschaft': cur_frm.doc.name,
                                'eintrittsdatum': values.eintrittsdatum,
                                'bezahltes_mitgliedschaftsjahr': values.mitgliedschaft_bezahlt,
                                'zuzug_von': cur_frm.doc.sektion_id,
                                'sektion_id': values.sektion_neu,
                                'zuzug': values.zuzug_datum
                        },
                        freeze: true,
                        freeze_message: 'Führe Sektionswechsel durch...',
                        callback: function(r)
                        {
                            if (r.message.status == 200) {
                                if (values.mitgliedschaft_bezahlt != String(frappe.datetime.get_today()).split("-")[0]) {
                                    frappe.msgprint("Die Rechnung wurde erstellt, bitte ausdrucken und zustellen.");
                                } else {
                                    frappe.msgprint("Die Begrüssungs Korrespondenz wurde erstellt, bitte ausdrucken und zustellen.");
                                }
                            } else {
                                if (r.message.status == 500) {
                                    frappe.msgprint(`oops, da ist etwas schiefgelaufen!<br>${r.message.error}`);
                                } else {
                                    frappe.msgprint("oops, da ist etwas schiefgelaufen!<br>Unbekannter Fehler");
                                }
                            }
                            cur_frm.reload_doc();
                        }
                    });
                },
                'Zuzug aus virtueller Sektion',
                'Übertragen'
                )
            }
        });
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function sektionswechsel(frm) {
    if (frappe.user.has_role("MV_MA")) {
        if (cur_frm.doc.zuzug_id||cint(cur_frm.doc.sektionswechsel_beantragt)==1) {
            if (cur_frm.doc.zuzug_id) {
                frappe.msgprint("Für dieses Mitglied wurde bereits ein Sektionswechsel vollzogen.");
            } else {
                frappe.msgprint("Für dieses Mitglied wurde bereits ein Sektionswechsel beantragt, welcher fehlgeschlagen ist.<br>Bitte kontaktieren Sie einen Administrator.");
            }
        } else {
            frappe.db.get_value("Mitgliedschaft", cur_frm.doc.name, "sektionswechsel_beantragt").then(function(sektionswechsel_beantragt) {
                if(cint(sektionswechsel_beantragt.message.sektionswechsel_beantragt)==1) {
                    frappe.msgprint("Für dieses Mitglied wurde bereits ein Sektionswechsel beantragt, welcher fehlgeschlagen ist.<br>Bitte kontaktieren Sie einen Administrator.");
                } else {
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
                                        if (r.message.status == 200) {
                                            cur_frm.set_value("wegzug", frappe.datetime.get_today());
                                            cur_frm.set_value("wegzug_zu", values.sektion_neu);
                                            cur_frm.set_value("zuzug_id", r.message.new_id);
                                            var status_change_log = cur_frm.add_child('status_change');
                                            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'datum', frappe.datetime.get_today());
                                            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_alt', cur_frm.doc.status_c);
                                            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_neu', 'Wegzug');
                                            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'grund', "Sektionswechsel zu " + values.sektion_neu);
                                            cur_frm.refresh_field('status_change');
                                            cur_frm.set_value("status_c", 'Wegzug');
                                            cur_frm.set_value("sektionswechsel_beantragt", 1);
                                            cur_frm.save().then(function(){
                                                cur_frm.timeline.insert_comment("Sektionswechsel zu " + values.sektion_neu + " vollzogen.");
                                                frappe.msgprint("Der Wechsel zur Sektion " + values.sektion_neu + " erfolgt.");
                                            });
                                        } else {
                                            if (r.message.status == 500) {
                                                frappe.msgprint(`oops, da ist etwas schiefgelaufen!<br>${r.message.error}`);
                                            } else {
                                                frappe.msgprint("oops, da ist etwas schiefgelaufen!<br>Unbekannter Fehler");
                                            }
                                            cur_frm.set_value("sektionswechsel_beantragt", 1);
                                            cur_frm.save()
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
            });
        }
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function daten_validiert(frm) {
    if (frappe.user.has_role("MV_MA")) {
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
                            var status_change_log = cur_frm.add_child('status_change');
                            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'datum', frappe.datetime.get_today());
                            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_alt', cur_frm.doc.status_c);
                            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_neu', 'Regulär');
                            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'grund', "Zuzugsvalidierung");
                            cur_frm.refresh_field('status_change');
                            cur_frm.set_value("status_c", 'Regulär');
                            cur_frm.save().then(function(){
                                cur_frm.timeline.insert_comment("Validierung durchgeführt.");
                                frappe.msgprint("Die Daten wurden als validert bestätigt und der Druck des Zuzugsdokument für den Massenlauf vorgemerkt.");
                            });
                        },
                        function(){
                            // on no
                            cur_frm.set_value("zuzug_massendruck", 0);
                            cur_frm.set_value("validierung_notwendig", 0);
                            var status_change_log = cur_frm.add_child('status_change');
                            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'datum', frappe.datetime.get_today());
                            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_alt', cur_frm.doc.status_c);
                            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_neu', 'Regulär');
                            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'grund', "Zuzugsvalidierung");
                            cur_frm.refresh_field('status_change');
                            cur_frm.set_value("status_c", 'Regulär');
                            cur_frm.save().then(function(){
                                cur_frm.timeline.insert_comment("Validierung durchgeführt.");
                                frappe.msgprint("Die Daten wurden als validert bestätigt.");
                            });
                        }
                    )
                } else if (cur_frm.doc.status_c == 'Online-Anmeldung') {
                    cur_frm.set_value("validierung_notwendig", '0');
                    cur_frm.timeline.insert_comment("Validierung durchgeführt.");
                    cur_frm.save().then(function(){
                        erstelle_rechnung(frm);
                    });
                } else if (cur_frm.doc.status_c == 'Online-Beitritt') {
                    cur_frm.set_value("validierung_notwendig", '0');
                    var status_change_log = cur_frm.add_child('status_change');
                    frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'datum', frappe.datetime.get_today());
                    frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_alt', cur_frm.doc.status_c);
                    frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_neu', 'Regulär');
                    frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'grund', "Validierung Online-Beitritt");
                    cur_frm.refresh_field('status_change');
                    cur_frm.set_value("status_c", 'Regulär');
                    cur_frm.timeline.insert_comment("Validierung durchgeführt.");
                    // verhinderung der E-Mailprüfung (ISS-2024-00127/#1016)
                    locals.dont_check_email = true;
                    cur_frm.save().then(function(){
                        erstelle_begruessungs_korrespondenz(frm);
                    });
                } else if (cur_frm.doc.status_c == 'Online-Mutation') {
                    if (cur_frm.doc.status_vor_onl_mutation) {
                        var alter_status = cur_frm.doc.status_vor_onl_mutation;
                        cur_frm.set_value("status_c", alter_status);
                    } else {
                        cur_frm.set_value("status_c", 'Regulär');
                    }
                    if ((alter_status == 'Regulär')&&(cur_frm.doc.kuendigung)) {
                        var status_change_log = cur_frm.add_child('status_change');
                        frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'datum', frappe.datetime.get_today());
                        frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_alt', 'Online-Mutation');
                        frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_neu', 'Regulär &dagger;');
                        frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'grund', "Validierung Online-Mutation");
                        cur_frm.refresh_field('status_change');
                    } else {
                        var status_change_log = cur_frm.add_child('status_change');
                        frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'datum', frappe.datetime.get_today());
                        frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_alt', 'Online-Mutation');
                        frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_neu', alter_status);
                        frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'grund', "Validierung Online-Mutation");
                        cur_frm.refresh_field('status_change');
                    }
                    if (cur_frm.doc.status_vor_onl_mutation && cur_frm.doc.status_vor_onl_mutation != 'Online-Kündigung') {
                        // Nur wenn nicht Special Case: Regulär > Online-Kündigung > Online-Mutation
                        cur_frm.set_value("validierung_notwendig", '0');
                    }
                    cur_frm.set_value("status_vor_onl_mutation", '');
                    cur_frm.save().then(function(){
                        cur_frm.timeline.insert_comment("Validierung durchgeführt.");
                        if (cur_frm.doc.ist_geschenkmitgliedschaft) {
                            frappe.msgprint("Die Daten wurden als validert bestätigt.<br><b>Achtung:</b> es handelt sich um eine Geschenkmitgliedschaft.");
                        }
                    });
                } else {
                    cur_frm.set_value("validierung_notwendig", '0');
                    cur_frm.set_value("status_c", 'Regulär');
                    cur_frm.save().then(function(){
                        cur_frm.timeline.insert_comment("Validierung durchgeführt.");
                        if (cur_frm.doc.ist_geschenkmitgliedschaft) {
                            frappe.msgprint("Die Daten wurden als validert bestätigt.<br><b>Achtung:</b> es handelt sich um eine Geschenkmitgliedschaft.");
                        } else {
                            frappe.msgprint("Die Daten wurden als validert bestätigt.");
                        }
                    });
                }
            },
            function(){
                // on no
            }
        )
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function kuendigung_verarbeitet(frm) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.confirm(
            'Haben Sie die Kündigung manuell gedruckt und möchten Sie sie aus dem Massenlauf entfernen?',
            function(){
                // on yes
                cur_frm.set_value("kuendigung_verarbeiten", '0');
                cur_frm.save().then(function(){
                    cur_frm.timeline.insert_comment("Kündigung verarbeitet.");
                    frappe.msgprint("Die Kündigung wurde aus dem Massenlauf entfernt.");
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

function interessent_innenbrief_mit_ez_verarbeitet(frm) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.confirm(
            'Haben Sie den Interessent*Innenbrief mit EZ erstellt und möchten diesen als verarbeitet bestätigen?',
            function(){
                // on yes
                cur_frm.set_value("interessent_innenbrief_mit_ez", '0');
                cur_frm.save().then(function(){
                    cur_frm.timeline.insert_comment("Interessent*Innenbrief mit EZ erstellt.");
                    frappe.msgprint("Der Interessent*Innenbrief mit EZ wurde als verarbeitet bestätigt.");
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

function anmeldung_mit_ez_verarbeitet(frm) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.confirm(
            'Haben Sie die Anmeldung mit EZ erstellt und möchten diesen als verarbeitet bestätigen?',
            function(){
                // on yes
                cur_frm.set_value("anmeldung_mit_ez", '0');
                cur_frm.save().then(function(){
                    cur_frm.timeline.insert_comment("Anmeldung mit EZ erstellt.");
                    frappe.msgprint("Die Anmeldung mit EZ wurde als verarbeitet bestätigt.");
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

function rg_massendruck_verarbeitet(frm) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.confirm(
            'Haben Sie die Mitgliedschaftsrechnung manuell gedruckt und möchten Sie sie aus dem Massenlauf entfernen?',
            function(){
                // on yes
                cur_frm.set_value("rg_massendruck_vormerkung", '0');
                cur_frm.set_value("rg_massendruck", '');
                cur_frm.save().then(function(){
                    frappe.msgprint("Der Druck der Mitgliedschaftsrechnung wurde aus dem Massenlauf entfernt.");
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

function begruessung_massendruck_verarbeitet(frm) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.confirm(
            'Haben Sie das Begrüssungsschreiben manuell gedruckt und möchten Sie dies aus dem Massenlauf entfernen?',
            function(){
                // on yes
                cur_frm.set_value("begruessung_massendruck", '0');
                cur_frm.set_value("begruessung_via_zahlung", '0');
                cur_frm.set_value("begruessung_massendruck_dokument", '');
                cur_frm.save().then(function(){
                    frappe.msgprint("Der Druck des Begrüssungsschreibens wurde aus dem Massenlauf entfernt.");
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



function erstelle_rechnung(frm) {
    if (frappe.user.has_role("MV_MA")) {
        if (!cur_frm.doc.ist_geschenkmitgliedschaft) {
            // normale Mitgliedschaft
            erstelle_normale_rechnung(frm);
        } else {
            // Geschenkmitgliedschaft
            // prüfung bezgl. "einmalige Schenkung"
            if (cur_frm.doc.ist_einmalige_schenkung && cur_frm.doc.unabhaengiger_debitor) {
                // Warnhinweis
                frappe.msgprint("Es handelt sich hierbei um eine <b>einmalige Schenkung</b>.<br>Bitte entfernen Sie zuerst den unabhängigen Debitor und die zugehörige abweichende Rechnungsadresse.", "Achtung: einmalige Schenkung");
            } else {
                erstelle_geschenk_rechnung(frm);
            }
        }
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function erstelle_geschenk_rechnung(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.check_erstelle_rechnung",
        args:{
                'mitgliedschaft': cur_frm.doc.name,
                'typ': cur_frm.doc.mitgliedtyp_c,
                'sektion': cur_frm.doc.sektion_id
        },
        callback: function(r)
        {
            // Prüfung ob Rechnung für aktuelles Jahr
            if (r.message == 1) {
                var dokument = 'Geschenk-Weiterführung';
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
                            {'fieldname': 'rg_druckvorlage', 'fieldtype': 'Link', 'label': 'Rechnungs Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage',
                                'get_query': function() {
                                    return { 'filters': {
                                        'dokument': 'Jahresrechnung',
                                        'sektion_id': cur_frm.doc.sektion_id,
                                        'deaktiviert': ['!=', 1]
                                    } };
                                }
                            },
                            {'fieldname': 'korrespondenz_druckvorlage', 'fieldtype': 'Link', 'label': 'Korrespondenz Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage',
                                'get_query': function() {
                                    return { 'filters': {
                                        'dokument': 'Korrespondenz',
                                        'sektion_id': cur_frm.doc.sektion_id,
                                        'deaktiviert': ['!=', 1]
                                    } };
                                }
                            }
                        ],
                        function(values){
                            frappe.call({
                                method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.create_mitgliedschaftsrechnung",
                                args:{
                                        'mitgliedschaft': cur_frm.doc.name,
                                        'attach_as_pdf': true,
                                        'submit': true,
                                        'druckvorlage': values.rg_druckvorlage,
                                        'geschenk_reset': true
                                },
                                freeze: true,
                                freeze_message: 'Erstelle Rechnung und Korrespondenz...',
                                callback: function(r)
                                {
                                    //~ cur_frm.reload_doc();
                                    cur_frm.timeline.insert_comment("Mitgliedschaftsrechnung " + r.message + " erstellt.");
                                    
                                    
                                    frappe.call({
                                        method: "mvd.mvd.doctype.mitgliedschaft.utils.create_korrespondenz",
                                        args:{
                                                'mitgliedschaft': cur_frm.doc.name,
                                                'druckvorlage': values.korrespondenz_druckvorlage,
                                                'titel': "Begleitschreiben zu " + r.message,
                                                'attach_as_pdf': true,
                                                'sinv_mitgliedschaftsjahr': r.message
                                        },
                                        freeze: true,
                                        freeze_message: 'Erstelle Korrespondenz...',
                                        callback: function(res)
                                        {
                                            cur_frm.reload_doc();
                                            cur_frm.timeline.insert_comment("Korrespondenz " + res.message + " erstellt.");
                                            frappe.msgprint("Die Rechnung und Korrespondenz wurde erstellt, Sie finden sie in den Anhängen.");
                                        }
                                    });
                                }
                            });
                        },
                        'Rechnungs/Korrespondenz Erstellung',
                        'Erstellen'
                        )
                    }
                });
            } else {
                // Rechnung für aktuelles Jahr bereits gestellt, prüfung für Folgejahrrechnung
                //~ frappe.call({
                    //~ method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.check_erstelle_rechnung",
                    //~ args:{
                            //~ 'mitgliedschaft': cur_frm.doc.name,
                            //~ 'typ': cur_frm.doc.mitgliedtyp_c,
                            //~ 'sektion': cur_frm.doc.sektion_id,
                            //~ 'jahr': r.message
                    //~ },
                    //~ callback: function(response)
                    //~ {
                        //~ if (response.message == 1) {
                            //~ var txt = 'Die Rechnung des entsprechenden Jahres wurde bereits erstellt.<br>Wenn Sie diese neu erstellen möchten, müssen Sie die existierende zuerst stornieren.<br><br>';
                            //~ txt += 'Alternativ können Sie eine Rechnung für das Jahr ' + r.message + ' erstellen.</p>'
                            
                            //~ frappe.prompt([
                                //~ {'fieldname': 'txt', 'fieldtype': 'HTML', 'options': txt}  
                            //~ ],
                            //~ function(values){
                                //~ erstelle_folgejahr_rechnung(frm, r.message)
                            //~ },
                            //~ 'Rechnungserstellung',
                            //~ 'Erstelle Rechnung für ' + r.message
                            //~ )
                        //~ } else {
                            //~ frappe.msgprint("Es wurde bereits für das aktuelle Jahr sowie das Folgejahr eine Rechnung erstellt.");
                        //~ }
                    //~ }
                //~ });
            }
        }
    });
}

function erstelle_normale_rechnung(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.check_erstelle_rechnung",
        args:{
                'mitgliedschaft': cur_frm.doc.name,
                'typ': cur_frm.doc.mitgliedtyp_c,
                'sektion': cur_frm.doc.sektion_id
        },
        callback: function(r)
        {
            // Prüfung ob Rechnung für aktuelles Jahr
            if (r.message == 1) {
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
                        frappe.call({
                            'method': "frappe.client.get",
                            'args': {
                                'doctype': "MVD Settings",
                                'name': "MVD Settings"
                            },
                            'callback': function(settings_response) {
                                var settings = settings_response.message;
                                frappe.prompt([
                                    {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage',
                                        'get_query': function() {
                                            return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                                        }
                                    },
                                    {'fieldname': 'bar_bezahlt', 'fieldtype': 'Check', 'label': 'Barzahlung', 'reqd': 0, 'default': 0, 'hidden': cur_frm.doc.status_c != 'Online-Anmeldung' ? 0:1},
                                    {'fieldname': 'hv_bar_bezahlt', 'fieldtype': 'Check', 'label': 'HV Barzahlung', 'reqd': 0, 'default': 0, 'depends_on': 'eval:doc.bar_bezahlt==1'},
                                    {'fieldname': 'massendruck', 'fieldtype': 'Check', 'label': 'Für Massendruck vormerken', 'reqd': 0, 'default': 0},
                                    {'fieldname': 'eigene_items', 'fieldtype': 'Check', 'label': 'Manuelle Artikel Auswahl', 'reqd': 0, 'default': 0, 'hidden': settings.manuelle_artikelauswahl ? 0:1},
                                    {
                                        label: "Rechnungs Artikel",
                                        fieldname: "rechnungs_artikel", 
                                        fieldtype: "Table", 
                                        cannot_add_rows: false,
                                        in_place_edit: false,
                                        depends_on: 'eval:doc.eigene_items',
                                        data: [],
                                        get_data: () => {
                                            return [];
                                        },
                                        fields: [
                                        {
                                            fieldtype:'Link',
                                            fieldname:"item_code",
                                            options: 'Item',
                                            in_list_view: 1,
                                            read_only: 0,
                                            reqd: 1,
                                            label: __('Item Code'),
                                            change: function() {
                                                if (this.get_value()) {
                                                    var rate_field = this.grid_row.on_grid_fields[2]
                                                    var qty_field = this.grid_row.on_grid_fields[1];
                                                    frappe.call({
                                                        method: "mvd.mvd.utils.manuelle_rechnungs_items.get_item_price",
                                                        args:{
                                                                'item': this.get_value()
                                                        },
                                                        callback: function(r)
                                                        {
                                                            rate_field.set_value(r.message.price);
                                                            qty_field.set_value(1);
                                                        }
                                                    });
                                                }
                                            },
                                            get_query: function() {
                                                return { 'filters': { 'mitgliedschaftsspezifischer_artikel': 1 } };
                                            }
                                        },
                                        {
                                            fieldtype:'Int',
                                            fieldname:"qty",
                                            in_list_view: 1,
                                            read_only: 1,
                                            label: __('Qty'),
                                            reqd: 1
                                        },
                                        {
                                            fieldtype:'Currency',
                                            fieldname:"rate",
                                            in_list_view: 1,
                                            read_only: 0,
                                            label: __('Rate'),
                                            reqd: 1
                                        }]
                                    }
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
                                                'massendruck': massendruck,
                                                'eigene_items': values.eigene_items,
                                                'rechnungs_artikel': values.rechnungs_artikel
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
                });
            } else {
                // Rechnung für aktuelles Jahr bereits gestellt, prüfung für Folgejahrrechnung
                frappe.call({
                    method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.check_erstelle_rechnung",
                    args:{
                            'mitgliedschaft': cur_frm.doc.name,
                            'typ': cur_frm.doc.mitgliedtyp_c,
                            'sektion': cur_frm.doc.sektion_id,
                            'jahr': r.message
                    },
                    callback: function(response)
                    {
                        if (response.message == 1) {
                            var txt = 'Die Rechnung des entsprechenden Jahres wurde bereits erstellt.<br>Wenn Sie diese neu erstellen möchten, müssen Sie die existierende zuerst stornieren.<br><br>';
                            txt += 'Alternativ können Sie eine Rechnung für das Jahr ' + r.message + ' erstellen.</p>'
                            
                            frappe.prompt([
                                {'fieldname': 'txt', 'fieldtype': 'HTML', 'options': txt}  
                            ],
                            function(values){
                                erstelle_folgejahr_rechnung(frm, r.message)
                            },
                            'Rechnungserstellung',
                            'Erstelle Rechnung für ' + r.message
                            )
                        } else {
                            frappe.msgprint("Es wurde bereits für das aktuelle Jahr sowie das Folgejahr eine Rechnung erstellt.");
                        }
                    }
                });
            }
        }
    });
}

function erstelle_folgejahr_rechnung(frm, jahr) {
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
            frappe.call({
                'method': "frappe.client.get",
                'args': {
                    'doctype': "MVD Settings",
                    'name': "MVD Settings"
                },
                'callback': function(settings_response) {
                    var settings = settings_response.message;
                    frappe.prompt([
                        {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage',
                            'get_query': function() {
                                return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                            }
                        },
                        {'fieldname': 'bar_bezahlt', 'fieldtype': 'Check', 'label': 'Barzahlung', 'reqd': 0, 'default': 0, 'hidden': cur_frm.doc.status_c != 'Online-Anmeldung' ? 0:1},
                        {'fieldname': 'hv_bar_bezahlt', 'fieldtype': 'Check', 'label': 'HV Barzahlung', 'reqd': 0, 'default': 0, 'depends_on': 'eval:doc.bar_bezahlt==1'},
                        {'fieldname': 'massendruck', 'fieldtype': 'Check', 'label': 'Für Massendruck vormerken', 'reqd': 0, 'default': 0},
                        {'fieldname': 'eigene_items', 'fieldtype': 'Check', 'label': 'Manuelle Artikel Auswahl', 'reqd': 0, 'default': 0, 'hidden': settings.manuelle_artikelauswahl ? 0:1},
                        {
                            label: "Rechnungs Artikel",
                            fieldname: "rechnungs_artikel", 
                            fieldtype: "Table", 
                            cannot_add_rows: false,
                            in_place_edit: false,
                            depends_on: 'eval:doc.eigene_items',
                            data: [],
                            get_data: () => {
                                return [];
                            },
                            fields: [
                            {
                                fieldtype:'Link',
                                fieldname:"item_code",
                                options: 'Item',
                                in_list_view: 1,
                                read_only: 0,
                                reqd: 1,
                                label: __('Item Code'),
                                change: function() {
                                    if (this.get_value()) {
                                        var rate_field = this.grid_row.on_grid_fields[1]
                                        frappe.call({
                                            method: "mvd.mvd.utils.manuelle_rechnungs_items.get_item_price",
                                            args:{
                                                    'item': this.get_value()
                                            },
                                            callback: function(r)
                                            {
                                                rate_field.set_value(r.message.price);
                                            }
                                        });
                                    }
                                }
                            },
                            {
                                fieldtype:'Currency',
                                fieldname:"rate",
                                in_list_view: 1,
                                read_only: 0,
                                label: __('Rate'),
                                reqd: 1
                            }]
                        }
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
                                    'massendruck': massendruck,
                                    'ignore_stichtage': true,
                                    'jahr': jahr,
                                    'eigene_items': values.eigene_items,
                                    'rechnungs_artikel': values.rechnungs_artikel
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
    });
}

function setze_read_only(frm) {
    var i = 0;
    for (i; i<cur_frm.fields.length; i++) {
        cur_frm.set_df_property(cur_frm.fields[i].df.fieldname,'read_only', 1);
    }
}

function erstelle_spenden_rechnung(frm) {
    if (frappe.user.has_role("MV_MA")) {
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
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
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
    // overwrite E-Mail BTN
    $("[data-label='Email']").parent().off("click");
    $("[data-label='Email']").parent().click(function(){frappe.mvd.new_mail(cur_frm);});
    $("[data-label='E-Mail']").parent().off("click");
    $("[data-label='E-Mail']").parent().click(function(){frappe.mvd.new_mail(cur_frm);});
    $(".btn.btn-default.btn-new-email.btn-xs").off("click");
    $(".btn.btn-default.btn-new-email.btn-xs").click(function(){frappe.mvd.new_mail(cur_frm);});
    $("[data-communication-type='Communication']").off("click");
    $(".reply-link").off("click");
    $(".reply-link").click(function(e){prepare_mvd_mail_composer(e);}); 
    $(".reply-link-all").click(function(e){prepare_mvd_mail_composer(e);});
    frappe.ui.keys.off('ctrl+e', cur_frm.page);
}

function erstelle_hv_rechnung(frm) {
    if (frappe.user.has_role("MV_MA")) {
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
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function erstelle_korrespondenz(frm) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.call({
            method: "mvd.mvd.doctype.druckvorlage.druckvorlage.get_druckvorlagen",
            args:{
                    'sektion': cur_frm.doc.sektion_id,
                    'dokument': 'Korrespondenz',
                    //'mitgliedtyp': cur_frm.doc.mitgliedtyp_c,
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
                        method: "mvd.mvd.doctype.mitgliedschaft.utils.create_korrespondenz",
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
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function erstelle_geschenk_korrespondenz(frm) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.call({
            method: "mvd.mvd.doctype.druckvorlage.druckvorlage.get_druckvorlagen",
            args:{
                    'sektion': cur_frm.doc.sektion_id,
                    'dokument': 'Geschenkmitgliedschaft',
                    'language': cur_frm.doc.language
            },
            async: false,
            callback: function(res)
            {
                var druckvorlagen = res.message;
                if (cur_frm.doc.geschenkunterlagen_an_schenker) {
                    frappe.prompt([
                        {'fieldname': 'druckvorlage_inhaber', 'fieldtype': 'Link', 'label': 'Druckvorlage Beschenkte*r', 'reqd': 1, 'options': 'Druckvorlage',
                            'get_query': function() {
                                return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                            }
                        },
                        {'fieldname': 'druckvorlage_zahler', 'fieldtype': 'Link', 'label': 'Druckvorlage Schenkende*r', 'reqd': 1, 'options': 'Druckvorlage',
                            'get_query': function() {
                                return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                            }
                        }
                    ],
                    function(values){
                        frappe.call({
                            method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.create_geschenk_korrespondenz",
                            args:{
                                    'mitgliedschaft': cur_frm.doc.name,
                                    'druckvorlage_inhaber': values.druckvorlage_inhaber,
                                    'druckvorlage_zahler': values.druckvorlage_zahler
                            },
                            freeze: true,
                            freeze_message: 'Erstelle Geschenk-Korrespondenz...',
                            callback: function(r)
                            {
                                frappe.msgprint("Die Geschenk-Korrespondenzen wurden erstellt und bei den Korrespondenzen abgelegt.");
                                cur_frm.reload_doc();
                            }
                        });
                    },
                    'Geschenk-Korrespondenz Erstellung',
                    'Erstellen'
                    )
                } else {
                    frappe.prompt([
                        {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage Beschenkte*r', 'reqd': 1, 'options': 'Druckvorlage',
                            'get_query': function() {
                                return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                            }
                        }
                    ],
                    function(values){
                        frappe.call({
                            method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.create_geschenk_korrespondenz",
                            args:{
                                    'mitgliedschaft': cur_frm.doc.name,
                                    'druckvorlage_inhaber': values.druckvorlage
                            },
                            freeze: true,
                            freeze_message: 'Erstelle Geschenk-Korrespondenz...',
                            callback: function(r)
                            {
                                frappe.msgprint("Die Geschenk-Korrespondenz wurde erstellt und bei den Korrespondenzen abgelegt.");
                                cur_frm.reload_doc();
                            }
                        });
                    },
                    'Geschenk-Korrespondenz Erstellung',
                    'Erstellen'
                    )
                }
            }
        });
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
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
                {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage',
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
                            'mitgliedschaft': cur_frm.doc.name,
                            'druckvorlage': druckvorlage,
                            'titel': values.titel
                    },
                    freeze: true,
                    freeze_message: 'Erstelle Korrespondenz...',
                    callback: function(r)
                    {
                        console.log(r.message)
                        frappe.confirm(
                            'Möchten Sie den Druck des Begrüssungsdokument für den Massenlauf vormerken?',
                            function(){
                                // on yes
                                cur_frm.set_value("begruessung_massendruck", '1');
                                cur_frm.set_value("begruessung_massendruck_dokument", r.message);
                                cur_frm.set_value("validierung_notwendig", '0');
                                cur_frm.set_value("status_c", 'Regulär');
                                cur_frm.save().then(function(){
                                    frappe.msgprint("Die Daten wurden als validert bestätigt und der Druck des Begrüssungsdokument für den Massenlauf vorgemerkt.");
                                });
                            },
                            function(){
                                // on no
                                cur_frm.set_value("validierung_notwendig", '0');
                                cur_frm.set_value("status_c", 'Regulär');
                                cur_frm.save().then(function(){
                                    frappe.msgprint("Die Daten wurden als validert bestätigt, das erstellte Begrüssungsdokument finden Sie unter Korrespondenz.");
                                });
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
        cur_frm.set_value("status_c", 'Regulär');
        cur_frm.save();
    }
}

function erstelle_todo(frm) {
    if (frappe.user.has_role("MV_MA")||frappe.user.has_role("MV_RB")) {
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
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function mitglied_inaktivieren(frm) {
    frappe.confirm(
        'Haben Sie alle Rechnungen und Fakultativen Rechnungen storniert und möchten das Mitglied wirklich <b>inaktivieren</b>?',
        function(){
            // on yes
            cur_frm.set_value("validierung_notwendig", '0');
            cur_frm.set_value("kuendigung_verarbeiten", '0');
            cur_frm.set_value("interessent_innenbrief_mit_ez", '0');
            cur_frm.set_value("anmeldung_mit_ez", '0');
            cur_frm.set_value("zuzug_massendruck", '0');
            cur_frm.set_value("rg_massendruck_vormerkung", '0');
            cur_frm.set_value("begruessung_massendruck", '0');
            cur_frm.set_value("begruessung_via_zahlung", '0');
            cur_frm.set_value("zuzugs_rechnung", '');
            cur_frm.set_value("zuzug_korrespondenz", '');
            cur_frm.set_value("kuendigung_druckvorlage", '');
            cur_frm.set_value("rg_massendruck", '');
            cur_frm.set_value("begruessung_massendruck_dokument", '');
            cur_frm.set_value("letzte_bearbeitung_von", 'User');
            var status_change_log = cur_frm.add_child('status_change');
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'datum', frappe.datetime.get_today());
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_alt', cur_frm.doc.status_c);
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_neu', 'Inaktiv');
            frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'grund', 'Manuelle Inaktivierung');
            cur_frm.refresh_field('status_change');
            cur_frm.set_value("status_c", 'Inaktiv');
            cur_frm.set_value("austritt", frappe.datetime.get_today());
            cur_frm.save().then(function(){
                frappe.msgprint("Das Mitglied wurde inaktiviert.");
            });
        },
        function(){
            // on no
        }
    )
}

function wieder_beitritt(frm) {
    frappe.confirm(
        'Möchten Sie das inaktivierte Mitglied in eine <b>Neu Anmeldung</b> umwandeln?',
        function(){
            // on yes
            frappe.call({
                "method": "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.wieder_beitritt",
                "args": {
                    "mitgliedschaft": cur_frm.doc.name
                },
                "callback": function(response) {
                    frappe.set_route("Form", "Mitgliedschaft", response.message);
                }
            });
        },
        function(){
            // on no
        }
    )
}

function is_valid_phone(number) {
    var regex = /[^+0123456789 ]/g
    if (regex.test(number)) {
        frappe.msgprint({
            title: __('Unzulässiges Format'),
            indicator: 'red',
            message: __('Die erfasste Telefonnummer ist <b>nicht</b> zulässig.<br>Zulässige Inhalte sind:<ul><li>+</li><li>Leerschlag</li><li>Zahlen von 0-9</li></ul>')
        });
    }
}

function mitglied_name_anzeigen(frm) {
    var data = cur_frm.doc.mitglied_nr + "&nbsp;&nbsp;&nbsp;";
    if (cur_frm.doc.firma) {
        data += cur_frm.doc.firma + ', ';
    }
    data += cur_frm.doc.vorname_1 + " " + cur_frm.doc.nachname_1;
    $(".ellipsis.title-text").html(data);
}

function status_historie_ergaenzen(frm) {
    frappe.prompt([
        {'fieldname': 'status_alt', 'fieldtype': 'Select', 'label': 'Status alt', 'reqd': 1, 'options': 'Regulär\nRegulär &dagger;\nAnmeldung\nOnline-Anmeldung\nOnline-Beitritt\nOnline-Kündigung\nOnline-Mutation\nZuzug\nGestorben\nKündigung\nWegzug\nAusschluss\nInaktiv\nInteressent*in'},
        {'fieldname': 'status_neu', 'fieldtype': 'Select', 'label': 'Status neu', 'reqd': 1, 'options': 'Regulär\nRegulär &dagger;\nAnmeldung\nOnline-Anmeldung\nOnline-Beitritt\nOnline-Kündigung\nOnline-Mutation\nZuzug\nGestorben\nKündigung\nWegzug\nAusschluss\nInaktiv\nInteressent*in'},
        {'fieldname': 'grund', 'fieldtype': 'Data', 'label': 'Grund', 'reqd': 1},
        {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Datum', 'reqd': 1, 'default': frappe.datetime.get_today()}
    ],
    function(values){
        show_alert(values, 5);
        var status_change_log = cur_frm.add_child('status_change');
        frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'datum', values.datum);
        frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_alt', values.status_alt);
        frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_neu', values.status_neu);
        frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'grund', values.grund);
        cur_frm.refresh_field('status_change');
        cur_frm.save();
    },
    'Status Historie Ergänzung',
    'Hinzufügen'
    )
}

function dirty_observer(frm) {
    $(cur_frm.wrapper).on("dirty", function() {
       if (cur_frm.is_dirty()) {
           $(".page-head.flex.align-center").css("background-color", "orange");
       }
   });
   if (!cur_frm.is_dirty()) {
       $(".page-head.flex.align-center").css("background-color", '#fff');
   }
}

function mitglied_reaktivieren(frm) {
    frappe.confirm(
        'Mitglieder sollten nur reaktiviert werden, wenn die Beiträge lückenlos bezahlt wurden. Bei Bedarf müssen fehlende Rechnungen revisioniert und nach der Reaktivierung nochmals gestellt bzw. gebucht werden.',
        function(){
            // on yes
            frappe.prompt([
                {'fieldname': 'grund', 'fieldtype': 'Data', 'label': 'Reaktivierungs Grund', 'reqd': 1}  
            ],
            function(values){
                cur_frm.set_value("austritt", '');
                cur_frm.set_value("kuendigung", '');
                
                var status_change_log = cur_frm.add_child('status_change');
                frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'datum', frappe.datetime.get_today());
                frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_alt', 'Inaktiv');
                frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'status_neu', 'Regulär');
                frappe.model.set_value(status_change_log.doctype, status_change_log.name, 'grund', values.grund);
                cur_frm.refresh_field('status_change');
                
                cur_frm.set_value("status_c", 'Regulär');
                cur_frm.set_value("letzte_bearbeitung_von", 'User');
                
                cur_frm.save();
            },
            'Manuelle Reaktivierung',
            'Reaktivieren'
            )

        },
        function(){
            // on no
        }
    )
}

function erstelle_rechnung_sonstiges(frm) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.call({
            method: "mvd.mvd.doctype.druckvorlage.druckvorlage.get_druckvorlagen",
            args:{
                    'sektion': cur_frm.doc.sektion_id,
                    'dokument': 'Rechnung (Sonstiges)',
                    'language': cur_frm.doc.language
            },
            async: false,
            callback: function(r)
            {
                var druckvorlagen = r.message
                frappe.call({
                    'method': "frappe.client.get",
                    'args': {
                        'doctype': "MVD Settings",
                        'name': "MVD Settings"
                    },
                    'callback': function(settings_response) {
                        var settings = settings_response.message;
                        frappe.prompt([
                            {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage',
                                'get_query': function() {
                                    return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                                }
                            },
                            {'fieldname': 'bar_bezahlt', 'fieldtype': 'Check', 'label': 'Barzahlung', 'reqd': 0, 'default': 0, 'hidden': 0},
                            {'fieldname': 'ohne_betrag', 'fieldtype': 'Check', 'label': 'Betrag ausblenden', 'reqd': 0, 'default': 0, 'hidden': 0},
                            {'fieldname': 'eigene_items', 'fieldtype': 'Check', 'label': 'Manuelle Artikel Auswahl', 'reqd': 0, 'default': 1, 'read_only': 1},
                            {'fieldname': 'ignore_pricing_rule', 'fieldtype': 'Check', 'label': 'Preisregeln ignorieren', 'reqd': 0, 'default': 0, 'read_only': 0},
                            {
                                label: "Rechnungs Artikel",
                                fieldname: "rechnungs_artikel", 
                                fieldtype: "Table", 
                                description: 'Die Preise der untenstehenden Tabelle werden nur im Zusammenhang mit "Preisregel ignorieren" verwendet.',
                                cannot_add_rows: false,
                                in_place_edit: false,
                                reqd: 1,
                                data: [],
                                get_data: () => {
                                    return [];
                                },
                                fields: [
                                {
                                    fieldtype:'Link',
                                    fieldname:"item_code",
                                    options: 'Item',
                                    in_list_view: 1,
                                    read_only: 0,
                                    reqd: 1,
                                    label: __('Item Code'),
                                    change: function() {
                                        if (this.get_value()) {
                                            if (this.section) {
                                                var rate_field = this.section.fields_dict.rate;
                                                var qty_field = this.section.fields_dict.qty;
                                                var description_field = this.section.fields_dict.description;
                                            } else {
                                                var rate_field = this.grid_row.on_grid_fields[2];
                                                var qty_field = this.grid_row.on_grid_fields[1];
                                                var description_field = this.grid_row.on_grid_fields[3];
                                            }
                                            frappe.call({
                                                method: "mvd.mvd.utils.manuelle_rechnungs_items.get_item_price",
                                                args:{
                                                        'item': this.get_value()
                                                },
                                                callback: function(r)
                                                {
                                                    rate_field.set_value(r.message.price);
                                                    description_field.set_value(r.message.description);
                                                    qty_field.set_value(1);
                                                }
                                            });
                                        }
                                    },
                                    get_query: function() {
                                        return { 'filters': { 'mitgliedschaftsspezifischer_artikel': 0 } };
                                    }
                                },
                                {
                                    fieldtype:'Int',
                                    fieldname:"qty",
                                    in_list_view: 1,
                                    read_only: 0,
                                    label: __('Qty'),
                                    reqd: 1
                                },
                                {
                                    fieldtype:'Currency',
                                    fieldname:"rate",
                                    in_list_view: 1,
                                    read_only: 0,
                                    label: __('Rate'),
                                    reqd: 1
                                },
                                {
                                    fieldtype:'Text Editor',
                                    fieldname:"description",
                                    in_list_view: 1,
                                    read_only: 0,
                                    label: __('Description'),
                                    reqd: 0
                                }]
                            }
                        ],
                        function(values){
                            if (values.bar_bezahlt == 1) {
                                var bar_bezahlt = true;
                            } else {
                                var bar_bezahlt = null;
                            }
                            
                            if (values.ohne_betrag == 1) {
                                var ohne_betrag = true;
                            } else {
                                var ohne_betrag = null;
                            }
                            
                            if (values.ignore_pricing_rule == 1) {
                                var ignore_pricing_rule = true;
                            } else {
                                var ignore_pricing_rule = null;
                            }
                            frappe.call({
                                method: "mvd.mvd.utils.sonstige_rechnungen.create_rechnung_sonstiges",
                                args:{
                                        'sektion': cur_frm.doc.sektion_id,
                                        'mitgliedschaft': cur_frm.doc.name,
                                        'bezahlt': bar_bezahlt,
                                        'attach_as_pdf': true,
                                        'submit': true,
                                        'druckvorlage': values.druckvorlage,
                                        'rechnungs_artikel': values.rechnungs_artikel,
                                        'ohne_betrag': ohne_betrag,
                                        'ignore_pricing_rule': ignore_pricing_rule
                                },
                                freeze: true,
                                freeze_message: 'Erstelle Rechnung (Sonstiges)...',
                                callback: function(r)
                                {
                                    cur_frm.reload_doc();
                                    cur_frm.timeline.insert_comment("Rechnung (Sonstiges) " + r.message + " erstellt.");
                                    frappe.msgprint("Die Rechnung wurde erstellt, Sie finden sie in den Anhängen.");
                                }
                            });
                        },
                        'Rechnungs Erstellung (Sonstiges)',
                        'Erstellen'
                        )
                    }
                });
            }
        });
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function m_und_w_sperre_aufheben(frm) {
    if (cur_frm.is_dirty()) {
        frappe.msgprint("Bitte speichern Sie die Mitgliedschaft zuerst.");
    } else {
        cur_frm.set_value("retoure_in_folge", "0");
        cur_frm.set_df_property('m_und_w', 'read_only', 0);
        cur_frm.save().then(function(){
            frappe.msgprint("Sie können die Anzahl M+W nun manuell setzen.");
        });
    }
}

function sende_k_best_email(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_kuendigungsmail_txt",
        args:{
                'mitgliedschaft': cur_frm.doc.name,
                'sektion_id': cur_frm.doc.sektion_id,
                'language': cur_frm.doc.language
        },
        callback: function(r)
        {
            if (r.message) {
                var mail_data = r.message;
                frappe.mvd.new_mail(cur_frm, '', mail_data);
            }
        }
    });
}

function erstellung_faktura_kunde(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.erstellung_faktura_kunde",
        args:{
                'mitgliedschaft': cur_frm.doc.name
        },
        freeze: true,
        freeze_message: 'Erstelle Faktura Kunde...',
        callback: function(r)
        {
            if (r.message) {
                frappe.set_route("Form", "Kunden", r.message);
            }
        }
    });
}

function erstelle_beratung(frm) {
    termin_quick_entry(frm);
}

function erstelle_beratung_only(frm) {
    var kwargs = {
        'beratung_only': 1,
        'termin_block_data': '',
        'art': '',
        'ort':'',
        'berater_in': '',
        'telefonnummer': '',
        'notiz': '',
        'mitgliedschaft': cur_frm.doc.name
    }
    frappe.call({
        method: "mvd.mvd.doctype.beratung.beratung.create_neue_beratung",
        args: kwargs,
        freeze: true,
        freeze_message: 'Erstelle Beratung...',
        callback: function(r)
        {
            if (r.message) {
                frappe.set_route("Form", "Beratung", r.message);
            }
        }
    });
}

function termin_quick_entry(frm) {
    localStorage.setItem('selected_termine', '');
    frappe.call({
        'method': "mvd.mvd.doctype.beratung.beratung.get_beratungsorte",
        'args': {
            'sektion': cur_frm.doc.sektion_id
        },
        'callback': function(r) {
            var orte = " \n" + r.message.ort_string;
            var default_von = frappe.datetime.nowdate();
            frappe.call({
                method: "mvd.mvd.doctype.arbeitsplan_beratung.arbeitsplan_beratung.zeige_verfuegbarkeiten",
                args:{
                    'sektion': cur_frm.doc.sektion_id,
                    'datum': frappe.datetime.nowdate(),
                    'marked': ''
                },
                callback: function(verfuegbarkeiten) {
                    var verfuegbarkeiten_html = '<p>Leider sind <b>keine</b> Berater*in verfügbar</p>';
                    if (verfuegbarkeiten.message) {
                        verfuegbarkeiten_html = verfuegbarkeiten.message;
                    }
                    var tel = cur_frm.doc.tel_m_1 || cur_frm.doc.tel_p_1 || cur_frm.doc.tel_g_1 || '';
                    var defaultArt = cur_frm.doc.sektion_id == 'MVBE' ? 'telefonisch' : 'persönlich';
                    var d = new frappe.ui.Dialog({
                        'title': __('Termin erstellen'),
                        'fields': [
                            {'fieldname': 'beratung', 'fieldtype': 'Link', 'label': __('Für Beratung'), 'options': 'Beratung', 'reqd': 0, 'hidden': 1,
                                'get_query': function() {
                                    return {
                                        filters: {
                                            'mv_mitgliedschaft': cur_frm.doc.name
                                        }
                                    }
                                }
                            },
                            {'fieldname': 'neue_beratung', 'fieldtype': 'Check', 'label': __('Erstelle neue Beratung'), 'default': 1,
                                'change': function() {
                                    if (d.get_value('neue_beratung') == 1) {
                                        d.set_df_property('beratung', 'reqd', 0);
                                        d.set_df_property('beratung', 'hidden', 1);
                                    } else {
                                        d.set_df_property('beratung', 'reqd', 1);
                                        d.set_df_property('beratung', 'hidden', 0);
                                    }
                                }
                            },
                            {'fieldname': 'ort', 'fieldtype': 'Select', 'label': __('Ort'), 'options': orte, 'reqd': 1, 'default': '',
                                'change': function() {
                                    // aktualisierung verfügbarkeiten
                                    frappe.call({
                                        method: "mvd.mvd.doctype.arbeitsplan_beratung.arbeitsplan_beratung.zeige_verfuegbarkeiten",
                                        args:{
                                            'sektion': cur_frm.doc.sektion_id,
                                            'datum': d.get_value('von'),
                                            'beraterin': d.get_value('kontaktperson')||'',
                                            'ort': d.get_value('ort')||'',
                                            'marked': localStorage.getItem('selected_termine'),
                                            'short_results': d.get_value('short_results'),
                                            'art': d.get_value('art')||''
                                        },
                                        callback: function(r) {
                                            if (r.message) {
                                                // anzeigen der Verfügbarkeiten
                                                d.set_df_property('verfuegbarkeiten_html', 'options', r.message);
                                            } else {
                                                // keine freien Beratungspersonen
                                                d.set_df_property('verfuegbarkeiten_html', 'options', '<p>Leider sind <b>keine</b> Berater*in verfügbar</p>');
                                            }
                                        }
                                    });
                                }
                            },
                            {'fieldname': 'art', 'fieldtype': 'Select', 'label': __('Art'), 'options': 'telefonisch\npersönlich', 'reqd': 1, 'default': defaultArt, 
                                'change': function() {
                                    if (d.get_value('art') == 'telefonisch') {
                                        d.set_df_property('telefonnummer', 'reqd', 1);
                                    } else {
                                        d.set_df_property('telefonnummer', 'reqd', 0);
                                    }
                                    // aktualisierung verfügbarkeiten
                                    frappe.call({
                                        method: "mvd.mvd.doctype.arbeitsplan_beratung.arbeitsplan_beratung.zeige_verfuegbarkeiten",
                                        args:{
                                            'sektion': cur_frm.doc.sektion_id,
                                            'datum': d.get_value('von'),
                                            'beraterin': d.get_value('kontaktperson')||'',
                                            'ort': d.get_value('ort')||'',
                                            'marked': localStorage.getItem('selected_termine'),
                                            'short_results': d.get_value('short_results'),
                                            'art': d.get_value('art')||''
                                        },
                                        callback: function(r) {
                                            if (r.message) {
                                                // anzeigen der Verfügbarkeiten
                                                d.set_df_property('verfuegbarkeiten_html', 'options', r.message);
                                            } else {
                                                // keine freien Beratungspersonen
                                                d.set_df_property('verfuegbarkeiten_html', 'options', '<p>Leider sind <b>keine</b> Berater*in verfügbar</p>');
                                            }
                                        }
                                    });
                                }
                            },
                            {'fieldname': 'telefonnummer', 'fieldtype': 'Data', 'label': __('Telefonnummer'), 'default': tel, 'reqd': 1},
                            {'fieldname': 'von', 'fieldtype': 'Date', 'label': __('Datum'), 'reqd': 1, 'default': default_von, 'description': '"Datum" ist relevant für die Anzeige der Verfügbarkeiten. Es wird immer in dessen Zukunft geblickt.',
                                'change': function() {
                                    // aktualisierung verfügbarkeiten
                                    frappe.call({
                                        method: "mvd.mvd.doctype.arbeitsplan_beratung.arbeitsplan_beratung.zeige_verfuegbarkeiten",
                                        args:{
                                            'sektion': cur_frm.doc.sektion_id,
                                            'datum': d.get_value('von'),
                                            'beraterin': d.get_value('kontaktperson')||'',
                                            'ort': d.get_value('ort')||'',
                                            'marked': localStorage.getItem('selected_termine'),
                                            'short_results': d.get_value('short_results'),
                                            'art': d.get_value('art')||''
                                        },
                                        callback: function(r) {
                                            if (r.message) {
                                                // anzeigen der Verfügbarkeiten
                                                d.set_df_property('verfuegbarkeiten_html', 'options', r.message);
                                            } else {
                                                // keine freien Beratungspersonen
                                                d.set_df_property('verfuegbarkeiten_html', 'options', '<p>Leider sind <b>keine</b> Berater*in verfügbar</p>');
                                            }
                                        }
                                    });
                                }
                            },
                            {'fieldname': 'short_results', 'fieldtype': 'Check', 'label': __('Zeige 14 Tage'), 'default': 1,
                                'change': function() {
                                    // aktualisierung verfügbarkeiten
                                    frappe.call({
                                        method: "mvd.mvd.doctype.arbeitsplan_beratung.arbeitsplan_beratung.zeige_verfuegbarkeiten",
                                        args:{
                                            'sektion': cur_frm.doc.sektion_id,
                                            'datum': d.get_value('von'),
                                            'beraterin': d.get_value('kontaktperson')||'',
                                            'ort': d.get_value('ort')||'',
                                            'marked': localStorage.getItem('selected_termine'),
                                            'short_results': d.get_value('short_results'),
                                            'art': d.get_value('art')||''
                                        },
                                        callback: function(r) {
                                            if (r.message) {
                                                // anzeigen der Verfügbarkeiten
                                                d.set_df_property('verfuegbarkeiten_html', 'options', r.message);
                                            } else {
                                                // keine freien Beratungspersonen
                                                d.set_df_property('verfuegbarkeiten_html', 'options', '<p>Leider sind <b>keine</b> Berater*in verfügbar</p>');
                                            }
                                        }
                                    });
                                }
                            },
                            {'fieldname': 'kontaktperson', 'fieldtype': 'Link', 'label': __('Berater*in'), 'options': 'Termin Kontaktperson', 'reqd': 1,
                                'get_query': function() {
                                    return {
                                        filters: {
                                            'sektion_id': cur_frm.doc.sektion_id
                                        }
                                    }
                                },
                                'change': function() {
                                    if (d.get_value('kontaktperson')) {
                                        frappe.call({
                                            method: "mvd.mvd.doctype.beratung.beratung.get_beratungsorte",
                                            args:{
                                                'sektion': cur_frm.doc.sektion_id,
                                                'kontakt': d.get_value('kontaktperson')
                                            },
                                            callback: function(r) {
                                                if (r.message) {
                                                    // hinterlegen von Orten auf Basis Kontakt
                                                    var orte_kontaktbasis = " \n" + r.message.ort_string;
                                                    if ((d.get_value('ort'))&&(d.get_value('ort') != ' ')&&(!orte_kontaktbasis.includes(d.get_value('ort')))) {
                                                        d.set_value('ort', '');
                                                    }
                                                    d.set_df_property('ort', 'options', orte_kontaktbasis);
                                                } else {
                                                    // Keine Orte zu Kontakt
                                                    d.set_value('ort', '');
                                                    d.set_df_property('ort', 'options', '');
                                                }

                                                // aktualisierung verfügbarkeiten
                                                frappe.call({
                                                    method: "mvd.mvd.doctype.arbeitsplan_beratung.arbeitsplan_beratung.zeige_verfuegbarkeiten",
                                                    args:{
                                                        'sektion': cur_frm.doc.sektion_id,
                                                        'datum': d.get_value('von'),
                                                        'beraterin': d.get_value('kontaktperson')||'',
                                                        'ort': d.get_value('ort')||'',
                                                        'marked': localStorage.getItem('selected_termine'),
                                                        'short_results': d.get_value('short_results'),
                                                        'art': d.get_value('art')||''
                                                    },
                                                    callback: function(r) {
                                                        if (r.message) {
                                                            // anzeigen der Verfügbarkeiten
                                                            d.set_df_property('verfuegbarkeiten_html', 'options', r.message);
                                                        } else {
                                                            // keine freien Beratungspersonen
                                                            d.set_df_property('verfuegbarkeiten_html', 'options', '<p>Leider sind <b>keine</b> Berater*in verfügbar</p>');
                                                        }
                                                    }
                                                });
                                            }
                                        });
                                    } else {
                                        // reset to default
                                        d.set_df_property('ort', 'options', orte);
                                        // aktualisierung verfügbarkeiten
                                        frappe.call({
                                            method: "mvd.mvd.doctype.arbeitsplan_beratung.arbeitsplan_beratung.zeige_verfuegbarkeiten",
                                            args:{
                                                'sektion': cur_frm.doc.sektion_id,
                                                'datum': d.get_value('von'),
                                                'ort': d.get_value('ort')||'',
                                                'marked': localStorage.getItem('selected_termine'),
                                                'short_results': d.get_value('short_results'),
                                                'art': d.get_value('art')||''
                                            },
                                            callback: function(r) {
                                                if (r.message) {
                                                    // anzeigen der Verfügbarkeiten
                                                    d.set_df_property('verfuegbarkeiten_html', 'options', r.message);
                                                } else {
                                                    // keine freien Beratungspersonen
                                                    d.set_df_property('verfuegbarkeiten_html', 'options', '<p>Leider sind <b>keine</b> Berater*in verfügbar</p>');
                                                }
                                            }
                                        });
                                    }
                                }
                            },
                            {'fieldname': 'notiz', 'fieldtype': 'Text Editor', 'label': __('Notiz (Intern)')},
                            {'fieldname': 'verfuegbarkeiten_titel', 'fieldtype': 'HTML', 'options': '<h4>Berater*innen Verfügbarkeiten</h4>'},
                            {'fieldname': 'verfuegbarkeiten_html', 'fieldtype': 'HTML', 'label': '', 'options': verfuegbarkeiten_html}
                        ],
                        'primary_action': function() {
                            frappe.call({
                                method: "mvd.mvd.doctype.beratung.beratung.get_termin_block_data",
                                args:{
                                    'abp_zuweisungen': localStorage.getItem('selected_termine')
                                },
                                callback: function(r) {
                                    console.log(r.message)
                                    if (r.message) {
                                        var termin_block_data = r.message;
                                        d.hide();

                                        if (d.get_value('neue_beratung') == 1) {
                                            var kwargs = {
                                                'termin_block_data': termin_block_data,
                                                'art': d.get_value('art'),
                                                'ort': d.get_value('ort'),
                                                'berater_in': d.get_value('kontaktperson'),
                                                'telefonnummer': d.get_value('telefonnummer'),
                                                'notiz': d.get_value('notiz'),
                                                'mitgliedschaft': cur_frm.doc.name
                                            }
                                        } else {
                                            var kwargs = {
                                                'beratung': d.get_value('beratung'),
                                                'termin_block_data': termin_block_data,
                                                'art': d.get_value('art'),
                                                'ort': d.get_value('ort'),
                                                'berater_in': d.get_value('kontaktperson'),
                                                'telefonnummer': d.get_value('telefonnummer'),
                                                'notiz': d.get_value('notiz'),
                                                'mitgliedschaft': cur_frm.doc.name
                                            }
                                        }
                                        
                                        frappe.call({
                                            method: "mvd.mvd.doctype.beratung.beratung.create_neue_beratung",
                                            args: kwargs,
                                            freeze: true,
                                            freeze_message: d.get_value('neue_beratung') == 1 ? 'Erstelle Beratung und Termin...':'Erstelle Termin...',
                                            callback: function(r)
                                            {
                                                if (r.message) {
                                                    localStorage.setItem("trigger_termin_mail", "1");
                                                    localStorage.setItem("termin_block_data", JSON.stringify(termin_block_data));
                                                    localStorage.setItem("termin_block_art", d.get_value('art'));
                                                    localStorage.setItem("termin_block_ort", d.get_value('ort'));
                                                    localStorage.setItem("termin_block_tel", d.get_value('telefonnummer')||'');
                                                    localStorage.setItem("termin_block_berater_in", d.get_value('kontaktperson')||'');
                                                    
                                                    frappe.set_route("Form", "Beratung", r.message);
                                                }
                                            }
                                        });
                                    } else {
                                        frappe.msgprint("Ups, da ist etwas schief gelaufen.");
                                    }
                                }
                            });
                        },
                        'primary_action_label': __('Erstellen'),
                        'checkbox_clicked': function(cb) {
                            var termin = $(cb).data().abpzuweisung;
                            var ort = $(cb).data().ort;
                            if (!d.get_value('ort')) {
                                d.set_value('ort', ort)
                            }
                            var beratungsperson = $(cb).data().beratungsperson;
                            if (!d.get_value('kontaktperson')) {
                                d.set_value('kontaktperson', beratungsperson)
                            }
                            if (localStorage.getItem('selected_termine').includes(`-${termin}`)) {
                                localStorage.setItem('selected_termine', localStorage.getItem('selected_termine').replace(`-${termin}`, ''));
                                
                            } else {
                                var marks = localStorage.getItem('selected_termine')
                                localStorage.setItem('selected_termine', `${marks}-${termin}`);
                            }
                            if (localStorage.getItem('selected_termine').length > 0) {
                                d.set_df_property("ort", "read_only", 1);
                                d.set_df_property("kontaktperson", "read_only", 1);
                            } else {
                                d.set_df_property("ort", "read_only", 0);
                                d.set_df_property("kontaktperson", "read_only", 0);
                            }
                            
                        }
                    });
                    d.show();
                }
            });
        }
    });
}

function roundMinutes(date_string) {
    var date = new Date(date_string);
    date.setHours(date.getHours() + Math.round(date.getMinutes()/60));
    date.setMinutes(0, 0, 0);
    return date
}

function prepare_mvd_mail_composer(e, forward=false) {
    var last_email = null;
    var default_sender = frappe.boot.default_beratungs_sender || '';

    const $target = $(e.currentTarget);
    const name = $target.data().name ? $target.data().name:e.currentTarget.closest(".timeline-item").getAttribute("data-name");
    
    // find the email to reply to
    cur_frm.timeline.get_communications().forEach(function(c) {
        if(c.name == name) {
            last_email = c;
            return false;
        }
    });
    if (last_email.sender.includes(".mieterverband.ch")){
        last_email.sender = cur_frm.doc.e_mail_1 || '';
    }
    
    const opts = {
        doc: cur_frm.doc,
        txt: "",
        title: forward ? __('Forward'):__('Reply'),
        frm: cur_frm,
        sender: default_sender,
        last_email,
        is_a_reply: true,
        subject: forward ? __("Fw: {0}", [last_email.subject]):''
    };

    if ($target.is('.reply-link-all')) {
        if (last_email) {
            opts.cc = last_email.cc;
            opts.bcc = last_email.bcc;
        }
    }

    // make the composer
    new frappe.mvd.MailComposer(opts);
}

function check_for_running_job(frm) {
    frappe.call({
        method: "mvd.mvd.utils.check_for_running_job",
        args: {
            'jobname': `Aktualisiere Mitgliedschaft ${cur_frm.doc.name}`
        },
        callback: function(r)
        {
            if (r.message) {
                cur_frm.dashboard.add_comment(__('Bitte warten Sie einen Moment, es steht noch ein Update für dieses Mitglied an.<br>Aktualisieren Sie diese Seite in ein paar Minuten.'), 'red', true);
            }
        }
    });
}

function erfassung_vermieterkuendigung(frm) {
    let mietobjekt = '';
    if (cur_frm.doc.abweichende_objektadresse) {
        mietobjekt = `${cur_frm.doc.objekt_strasse || ''}${cur_frm.doc.objekt_hausnummer || ''}${cur_frm.doc.objekt_nummer_zu || ''}, ${cur_frm.doc.objekt_plz || ''} ${cur_frm.doc.objekt_ort || ''}`
    } else {
        mietobjekt = `${cur_frm.doc.strasse || ''} ${cur_frm.doc.nummer || ''}${cur_frm.doc.nummer_zu || ''}, ${cur_frm.doc.plz || ''} ${cur_frm.doc.ort || ''}`
    }
    frappe.prompt([
        {'fieldname': 'datum_kuendigung_per', 'fieldtype': 'Date', 'label': 'Kündigung per', 'reqd': 1},
        {'fieldname': 'mietobjekt', 'fieldtype': 'Data', 'label': 'Mietobjekt', 'reqd': 1, 'default': mietobjekt}
    ],
    function(values){
        let new_row = cur_frm.add_child("kuendigungen");
        frappe.model.set_value(new_row.doctype, new_row.name, 'datum_erfassung', frappe.datetime.nowdate());
        frappe.model.set_value(new_row.doctype, new_row.name, 'datum_kuendigung_per', values.datum_kuendigung_per);
        frappe.model.set_value(new_row.doctype, new_row.name, 'mietobjekt', values.mietobjekt);
        cur_frm.refresh_field("kuendigungen");
        cur_frm.save();
    },
    'Vermieterkündigung erfassen',
    'Erfassen'
    );
}