// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('MV Korrespondenz', {
     refresh: function(frm) {
        frm.add_custom_button(__("Vorlage laden"),  function() {
                get_vorlage(frm);
        });
        frm.add_custom_button(__("Als Vorlage speichern"),  function() {
                save_as_vorlage(frm);
        });
     },
     sektion_id: function(frm) {
        frappe.call({
            'method': "frappe.client.get",
            'args': {
                'doctype': "Sektion",
                'name': cur_frm.doc.sektion_id
            },
            'callback': function(response) {
                var sektion_settings = response.message;

                if (sektion_settings) {
                    cur_frm.set_value('ort', sektion_settings.default_ort);
                }
            }
        });
     },
     setup: function(frm) {
         if (!cur_frm.doc.ansprechperson && !cur_frm.doc.tel_ma && !cur_frm.doc.email_ma) {
             frappe.call({
                'method': "frappe.client.get",
                'args': {
                    'doctype': "User",
                    'name': frappe.session.user
                },
                'callback': function(response) {
                    var user = response.message;

                    if (user) {
                        cur_frm.set_value('ansprechperson', user.full_name);
                        cur_frm.set_value('tel_ma', user.phone);
                        cur_frm.set_value('email_ma', user.email);
                    }
                }
            });
         }
     }
});


function get_vorlage(frm) {
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
                    cur_frm.set_value("sektion_id", vorlage.sektion_id);
                    cur_frm.set_value("check_ansprechperson", vorlage.check_ansprechperson);
                    cur_frm.set_value("mit_ausweis", vorlage.mit_ausweis);
                    cur_frm.set_value("ort", vorlage.ort);
                    cur_frm.set_value("brieftitel", vorlage.brieftitel);
                    cur_frm.set_value("check_anrede", vorlage.check_anrede);
                    cur_frm.set_value("anrede", vorlage.anrede);
                    cur_frm.set_value("inhalt", vorlage.inhalt);
                    cur_frm.set_value("inhalt_2", vorlage.inhalt_2);
                }
            }
        });
    },
    'Vorlage laden',
    'Laden'
    )
}

function save_as_vorlage(frm) {
    frappe.prompt([
        {'fieldname': 'titel', 'fieldtype': 'Data', 'label': 'Vorlagen Titel', 'reqd': 1}  
    ],
    function(values){
        frappe.call({
            method: "mvd.mvd.doctype.mv_korrespondenz.mv_korrespondenz.check_if_vorlage_exist",
            args:{
                    'vorlage': cur_frm.doc,
                    'titel': values.titel
            },
            callback: function(r)
            {
                if (r.message != 'alreadyExist') {
                    frappe.msgprint("Die Vorlage wurde gespeichert");
                } else {
                    frappe.confirm(
                        'Diese Vorlage existiert bereits, möchten Sie sie überschreiben?',
                        function(){
                            // on yes
                            frappe.call({
                                method: "mvd.mvd.doctype.mv_korrespondenz.mv_korrespondenz.check_if_vorlage_exist",
                                args:{
                                        'vorlage': cur_frm.doc,
                                        'titel': values.titel,
                                        'override': 1
                                },
                                callback: function(r)
                                {
                                    if (r.message == 'done') {
                                        frappe.msgprint("Die Vorlage wurde gespeichert");
                                    }
                                }
                            });
                        },
                        function(){
                            // on no
                        }
                    )
                }
            }
        });
    },
    'Als Vorlage speichern',
    'Speichern'
    )
}
