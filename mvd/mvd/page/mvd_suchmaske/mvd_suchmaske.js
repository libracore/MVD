frappe.pages['mvd-suchmaske'].on_page_load = function(wrapper) {
    var me = this;
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Mitgliedschaftssuche',
        single_column: true
    });
    //add_action_item
    me.$user_search_button = me.page.set_primary_action('Suche starten<span class="text-muted pull-right" style="padding-left: 5px;">Ctrl+S</span>', () => {
        frappe.mvd_such_client.suche(page);
    });
    me.$listenansicht_button = me.page.add_menu_item('Listenansicht zeigen<span class="text-muted pull-right">Ctrl+L</span>', () => {
        frappe.mvd_such_client.goto_list(page);
    });
    me.$reset_button = me.page.set_secondary_action('Suche zurücksetzen<span class="text-muted pull-right" style="padding-left: 5px;">Ctrl+R</span>', () => {
        location.reload();
    });
    //set_primary_action
    
    // trigger für ctrl + s
    frappe.ui.keys.on('ctrl+s', function(e) {
        var route = frappe.get_route();
        if(route[0]==='mvd-suchmaske') {
            me.$user_search_button.click();
            e.preventDefault();
            return false;
        }
    });
    // trigger für ctrl + l
    frappe.ui.keys.on('ctrl+l', function(e) {
        var route = frappe.get_route();
        if(route[0]==='mvd-suchmaske') {
            me.$listenansicht_button.click();
            e.preventDefault();
            return false;
        }
    });
    
    //erstelle suchabschnitt
    page.main.html(frappe.render_template("suchmaske", {}));
    
    //erstelle suchfelder
    me.search_fields = {};
    
    me.search_fields.sektion_id = frappe.mvd_such_client.create_sektion_id_field(page)
    me.search_fields.sektion_id.set_value(get_default_sektion());
    me.search_fields.sektion_id.refresh();
    
    me.search_fields.mitglied_nr = frappe.mvd_such_client.create_mitglied_nr_field(page)
    me.search_fields.mitglied_nr.refresh();
    
    me.search_fields.sektions_uebergreifend = frappe.mvd_such_client.create_sektions_uebergreifend_field(page, me.search_fields.sektion_id)
    me.search_fields.sektions_uebergreifend.refresh();
    
    me.search_fields.status_c = frappe.mvd_such_client.create_status_c_field(page)
    me.search_fields.status_c.refresh();
    
    me.search_fields.mitgliedtyp_c = frappe.mvd_such_client.create_mitgliedtyp_c_field(page)
    me.search_fields.mitgliedtyp_c.refresh();
    
    me.search_fields.vorname = frappe.mvd_such_client.create_vorname_field(page)
    me.search_fields.vorname.refresh();
    
    me.search_fields.nachname = frappe.mvd_such_client.create_nachname_field(page)
    me.search_fields.nachname.refresh();
    
    me.search_fields.tel = frappe.mvd_such_client.create_tel_field(page)
    me.search_fields.tel.refresh();
    
    me.search_fields.email = frappe.mvd_such_client.create_email_field(page)
    me.search_fields.email.refresh();
    
    me.search_fields.zusatz_adresse = frappe.mvd_such_client.create_zusatz_adresse_field(page)
    me.search_fields.zusatz_adresse.refresh();
    
    me.search_fields.nummer = frappe.mvd_such_client.create_nummer_field(page)
    me.search_fields.nummer.refresh();
    
    me.search_fields.nummer_zu = frappe.mvd_such_client.create_nummer_zu_field(page)
    me.search_fields.nummer_zu.refresh();
    
    me.search_fields.postfach_nummer = frappe.mvd_such_client.create_postfach_nummer_field(page)
    me.search_fields.postfach_nummer.refresh();
    
    me.search_fields.strasse = frappe.mvd_such_client.create_strasse_field(page)
    me.search_fields.strasse.refresh();
    
    me.search_fields.postfach = frappe.mvd_such_client.create_postfach_field(page, me.search_fields.postfach_nummer)
    me.search_fields.postfach.refresh();
    
    me.search_fields.plz = frappe.mvd_such_client.create_plz_field(page)
    me.search_fields.plz.refresh();
    
    me.search_fields.ort = frappe.mvd_such_client.create_ort_field(page)
    me.search_fields.ort.refresh();
    
    me.search_fields.firma = frappe.mvd_such_client.create_firma_field(page)
    me.search_fields.firma.refresh();
    
    me.search_fields.zusatz_firma = frappe.mvd_such_client.create_zusatz_firma_field(page)
    me.search_fields.zusatz_firma.refresh();
    
    me.search_fields.suchresultate = frappe.mvd_such_client.create_resultate_div(page)
    me.search_fields.suchresultate.refresh();
    
    me.search_fields.neuanlage = frappe.mvd_such_client.create_neuanlage_btn(page)
    me.search_fields.neuanlage.refresh();
}


frappe.mvd_such_client = {
    suche: function(page) {
        if (cur_page.page.search_fields.sektion_id.get_value()) {
            // normale suche
            frappe.mvd_such_client.start_suche(page)
        } else {
            if (cur_page.page.search_fields.sektions_uebergreifend.get_value() == 1) {
                // Freizügigkeitsabfrage
                if (cur_page.page.search_fields.mitglied_nr.get_value()) {
                    // auf basis mitglieder_nr
                    frappe.mvd_such_client.start_suche(page)
                } else {
                    if (cur_page.page.search_fields.nachname.get_value()&&cur_page.page.search_fields.strasse.get_value()&&(cur_page.page.search_fields.plz.get_value()||cur_page.page.search_fields.ort.get_value())) {
                        // kombination aus name & strasse & (plz und/oder ort)
                        frappe.mvd_such_client.start_suche(page)
                    } else {
                        // fehlende suchkriterien
                        frappe.msgprint("Freizügigkeitsabfragen können nur mit folgenden Suchkriterien getätigt werden:<br>- Angabe Mitgliedernummer<br>und/oder<br>- Kombination aus Nachname, Strasse und PLZ und/oder Ort", "Fehlende Suchkriterien");
                    }
                }
            } else {
                frappe.msgprint("Bitte mindestens eine Sektion angeben");
            }
        }
    },
    start_suche: function(page) {
        frappe.show_alert("Die Suche wurde gestartet, bitte warten...", 5);
        var search_data = {};
        for (const [ key, value ] of Object.entries(cur_page.page.search_fields)) {
            if (value.get_value()) {
                search_data[key] = value.get_value();
            } else {
                search_data[key] = false;
            }
        }
        frappe.call({
            method: "mvd.mvd.page.mvd_suchmaske.mvd_suchmaske.suche",
            args:{
                    'suchparameter': search_data
            },
            freeze: true,
            freeze_message: 'Suche nach Mitgliedschaften...',
            callback: function(r)
            {
                if (r.message) {
                    if (r.message != 'too many') {
                        cur_page.page.search_fields.suchresultate.set_value(r.message);
                        frappe.show_alert({message:"Die Suchresultate werden angezeigt.", indicator:'green'}, 5);
                    } else {
                        cur_page.page.search_fields.suchresultate.set_value("<center><p>Zu viele Suchresultate gefunden.<br>Die Freizügigkeitsabfrage ist auf ein Ergebnis limitiert.<br>Bitte geben sie mehr Suchkriterien ein</p></center>");
                        frappe.show_alert({message:"Zu viele Suchresultate gefunden.", indicator:'red'}, 5);
                    }
                } else {
                    cur_page.page.search_fields.suchresultate.set_value("<center><p>Keine Suchresultate vorhanden.</p></center>");
                    cur_page.page.search_fields.neuanlage.df.hidden = 0;
                    cur_page.page.search_fields.neuanlage.refresh();
                    frappe.show_alert({message:"Keine Suchresultate vorhanden.", indicator:'orange'}, 5);
                }
            }
        });
    },
    goto_list: function(page) {
        var search_data = {};
        for (const [ key, value ] of Object.entries(cur_page.page.search_fields)) {
            if (value.get_value()) {
                search_data[key] = value.get_value();
            } else {
                search_data[key] = false;
            }
        }
        frappe.call({
            method: "mvd.mvd.page.mvd_suchmaske.mvd_suchmaske.suche",
            args:{
                    'suchparameter': search_data,
                    'goto_list': true
            },
            freeze: true,
            freeze_message: 'Suche nach Mitgliedschaften...',
            callback: function(r)
            {
                if (r.message) {
                    frappe.route_options = {"mitglied_nr": ["in", r.message]}
                    frappe.set_route("List", "MV Mitgliedschaft");
                }
            }
        });
    },
    create_sektion_id_field: function(page) {
        var sektion_id = frappe.ui.form.make_control({
            parent: page.main.find(".sektion_id"),
            df: {
                fieldtype: "Link",
                options: "Sektion",
                fieldname: "sektion",
                placeholder: "Sektion",
                read_only: 0
            },
            only_input: true,
        });
        return sektion_id
    },
    create_mitglied_nr_field: function(page) {
        var mitglied_nr = frappe.ui.form.make_control({
            parent: page.main.find(".mitglied_nr"),
            df: {
                fieldtype: "Data",
                fieldname: "mitglied_nr",
                placeholder: "Mitglied Nr."
            },
            only_input: true,
        });
        return mitglied_nr
    },
    create_sektions_uebergreifend_field: function(page, sektion_id) {
        var sektions_uebergreifend = frappe.ui.form.make_control({
            parent: page.main.find(".sektions_uebergreifend"),
            df: {
                fieldtype: "Check",
                fieldname: "sektions_uebergreifend",
                change: function(){
                    if (sektions_uebergreifend.get_value() == 1) {
                        sektion_id.set_value('');
                        sektion_id.df.read_only = 1;
                        sektion_id.refresh();
                    } else {
                        sektion_id.set_value(get_default_sektion());
                        sektion_id.df.read_only = 0;
                        sektion_id.refresh();
                    }
                }
            },
            only_input: true,
        });
        return sektions_uebergreifend
    },
    create_status_c_field: function(page) {
        var status_c = frappe.ui.form.make_control({
            parent: page.main.find(".status_c"),
            df: {
                fieldtype: "Select",
                fieldname: "status_c",
                options: 'Regulär\nAnmeldung\nOnline-Anmeldung\nOnline-Beitritt\nZuzug\nGestorben\nKündigung\nWegzug\nAusschluss\nInaktiv\nInteressent*in',
                placeholder: "Status"
            },
            only_input: true,
        });
        return status_c
    },
    create_mitgliedtyp_c_field: function(page) {
        var mitgliedtyp_c = frappe.ui.form.make_control({
            parent: page.main.find(".mitgliedtyp_c"),
            df: {
                fieldtype: "Select",
                fieldname: "mitgliedtyp_c",
                options: 'Geschäftlich\nPrivat\nKollektiv',
                placeholder: "Mitgliedtyp"
            },
            only_input: true,
        });
        return mitgliedtyp_c
    },
    create_vorname_field: function(page) {
        var vorname = frappe.ui.form.make_control({
            parent: page.main.find(".vorname"),
            df: {
                fieldtype: "Data",
                fieldname: "vorname",
                placeholder: "Vorname"
            },
            only_input: true,
        });
        return vorname
    },
    create_nachname_field: function(page) {
        var nachname = frappe.ui.form.make_control({
            parent: page.main.find(".nachname"),
            df: {
                fieldtype: "Data",
                fieldname: "nachname",
                placeholder: "Nachname"
            },
            only_input: true,
        });
        return nachname
    },
    create_tel_field: function(page) {
        var tel = frappe.ui.form.make_control({
            parent: page.main.find(".tel"),
            df: {
                fieldtype: "Data",
                fieldname: "tel",
                placeholder: "Telefon"
            },
            only_input: true,
        });
        return tel
    },
    create_email_field: function(page) {
        var email = frappe.ui.form.make_control({
            parent: page.main.find(".email"),
            df: {
                fieldtype: "Data",
                options: 'Email',
                fieldname: "email",
                placeholder: "E-Mail"
            },
            only_input: true,
        });
        return email
    },
    create_zusatz_adresse_field: function(page) {
        var zusatz_adresse = frappe.ui.form.make_control({
            parent: page.main.find(".zusatz_adresse"),
            df: {
                fieldtype: "Data",
                fieldname: "zusatz_adresse",
                placeholder: "Zusatz Adresse"
            },
            only_input: true,
        });
        return zusatz_adresse
    },
    create_strasse_field: function(page) {
        var strasse = frappe.ui.form.make_control({
            parent: page.main.find(".strasse"),
            df: {
                fieldtype: "Data",
                fieldname: "strasse",
                hidden: 0,
                placeholder: "Strasse"
            },
            only_input: true,
        });
        return strasse
    },
    create_nummer_field: function(page) {
        var nummer = frappe.ui.form.make_control({
            parent: page.main.find(".nummer"),
            df: {
                fieldtype: "Data",
                fieldname: "nummer",
                hidden: 0,
                placeholder: "Nummer"
            },
            only_input: true,
        });
        return nummer
    },
    create_nummer_zu_field: function(page) {
        var nummer_zu = frappe.ui.form.make_control({
            parent: page.main.find(".nummer_zu"),
            df: {
                fieldtype: "Data",
                fieldname: "nummer_zu",
                hidden: 0,
                placeholder: "Nr. Zusatz"
            },
            only_input: true,
        });
        return nummer_zu
    },
    create_postfach_field: function(page, postfach_nummer) {
        var postfach = frappe.ui.form.make_control({
            parent: page.main.find(".postfach"),
            df: {
                fieldtype: "Check",
                fieldname: "postfach",
                change: function(){
                    if (postfach.get_value() == 1) {
                        postfach_nummer.df.hidden = 0;
                        postfach_nummer.refresh();
                    } else {
                        postfach_nummer.df.hidden = 1;
                        postfach_nummer.refresh();
                    }
                }
            },
            only_input: true,
        });
        return postfach
    },
    create_postfach_nummer_field: function(page) {
        var postfach_nummer = frappe.ui.form.make_control({
            parent: page.main.find(".postfach_nummer"),
            df: {
                fieldtype: "Data",
                fieldname: "postfach_nummer",
                hidden: 1,
                placeholder: "Postfach Nummer"
            },
            only_input: true,
        });
        return postfach_nummer
    },
    create_plz_field: function(page) {
        var plz = frappe.ui.form.make_control({
            parent: page.main.find(".plz"),
            df: {
                fieldtype: "Data",
                fieldname: "plz",
                placeholder: "PLZ"
            },
            only_input: true,
        });
        return plz
    },
    create_ort_field: function(page) {
        var ort = frappe.ui.form.make_control({
            parent: page.main.find(".ort"),
            df: {
                fieldtype: "Data",
                fieldname: "ort",
                placeholder: "Ort"
            },
            only_input: true,
        });
        return ort
    },
    create_firma_field: function(page) {
        var ort = frappe.ui.form.make_control({
            parent: page.main.find(".firma"),
            df: {
                fieldtype: "Data",
                fieldname: "firma",
                placeholder: "Firma"
            },
            only_input: true,
        });
        return ort
    },
    create_zusatz_firma_field: function(page) {
        var ort = frappe.ui.form.make_control({
            parent: page.main.find(".zusatz_firma"),
            df: {
                fieldtype: "Data",
                fieldname: "zusatz_firma",
                placeholder: "Zusatz Firma"
            },
            only_input: true,
        });
        return ort
    },
    create_resultate_div: function(page) {
        var suchresultate = frappe.ui.form.make_control({
            parent: page.main.find(".suchresultate"),
            df: {
                fieldtype: "HTML",
                fieldname: "suchresultate",
                options: ''
            },
            only_input: true,
        });
        return suchresultate
    },
    create_neuanlage_btn: function(page) {
        var neuanlage = frappe.ui.form.make_control({
            parent: page.main.find(".neuanlage"),
            df: {
                fieldtype: "Button",
                fieldname: "neuanlage",
                label: "Neuanlage",
                hidden: 1,
                click: function(){
                    frappe.prompt([
                        {'fieldname': 'status', 'fieldtype': 'Select', 'label': 'Status', 'reqd': 1, 'options': 'Interessent*in\nRegulär', 'default': 'Regulär'},
                        {'fieldname': 'mitgliedtyp', 'fieldtype': 'Select', 'label': 'Mitgliedtyp', 'reqd': 1, 'options': 'Privat\nGeschäft', 'default': 'Privat', 'change': function() {
                                if (cur_dialog.fields_dict.mitgliedtyp.get_value() == 'Privat') {
                                    cur_dialog.fields_dict.firma.df.reqd = 0;
                                    cur_dialog.fields_dict.firma.df.hidden = 1;
                                    cur_dialog.fields_dict.firma.refresh();
                                    cur_dialog.fields_dict.zusatz_firma.df.reqd = 0;
                                    cur_dialog.fields_dict.zusatz_firma.df.hidden = 1;
                                    cur_dialog.fields_dict.zusatz_firma.refresh();
                                } else {
                                    cur_dialog.fields_dict.firma.df.reqd = 1;
                                    cur_dialog.fields_dict.firma.df.hidden = 0;
                                    cur_dialog.fields_dict.firma.refresh();
                                    cur_dialog.fields_dict.zusatz_firma.df.reqd = 1;
                                    cur_dialog.fields_dict.zusatz_firma.df.hidden = 0;
                                    cur_dialog.fields_dict.zusatz_firma.refresh();
                                }
                            }
                        },
                        {'fieldname': 'sektion_id', 'fieldtype': 'Link', 'label': 'Sektion', 'reqd': 1, 'hidden': 1, 'options': 'Sektion', 'default': cur_page.page.search_fields.sektion_id.get_value()},
                        {'fieldname': 'autom_rechnung', 'fieldtype': 'Check', 'label': 'Rechnung autom. erzeugen', 'reqd': 0, 'default': 1},
                        {'fieldname': 'bar_bezahlt', 'fieldtype': 'Check', 'label': 'Barzahlung', 'reqd': 0, 'default': 0, 'depends_on': 'eval:doc.autom_rechnung'},
                        {'fieldname': 'hv_bar_bezahlt', 'fieldtype': 'Check', 'label': 'HV Barzahlung', 'reqd': 0, 'default': 0, 'depends_on': 'eval:doc.bar_bezahlt'},
                        {'fieldname': 's1', 'fieldtype': 'Section Break'},
                        {'fieldname': 'firma', 'fieldtype': 'Data', 'label': 'Firma', 'reqd': 0, 'default': cur_page.page.search_fields.firma.get_value(), 'hidden': 1},
                        {'fieldname': 'anrede', 'fieldtype': 'Link', 'label': 'Anrede', 'reqd': 0, 'options': 'Salutation'},
                        {'fieldname': 'vorname', 'fieldtype': 'Data', 'label': 'Vorname', 'reqd': 1, 'default': cur_page.page.search_fields.vorname.get_value()},
                        {'fieldname': 'nachname', 'fieldtype': 'Data', 'label': 'Nachname', 'reqd': 1, 'default': cur_page.page.search_fields.nachname.get_value()},
                        {'fieldname': 'telefon', 'fieldtype': 'Data', 'label': 'Telefon Privat', 'reqd': 0, 'default': cur_page.page.search_fields.tel.get_value()},
                        {'fieldname': 'telefon_g', 'fieldtype': 'Data', 'label': 'Telefon Geschäft', 'reqd': 0},
                        {'fieldname': 'telefon_m', 'fieldtype': 'Data', 'label': 'Telefon Mobile', 'reqd': 0},
                        {'fieldname': 'email', 'fieldtype': 'Data', 'label': 'E-Mail', 'reqd': 0, 'options': 'Email', 'default': cur_page.page.search_fields.email.get_value()},
                        {'fieldname': 'cb_2', 'fieldtype': 'Column Break'},
                        {'fieldname': 'zusatz_firma', 'fieldtype': 'Data', 'label': 'Zusatz Firma', 'reqd': 0, 'default': cur_page.page.search_fields.zusatz_firma.get_value(), 'hidden': 1},
                        {'fieldname': 'zusatz_adresse', 'fieldtype': 'Data', 'label': 'Zusatz Adresse', 'reqd': 0, 'default': cur_page.page.search_fields.zusatz_adresse.get_value()},
                        {'fieldname': 'postfach', 'fieldtype': 'Check', 'label': 'Postfach', 'reqd': 0, 'default': cur_page.page.search_fields.postfach.get_value()},
                        {'fieldname': 'postfach_nummer', 'fieldtype': 'Data', 'label': 'Postfach Nummer', 'reqd': 0, 'default': cur_page.page.search_fields.postfach_nummer.get_value(), 'depends_on': 'eval:doc.postfach'},
                        {'fieldname': 'strasse', 'fieldtype': 'Data', 'label': 'Strasse', 'reqd': 1, 'default': cur_page.page.search_fields.strasse.get_value()},
                        {'fieldname': 'nummer', 'fieldtype': 'Data', 'label': 'Nummer', 'reqd': 0, 'default': cur_page.page.search_fields.nummer.get_value()},
                        {'fieldname': 'nummer_zu', 'fieldtype': 'Data', 'label': 'Nr. Zusatz', 'reqd': 0, 'default': cur_page.page.search_fields.nummer_zu.get_value()},
                        {'fieldname': 'plz', 'fieldtype': 'Data', 'label': 'PLZ', 'reqd': 1, 'default': cur_page.page.search_fields.plz.get_value()},
                        {'fieldname': 'ort', 'fieldtype': 'Data', 'label': 'Ort', 'reqd': 1, 'default': cur_page.page.search_fields.ort.get_value()},
                    ],
                    function(values){
                        frappe.call({
                            method: "mvd.mvd.page.mvd_suchmaske.mvd_suchmaske.anlage_prozess",
                            args:{
                                    'anlage_daten': values
                            },
                            freeze: true,
                            freeze_message: 'Erstelle Mitgliedschaften...',
                            callback: function(r)
                            {
                                if (r.message) {
                                    cur_page.page.search_fields.neuanlage.df.hidden = 1;
                                    cur_page.page.search_fields.neuanlage.refresh();
                                    frappe.set_route("Form", "MV Mitgliedschaft", r.message);
                                }
                            }
                        });
                    },
                    'Neuanlage',
                    'Anlegen'
                    )
                }
            },
            only_input: true,
        });
        return neuanlage
    }
}

function get_default_sektion() {
    var default_sektion = '';
    if (frappe.defaults.get_user_permissions()["Sektion"]) {
        var sektionen = frappe.defaults.get_user_permissions()["Sektion"];
        sektionen.forEach(function(entry) {
            if (entry.is_default == 1) {
                default_sektion = entry.doc;
            }
        });
    }
    return default_sektion
}
