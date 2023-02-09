// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mahnlauf', {
    onload: function(frm) {
        if (!cur_frm.doc.sektion_id) {
            cur_frm.set_value("sektion_id", get_default_sektion());
        }
    },
    refresh: function(frm) {
        cur_frm.fields_dict['druckvorlage'].get_query = function(doc) {
             return {
                 filters: {
                     "sektion_id": frm.doc.sektion_id,
                     "mahntyp": frm.doc.typ,
                     "mahnstufe": frm.doc.mahnstufe,
                     "dokument": "Mahnung"
                 }
             }
        }
    },
    mahnungen_buchen: function(frm) {
        frappe.dom.freeze('Bitte warten, buche Mahnungen...');
        frappe.call({
            'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.bulk_submit",
            'args': {
                'mahnlauf': cur_frm.doc.name
            },
            'callback': function(r) {
                var jobname = 'Mahnlauf ' + cur_frm.doc.name + ' (Submit)';
                let mahnung_refresher = setInterval(mahnung_refresher_handler, 3000, jobname);
                function mahnung_refresher_handler(jobname) {
                    frappe.call({
                    'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.is_mahnungs_job_running",
                        'args': {
                            'jobname': jobname
                        },
                        'callback': function(res) {
                            if (res.message == 'refresh') {
                                clearInterval(mahnung_refresher);
                                frappe.dom.unfreeze();
                                cur_frm.reload_doc();
                            }
                        }
                    });
                }
            }
        });
    },
    mahnungen_stornieren: function(frm) {
        frappe.dom.freeze('Bitte warten, storniere Mahnungen...');
        frappe.call({
            'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.bulk_cancel",
            'args': {
                'mahnlauf': cur_frm.doc.name
            },
            'callback': function(r) {
                var jobname = 'Mahnlauf ' + cur_frm.doc.name + ' (Cancel)';
                let mahnung_refresher = setInterval(mahnung_refresher_handler, 3000, jobname);
                function mahnung_refresher_handler(jobname) {
                    frappe.call({
                    'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.is_mahnungs_job_running",
                        'args': {
                            'jobname': jobname
                        },
                        'callback': function(res) {
                            if (res.message == 'refresh') {
                                clearInterval(mahnung_refresher);
                                frappe.dom.unfreeze();
                                cur_frm.reload_doc();
                            }
                        }
                    });
                }
            }
        });
    },
    erstelle_pdf: function(frm) {
        var d = new frappe.ui.Dialog({
            'fields': [
                {'fieldname': 'ht', 'fieldtype': 'HTML'},
                {'fieldname': 'pdf', 'fieldtype': 'Button', 'label': 'PDF erstellen', 'click': function() {
                        d.hide();
                        print_pdf(frm);
                    }
                },
                {'fieldname': 'csv', 'fieldtype': 'Button', 'label': 'CSV erstellen', 'click': function() {
                        d.hide();
                        frappe.msgprint("Hier folgt ein csv...");
                    }
                }
            ],
            primary_action: function(){
                d.hide();
            },
            primary_action_label: __('Abbrechen')
        });
        d.fields_dict.ht.$wrapper.html('Wie wollen Sie verfahren?');
        d.show();
    },
    entwuerfe_loeschen: function(frm) {
        frappe.dom.freeze('Bitte warten, lösche Entwurfs Mahnungen...');
        frappe.call({
            'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.bulk_delete",
            'args': {
                'mahnlauf': cur_frm.doc.name
            },
            'callback': function(r) {
                var jobname = 'Mahnlauf ' + cur_frm.doc.name + ' (Delete)';
                let mahnung_refresher = setInterval(mahnung_refresher_handler, 3000, jobname);
                function mahnung_refresher_handler(jobname) {
                    frappe.call({
                    'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.is_mahnungs_job_running",
                        'args': {
                            'jobname': jobname
                        },
                        'callback': function(res) {
                            if (res.message == 'refresh') {
                                clearInterval(mahnung_refresher);
                                frappe.dom.unfreeze();
                                cur_frm.reload_doc();
                            }
                        }
                    });
                }
            }
        });
    },
    typ: function(frm) {
        if (cur_frm.doc.typ == 'Produkte / Dienstleistungen') {
            cur_frm.set_value("typ_code", "P");
        }
        if (cur_frm.doc.typ == 'Mitgliedschaft (Jahresrechnung)') {
            cur_frm.set_value("typ_code", "M");
        }
        if (cur_frm.doc.typ == 'Anmeldungen') {
            cur_frm.set_value("typ_code", "A");
        }
    },
    versende_e_mail: function(frm) {
        frappe.call({
        'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.get_e_mail_field_list",
            'args': {
                'e_mail_vorlage': cur_frm.doc.e_mail_vorlage
            },
            'callback': function(r) {
                var d = new frappe.ui.Dialog({
                    fields: r.message,
                    primary_action: function(){
                        d.hide();
                        frappe.call({
                            'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.send_reminder_mails",
                            'args': {
                                'mahnlauf': cur_frm.doc.name,
                                'betreff': d.get_values().betreff,
                                'message': d.get_values().message,
                                'email_vorlage': cur_frm.doc.e_mail_vorlage
                            },
                            'callback': function(res) {
                                cur_frm.reload_doc();
                                frappe.msgprint("Die E-Mails wurden versendet.");
                            }
                        });
                    },
                    primary_action_label: __('Versenden'),
                    title: 'Mahnungs E-Mail Versand'
                });
                d.show();
            }
        });
        
    },
    zahlungserinnerungen: function(frm) {
        if (cur_frm.doc.zahlungserinnerungen == 1) {
            cur_frm.set_value("typ", "Mitgliedschaft (Jahresrechnung)");
            cur_frm.set_df_property('typ', 'read_only', 1);
            cur_frm.set_value("mahnstufe", "1");
            cur_frm.set_df_property('mahnstufe', 'read_only', 1);
            cur_frm.set_value("mahnungen_per_mail", "Ja");
            cur_frm.set_df_property('mahnungen_per_mail', 'read_only', 1);
        } else {
            cur_frm.set_df_property('typ', 'read_only', 0);
            cur_frm.set_df_property('mahnstufe', 'read_only', 0);
            cur_frm.set_df_property('mahnungen_per_mail', 'read_only', 0);
        }
    }
});

function print_pdf(frm) {
    frappe.dom.freeze('Bitte warten, bereite Massenlauf vor...');
    frappe.call({
        'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.mahnung_massenlauf",
        'args': {
            'mahnlauf': cur_frm.doc.name
        },
        'callback': function(r) {
            var jobname = 'Mahnlauf ' + cur_frm.doc.name + ' (Vorber. Massenlauf)';
            let mahnung_refresher = setInterval(mahnung_refresher_handler, 3000, jobname);
            function mahnung_refresher_handler(jobname) {
                frappe.call({
                'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.is_mahnungs_job_running",
                    'args': {
                        'jobname': jobname
                    },
                    'callback': function(res) {
                        if (res.message == 'refresh') {
                            clearInterval(mahnung_refresher);
                            frappe.dom.unfreeze();
                            cur_frm.reload_doc()
                            frappe.msgprint("Das Massenlauf Dokument wurde vorbereitet.");
                        }
                    }
                });
            }
        }
    });
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
