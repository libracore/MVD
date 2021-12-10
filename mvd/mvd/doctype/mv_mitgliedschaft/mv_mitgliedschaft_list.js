// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['MV Mitgliedschaft'] = {
    onload: function(listview) {
        listview.page.add_menu_item(__("Erstelle Serienbrief"), function() {
                var selected = listview.get_checked_items();
                if (selected.length > 0) {
                    create_serienbrief(selected);
                } else {
                    frappe.msgprint("Bitte markieren Sie zuerst die gewünschten Mitgliedschaften");
                }
        });
    }
};

function create_serienbrief(mitgliedschaften) {
    var d = new frappe.ui.Dialog({
        'title': __('Serienbrief'),
        'fields': [
            {'fieldname': 'vorlage_laden', 'fieldtype': 'Button', 'label': 'Vorlage laden', 'click': function() {
                    var _d = get_vorlage(d);
                    if (_d) {
                        d = _d;
                    }
                }
            },
            {'fieldname': 'sektion_id', 'fieldtype': 'Link', 'label': 'Sektion', 'reqd': 1, 'options': 'Sektion', 'change': function() {
                    frappe.call({
                        'method': "frappe.client.get",
                        'args': {
                            'doctype': "Sektion",
                            'name': d.get_value('sektion_id')
                        },
                        'callback': function(response) {
                            var sektion_settings = response.message;

                            if (sektion_settings) {
                                d.set_value('ort', sektion_settings.default_ort);
                            }
                        }
                    });
                }
            },
            {'fieldname': 'check_ansprechperson', 'fieldtype': 'Check', 'label': 'Ansprechperson ausblenden'},
            {'fieldname': 'ansprechperson', 'fieldtype': 'Data', 'label': 'Ansprechperson', 'depends_on': 'eval:!doc.check_ansprechperson'},
            {'fieldname': 'tel_ma', 'fieldtype': 'Data', 'label': 'Tel. Mitarbeiter:inn', 'depends_on': 'eval:!doc.check_ansprechperson'},
            {'fieldname': 'email_ma', 'fieldtype': 'Data', 'label': 'E-Mail Mitarbeiter:inn', 'depends_on': 'eval:!doc.check_ansprechperson'},
            {'fieldname': 'mit_ausweis', 'fieldtype': 'Check', 'label': 'inkl. Mitgliederausweis', 'depends_on': 'eval:!doc.check_ansprechperson'},
            {'fieldname': 'ort', 'fieldtype': 'Data', 'label': 'Ort', 'reqd': 1},
            {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Datum', 'reqd': 1, 'default': frappe.datetime.get_today()},
            {'fieldname': 'brieftitel', 'fieldtype': 'Data', 'label': 'Brieftitel', 'reqd': 1},
            {'fieldname': 'check_anrede', 'fieldtype': 'Check', 'label': 'Eigene Anrede'},
            {'fieldname': 'anrede', 'fieldtype': 'Data', 'label': 'Anrede', 'depends_on': 'eval:doc.check_anrede'},
            {'fieldname': 'inhalt', 'fieldtype': 'Text Editor', 'label': 'Inhalt 1. Seite', 'reqd': 1},
            {'fieldname': 'inhalt_2', 'fieldtype': 'Text Editor', 'label': 'Inhalt 2. Seite'}
        ],
        primary_action: function(){
            d.hide();
            erstelle_korrespondenzen(mitgliedschaften, d);
        },
        primary_action_label: __('Erstellen')
    });
    frappe.call({
        'method': "frappe.client.get",
        'args': {
            'doctype': "User",
            'name': frappe.session.user
        },
        'callback': function(response) {
            var user = response.message;

            if (user) {
                d.set_value('ansprechperson', user.full_name);
                d.set_value('tel_ma', user.phone);
                d.set_value('email_ma', user.email);
            }
        }
    });
    d.show();
}

function get_vorlage(d) {
    frappe.prompt([
        {'fieldname': 'vorlage', 'fieldtype': 'Link', 'label': 'Vorlage', 'reqd': 1, 'options': 'MV Korrespondenz Vorlage'}  
    ],
    function(values){
        frappe.call({
            "method": "frappe.client.get",
            "args": {
                "doctype": "MV Korrespondenz Vorlage",
                "name": values.vorlage
            },
            "callback": function(r) {
                if (r.message) {
                    var vorlage = r.message;
                    d.set_value("sektion_id", vorlage.sektion_id);
                    d.set_value("check_ansprechperson", vorlage.check_ansprechperson);
                    d.set_value("mit_ausweis", vorlage.mit_ausweis);
                    d.set_value("ort", vorlage.ort);
                    d.set_value("brieftitel", vorlage.brieftitel);
                    d.set_value("check_anrede", vorlage.check_anrede);
                    d.set_value("anrede", vorlage.anrede);
                    d.set_value("inhalt", vorlage.inhalt);
                    d.set_value("inhalt_2", vorlage.inhalt_2);
                    return d
                }
            }
        });
    },
    'Vorlage laden',
    'Laden'
    )
}

function erstelle_korrespondenzen(mitgliedschaften, d) {
    console.log(mitgliedschaften);
    console.log(d);
}
