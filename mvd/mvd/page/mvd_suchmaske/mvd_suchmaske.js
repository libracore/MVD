frappe.pages['mvd-suchmaske'].on_page_load = function(wrapper) {
    var me = this;
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Mitgliedschaftssuche',
        single_column: true
    });
    
    me.$user_search_button = me.page.set_secondary_action('Suche zurücksetzen', () => {
        console.log(me);
    });
    me.$user_search_button = me.page.set_primary_action('Suche starten', () => {
        frappe.mvd_such_client.suche(page);
        console.log("hoii");
    });
    
    //erstelle suchabschnitt
    page.main.html(frappe.render_template("suchmaske", {}));
    
    //erstelle suchfelder
    me.search_fields = {};
    me.search_fields.sektion_id = frappe.mvd_such_client.create_sektion_id_field(page)
    me.search_fields.sektion_id.refresh();
    me.search_fields.mitglied_nr = frappe.mvd_such_client.create_mitglied_nr_field(page)
    me.search_fields.mitglied_nr.refresh();
    me.search_fields.status_c = frappe.mvd_such_client.create_status_c_field(page)
    me.search_fields.status_c.refresh();
    me.search_fields.mitgliedtyp_c = frappe.mvd_such_client.create_mitgliedtyp_c_field(page)
    me.search_fields.mitgliedtyp_c.refresh();
    me.search_fields.mitglied_c = frappe.mvd_such_client.create_mitglied_c_field(page)
    me.search_fields.mitglied_c.refresh();
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
    me.search_fields.postfach = frappe.mvd_such_client.create_postfach_field(page, me.search_fields.postfach_nummer, me.search_fields.strasse, me.search_fields.nummer, me.search_fields.nummer_zu)
    me.search_fields.postfach.refresh();
    me.search_fields.plz = frappe.mvd_such_client.create_plz_field(page)
    me.search_fields.plz.refresh();
    me.search_fields.ort = frappe.mvd_such_client.create_ort_field(page)
    me.search_fields.ort.refresh();
    
    
    me.search_fields.suchresultate = frappe.mvd_such_client.create_resultate_div(page)
    me.search_fields.suchresultate.refresh();
    
}


frappe.mvd_such_client = {
    suche: function(page) {
        var search_data = {};
        for (const [ key, value ] of Object.entries(cur_page.page.search_fields)) {
            if (value.get_value()) {
                search_data[key] = value.get_value();
            } else {
                search_data[key] = false;
            }
        }
        console.log(search_data);
        frappe.call({
            method: "mvd.mvd.page.mvd_suchmaske.mvd_suchmaske.suche",
            args:{
                    'suchparameter': search_data
            },
            callback: function(r)
            {
                // erstelle resultatabschnitt
                cur_page.page.search_fields.suchresultate.set_value(r.message);
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
                change: function(){
                    //if(pid != patient.get_value() && patient.get_value()){
                        //me.start = 0;
                        //me.page.main.find(".patient_documents_list").html("");
                        //get_documents(patient.get_value(), me);
                        //show_patient_info(patient.get_value(), me);
                        //show_patient_vital_charts(patient.get_value(), me, "bp", "mmHg", "Blood Pressure");
                    //}
                    //pid = patient.get_value();
                    console.log("ich wurde ausgewählt");
                }
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
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
            },
            only_input: true,
        });
        return mitglied_nr
    },
    create_status_c_field: function(page) {
        var status_c = frappe.ui.form.make_control({
            parent: page.main.find(".status_c"),
            df: {
                fieldtype: "Select",
                fieldname: "status_c",
                options: 'Mitglied\nKündigung\nMutation\nWegzug\nAusschluss\nReaktiviert\nNeueintritt\nZuzug\nGestorben',
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
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
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
            },
            only_input: true,
        });
        return mitgliedtyp_c
    },
    create_mitglied_c_field: function(page) {
        var mitglied_c = frappe.ui.form.make_control({
            parent: page.main.find(".mitglied_c"),
            df: {
                fieldtype: "Select",
                fieldname: "mitglied_c",
                options: 'Online-Anmeldung\nAngemeldet\nMitglied\nOnline-Beitritt\nInaktiv\nInteressiert',
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
            },
            only_input: true,
        });
        return mitglied_c
    },
    create_vorname_field: function(page) {
        var vorname = frappe.ui.form.make_control({
            parent: page.main.find(".vorname"),
            df: {
                fieldtype: "Data",
                fieldname: "vorname",
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
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
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
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
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
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
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
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
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
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
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
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
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
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
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
            },
            only_input: true,
        });
        return nummer_zu
    },
    create_postfach_field: function(page, postfach_nummer, strasse, nummer, nummer_zu) {
        var postfach = frappe.ui.form.make_control({
            parent: page.main.find(".postfach"),
            df: {
                fieldtype: "Check",
                fieldname: "postfach",
                change: function(){
                    if (postfach.get_value() == 1) {
                        postfach_nummer.df.hidden = 0;
                        postfach_nummer.refresh();
                        strasse.df.hidden = 1;
                        strasse.refresh();
                        nummer.df.hidden = 1;
                        nummer.refresh();
                        nummer_zu.df.hidden = 1;
                        nummer_zu.refresh();
                    } else {
                        postfach_nummer.df.hidden = 1;
                        postfach_nummer.refresh();
                        strasse.df.hidden = 0;
                        strasse.refresh();
                        nummer.df.hidden = 0;
                        nummer.refresh();
                        nummer_zu.df.hidden = 0;
                        nummer_zu.refresh();
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
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
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
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
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
                change: function(){
                    console.log("ich wurde ausgewählt");
                }
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
    }
}


function open_mitgliedschaft(mitgliedschaft) {
    console.log("ich öffne jetzt " + mitgliedschaft);
    frappe.set_route("Form", "MV Mitgliedschaft", mitgliedschaft);
}
