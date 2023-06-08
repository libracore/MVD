// Copyright (c) 2023, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Beratung', {
    refresh: function(frm) {
        // Handler für gesperrte Ansicht
        var gesperrt = false;
        if (cur_frm.doc.gesperrt_am) {
            if (cur_frm.doc.gesperrt_von != frappe.session.user) {
                gesperrt = true;
                setze_read_only(frm);
                var confirm_message = "Die Beratung ist seit <b>" + cur_frm.doc.gesperrt_am + "</b> durch <b>" + cur_frm.doc.gesperrt_von + "</b> geöffnet und dadurch die Bearbeitung gesperrt.<br><br>Wollen Sie in der Gesperrten Ansicht weiterfahren?";
                frappe.confirm(confirm_message,
                () => {
                    // yes -> do nothing
                }, () => {
                    // No -> nachfragen
                    frappe.confirm("Sind Sie sicher?",
                    () => {
                        // yes -> entsperren
                        frappe.call({
                            method: "mvd.mvd.doctype.beratung.beratung.clear_protection",
                            args:{
                                    'beratung': cur_frm.doc.name,
                                    'force': true
                            },
                            async: false,
                            callback: function(done) {
                                location.reload();
                                cur_frm.timeline.render_timeline_item({
                                    content: __("created"),
                                    comment_type: "Created",
                                    communication_type: "Comment",
                                    sender: frappe.session.user,
                                    communication_date: cur_frm.doc.gesperrt_am,
                                    creation: cur_frm.doc.gesperrt_am,
                                    frm: cur_frm
                                });
                            }
                        });
                    }, () => {
                        // No -> do nothing
                    })
                })
            }
        }
        
        if (!frm.doc.__islocal) {
            if (cur_frm.doc.mv_mitgliedschaft) {
                // load html overview
                load_html_overview(frm);
            }
            
            // load html verknüpfungen
            load_html_verknuepfungen(frm);
            
            if (!gesperrt) {
                // btn zum übernehmen
                frm.add_custom_button(__("Übernehmen"),  function() {
                    frappe.call({
                        method: "mvd.mvd.doctype.beratung.beratung.uebernahme",
                        args:{
                                'beratung': cur_frm.doc.name,
                                'user': frappe.session.user
                        },
                        callback: function(r)
                        {
                            if (r.message) {
                                if (cur_frm.doc.kontaktperson != r.message) {
                                    cur_frm.set_value("kontaktperson", r.message);
                                    if (cur_frm.doc.status == 'Eingang') {
                                        cur_frm.set_value("status", 'Open');
                                    }
                                    frappe.msgprint('Sie wurden als "Berater*in" erfasst.<br>Die ToDo anpassungen erfolgen mit dem <b>Speichern</b> der Beratung.');
                                } else {
                                    frappe.msgprint('Sie sind bereits als "Berater*in" erfasst.');
                                }
                            } else {
                                frappe.msgprint('Die automatische Übernahme dieser Beratung für Sie konnte nicht durchgeführt werden, weil es keine "Berater*in" gibt die Ihnen zugeordnet ist.');
                            }
                        }
                    });
                }, __("Beratungs Aktionen"));
                
                //btn zum Verknüpfen
                frm.add_custom_button(__("Verknüpfen"),  function() {
                    frappe.prompt([
                        {'fieldname': 'beratung', 'fieldtype': 'Link', 'options': 'Beratung', 'label': 'Beratung', 'reqd': 1}  
                    ],
                    function(values){
                        verknuepfen(cur_frm.doc.name, values.beratung, false);
                    },
                    'Beratungs Verknüpfung',
                    'Verknüpfen'
                    );
                }, __("Beratungs Aktionen"));
                
                // btn zum zusammenführen
                frm.add_custom_button(__("Zusammenführen"),  function() {
                    frappe.prompt([
                        {'fieldname': 'master', 'fieldtype': 'Link', 'label': 'Master Beratung', 'reqd': 1, 'options': 'Beratung'}  
                    ],
                    function(values){
                        frappe.call({
                            method: "mvd.mvd.doctype.beratung.beratung.merge",
                            args:{
                                    'slave': cur_frm.doc.name,
                                    'master': values.master
                            },
                            callback: function(r)
                            {
                                cur_frm.reload_doc();
                            }
                        });
                    },
                    'Beratungen zusammenführen',
                    'Zusammenführen'
                    )
                }, __("Beratungs Aktionen"));
                
                if (cur_frm.doc.status != 'Closed') {
                    frm.add_custom_button(__("Schliessen"),  function() {
                        cur_frm.set_value("status", 'Closed').then(function(){
                            cur_frm.save();
                        })
                    }, __("Beratungs Aktionen"));
                }
                
                if ((cur_frm.doc.status == 'Closed')&&(cur_frm.doc.ignore_abschluss_mail != 1)) {
                    // Abfrage ob Abschluss Mail gesendet werden soll
                    var d = new frappe.ui.Dialog({
                        'fields': [
                            {'fieldname': 'ht', 'fieldtype': 'HTML'},
                            {'fieldname': 'mail', 'fieldtype': 'Button', 'label': 'Abschluss E-Mail senden', 'click': function() {
                                    d.hide();
                                    cur_frm.set_value("ignore_abschluss_mail", 1).then(function(){
                                        cur_frm.save().then(function(){
                                            frappe.mvd.new_mail(cur_frm);
                                        })
                                    })
                                }
                            },
                            {'fieldname': 'ignore', 'fieldtype': 'Button', 'label': 'Diese Meldung deaktivieren', 'click': function() {
                                    d.hide();
                                    cur_frm.set_value("ignore_abschluss_mail", 1).then(function(){
                                        cur_frm.save();
                                    })
                                }
                            }
                        ],
                        'title': "Abschluss E-Mail"
                    });
                    d.fields_dict.ht.$wrapper.html('Diese Beratung besitzt den Status "Geschlossen".<br>Sie können nun entweder ein Abschluss E-Mail schreiben, oder diese Erinnerung für die Zukunft deaktivieren.');
                    d.show();
                }
                
                // als gelesen markieren
                if (cur_frm.doc.ungelesen) {
                    frm.add_custom_button(__("Als gelesen markieren"),  function() {
                        if (cur_frm.is_dirty()) {
                            cur_frm.set_value("ungelesen", 0);
                            cur_frm.save();
                        } else {
                            frappe.db.set_value("Beratung", cur_frm.doc.name, 'ungelesen', 0).then(function(){
                                cur_frm.reload_doc();
                            })
                        }
                    });
                }
                
                if (['Eingang', 'Open'].includes(cur_frm.doc.status)) {
                    frm.add_custom_button(__("E-Mail Rückfrage"),  function() {
                        cur_frm.set_value("status", "Rückfragen");
                        cur_frm.save();
                        frappe.db.get_value("Sektion", cur_frm.doc.sektion_id, 'default_rueckfragen_email_template').then(function(value){
                            cur_frm['default_rueckfragen_email_template'] = value.message.default_rueckfragen_email_template;
                            var communications = cur_frm.timeline.get_communications();
                            var last_email = '';
                            if (communications.length > 0) {
                                for (var i = communications.length - 1; i >= 0; i--) {
                                    if (communications[i].communication_medium == 'Email') {
                                        last_email = communications[i];
                                    }
                                }
                            }
                            frappe.mvd.new_mail(cur_frm, last_email);
                            cur_frm['default_rueckfragen_email_template'] = false;
                        });
                    }, __("Rückfrage"));
                    frm.add_custom_button(__("Termin vereinbaren"),  function() {
                        cur_frm.set_value("status", "Rückfrage: Termin vereinbaren");
                        cur_frm.save();
                    }, __("Rückfrage"));
                }
                
                if ((cur_frm.doc.status != 'Closed')&&(cur_frm.doc.termin.length < 1)&&(cur_frm.doc.mv_mitgliedschaft)) {
                    frm.add_custom_button(__("Termin vergeben"),  function() {
                        termin_quick_entry(frm);
                    });
                }
                
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
                frappe.ui.keys.on('ctrl+e', function(e) {frappe.mvd.new_mail(cur_frm);});
            } else {
                // disable E-Mail BTN
                $("[data-label='Email']").parent().off("click");
                $("[data-label='Email']").parent().click(function(){frappe.msgprint("Diese Beratung ist zur Bearbeitung gesperrt.");});
                $("[data-label='E-Mail']").parent().off("click");
                $("[data-label='E-Mail']").parent().click(function(){frappe.msgprint("Diese Beratung ist zur Bearbeitung gesperrt.");});
                $(".btn.btn-default.btn-new-email.btn-xs").off("click");
                $(".btn.btn-default.btn-new-email.btn-xs").click(function(){frappe.msgprint("Diese Beratung ist zur Bearbeitung gesperrt.");}); 
                $("[title='Reply']").hide();
                $("[title='Reply All']").hide();
                frappe.ui.keys.off('ctrl+e', cur_frm.page);
                frappe.ui.keys.on('ctrl+e', function(e) {frappe.msgprint("Diese Beratung ist zur Bearbeitung gesperrt.");});
            }
            
            if (cur_frm.doc.kontaktperson&&cur_frm.doc.create_todo) {
                frappe.call({
                    method: "mvd.mvd.doctype.beratung.beratung.new_todo",
                    args:{
                            'beratung': cur_frm.doc.name,
                            'kontaktperson': cur_frm.doc.kontaktperson
                    },
                    callback: function(r)
                    {
                        cur_frm.reload_doc();
                        frappe.msgprint("ToDo erstellt");
                    }
                });
            }
            
            if (cur_frm.doc.status == 'Zusammengeführt') {
                setze_read_only(frm);
            }
        }
    },
    mv_mitgliedschaft: function(frm) {
        if ((!frm.doc.__islocal)&&(cur_frm.doc.mv_mitgliedschaft)) {
            // load html overview
            load_html_overview(frm);
        }
    }
});

function load_html_overview(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_uebersicht_html",
        args:{
                'name': cur_frm.doc.mv_mitgliedschaft
        },
        callback: function(r)
        {
            cur_frm.set_df_property('uebersicht_html','options', r.message);
        }
    });
}

function load_html_verknuepfungen(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.beratung.beratung.get_verknuepfungsuebersicht",
        args:{
                'beratung': cur_frm.doc.name
        },
        callback: function(r)
        {
            cur_frm.set_df_property('verknuepfungen_html','options', r.message);
            add_jump_icons_event_handler(frm);
            add_trash_icons_event_handler(frm);
            add_route_to_list_view_event_handler(frm);
        }
    });
}

function verknuepfen(beratung_parent, beratung, remove) {
    if (!remove) {
        frappe.call({
            'method': "mvd.mvd.doctype.beratung.beratung.verknuepfen",
            'args': {
                'beratung': beratung_parent,
                'verknuepfung': beratung
            },
            'callback': function(r) {
                cur_frm.reload_doc()
            }
        });
    } else {
        frappe.call({
            'method': "mvd.mvd.doctype.beratung.beratung.verknuepfung_entfernen",
            'args': {
                'beratung': beratung_parent,
                'verknuepfung': beratung
            },
            'callback': function(r) {
                cur_frm.reload_doc()
            }
        });
    }
}

function add_trash_icons_event_handler(frm) {
    // event handler für trash icons (verknüpfungen)
    $(".verknuepfung_trash").each(function() {
        $(this).bind( "click", function() {
            $(this).parent().parent().css({"background-color": "red"});
            verknuepfen(cur_frm.doc.name, $(this).attr("data-remove"), true);
        });
    });
}

function add_jump_icons_event_handler(frm) {
    // event handler für jump icons (verknüpfungen)
    $(".verknuepfung_jump").each(function() {
        $(this).bind( "click", function() {
            frappe.set_route("Form", "Beratung", $(this).attr("data-jump"));
        });
    });
}

function add_route_to_list_view_event_handler(frm) {
    // event handler für anz. Beratungen (verknüpfungen)
    $("#route_to_list_view").bind( "click", function() {
        frappe.route_options = {
            'mv_mitgliedschaft': cur_frm.doc.mv_mitgliedschaft
        }
        frappe.set_route("List", "Beratung", "List");
    });
}

function setze_read_only(frm) {
    var i = 0;
    for (i; i<cur_frm.fields.length; i++) {
        cur_frm.set_df_property(cur_frm.fields[i].df.fieldname,'read_only', 1);
    }
}

function termin_quick_entry(frm) {
    frappe.call({
        'method': "mvd.mvd.doctype.beratung.beratung.get_beratungsorte",
        'args': {
            'sektion': cur_frm.doc.sektion_id
        },
        'callback': function(r) {
            var orte = r.message.ort_string;
            var default_termindauer = r.message.default_termindauer;
            var default_von = roundMinutes(frappe.datetime.now_datetime()); // default "von"-Zeit = aktuelle Zeit gerundet auf nächste volle Stunde
            var d = new frappe.ui.Dialog({
              'title': __('Termin erstellen'),
              'fields': [
                {'fieldname': 'kontaktperson', 'fieldtype': 'Link', 'label': __('Kontaktperson'), 'options': 'Termin Kontaktperson', 'reqd': 1,
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
                                        var orte_kontaktbasis = r.message.ort_string;
                                        var default_ort_kontaktbasis = r.message.default;
                                        d.set_df_property('ort', 'options', orte_kontaktbasis);
                                        d.set_value('ort',  default_ort_kontaktbasis);
                                    } else {
                                        // Keine Orte zu Kontakt
                                        d.set_value('ort',  '');
                                        d.set_df_property('ort', 'options', '');
                                    }
                                }
                            });
                          } else {
                              // reset to default
                              d.set_value('ort',  '');
                              d.set_df_property('ort', 'options', orte);
                          }
                      }
                },
                {'fieldname': 'ort', 'fieldtype': 'Select', 'label': __('Ort'), 'options': orte, 'reqd': 1, 'default': ''},
                {'fieldname': 'art', 'fieldtype': 'Select', 'label': __('Art'), 'options': 'telefonisch\npersönlich\nE-Mail', 'reqd': 1, 'default': 'telefonisch'},
                {'fieldname': 'von', 'fieldtype': 'Datetime', 'label': __('Zeit von'), 'reqd': 1, 'default': default_von,
                    'change': function() {
                        var newDateObj = moment(d.get_value('von')).add(default_termindauer, 'm').toDate(); // default "bis"-Zeit = "von"-Zeit + default_termindauer oder 45'
                        d.set_value('bis',  newDateObj);
                    }
                },
                {'fieldname': 'bis', 'fieldtype': 'Datetime', 'label': __('Zeit bis'), 'reqd': 1}
              ],
              'primary_action': function() {
                    d.hide();
                    var child = cur_frm.add_child('termin');
                    frappe.model.set_value(child.doctype, child.name, 'von', d.get_value('von'));
                    frappe.model.set_value(child.doctype, child.name, 'bis', d.get_value('bis'));
                    frappe.model.set_value(child.doctype, child.name, 'art', d.get_value('art'));
                    frappe.model.set_value(child.doctype, child.name, 'ort', d.get_value('ort'));
                    frappe.model.set_value(child.doctype, child.name, 'berater_in', d.get_value('kontaktperson'));
                    cur_frm.refresh_field('termin');
                    cur_frm.set_value("kontaktperson", d.get_value('kontaktperson'));
                    cur_frm.save();
                    frappe.db.get_value("Sektion", cur_frm.doc.sektion_id, 'default_terminbestaetigung_email_template').then(function(value){
                        cur_frm['default_terminbestaetigung_email_template'] = value.message.default_terminbestaetigung_email_template;
                        frappe.mvd.new_mail(cur_frm);
                        cur_frm['default_terminbestaetigung_email_template'] = false;
                    });
              },
              'primary_action_label': __('Erstellen')
            });
            d.show();
        }
    });
    
}

function roundMinutes(date_string) {
    var date = new Date(date_string);
    date.setHours(date.getHours() + Math.round(date.getMinutes()/60));
    date.setMinutes(0, 0, 0);
    return date
}

function prepare_mvd_mail_composer(e) {
    var last_email = null;

    const $target = $(e.currentTarget);
    const name = $target.data().name;

    // find the email to reply to
    cur_frm.timeline.get_communications().forEach(function(c) {
        if(c.name == name) {
            last_email = c;
            return false;
        }
    });

    const opts = {
        doc: cur_frm.doc,
        txt: "",
        title: __('Reply'),
        frm: cur_frm,
        last_email,
        is_a_reply: true
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
