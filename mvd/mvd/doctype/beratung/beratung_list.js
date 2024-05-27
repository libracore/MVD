frappe.listview_settings['Beratung'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Erstelle Beratungs Termin"), function() {
            termin_quick_entry();
        });
    }
}

function termin_quick_entry() {
    var mv_mitgliedschaft_filter = '';
    if (cur_list.filter_area.filter_list.filters) {
        for (var i = 0; i < cur_list.filter_area.filter_list.filters.length; i++) {
            if (cur_list.filter_area.filter_list.filters[i].fieldname == 'mv_mitgliedschaft') {
                mv_mitgliedschaft_filter = cur_list.filter_area.filter_list.filters[i].value;
            }
        }
    }
    frappe.call({
        'method': "mvd.mvd.doctype.beratung.beratung.get_beratungsorte",
        'args': {
            'sektion': frappe.boot.default_sektion
        },
        'callback': function(r) {
            var orte = r.message.ort_string;
            var default_von = roundMinutes(frappe.datetime.now_datetime()); // default "von"-Zeit = aktuelle Zeit gerundet auf nächste volle Stunde
            var default_termindauer = r.message.default_termindauer;
                
            var d = new frappe.ui.Dialog({
              'title': __('Termin erstellen'),
              'fields': [
                {'fieldname': 'beratung', 'fieldtype': 'Link', 'label': __('Für Beratung'), 'options': 'Beratung', 'reqd': 0, 'hidden': 1,
                    'get_query': function() {
                        if (d.get_value('mv_mitgliedschaft')) {
                            return {
                                filters: {
                                    'mv_mitgliedschaft': d.get_value('mv_mitgliedschaft'),
                                    'hat_termine': 0
                                }
                            }
                        }
                        if (mv_mitgliedschaft_filter) {
                            return {
                                filters: {
                                    'mv_mitgliedschaft': mv_mitgliedschaft_filter,
                                    'hat_termine': 0
                                }
                            }
                        }
                        if (frappe.boot.default_sektion) {
                            return {
                                filters: {
                                    'sektion_id': frappe.boot.default_sektion,
                                    'hat_termine': 0
                                }
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
                {'fieldname': 'mv_mitgliedschaft', 'fieldtype': 'Link', 'label': __('Mitgliedschaft'), 'options': 'Mitgliedschaft', 'default': mv_mitgliedschaft_filter, 'reqd': 1},
                {'fieldname': 'kontaktperson', 'fieldtype': 'Link', 'label': __('Kontaktperson'), 'options': 'Termin Kontaktperson', 'reqd': 1,
                    'get_query': function() {
                        if (frappe.boot.default_sektion) {
                            return {
                                filters: {
                                    'sektion_id': frappe.boot.default_sektion
                                }
                            }
                        }
                    },
                    'change': function() {
                        if (d.get_value('kontaktperson')) {
                            frappe.call({
                                method: "mvd.mvd.doctype.beratung.beratung.get_beratungsorte",
                                args:{
                                    'sektion': frappe.boot.default_sektion,
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
                {'fieldname': 'beratungskategorie', 'fieldtype': 'Link', 'label': __('Beratungskategorie'), 'options': 'Beratungskategorie'},
                {'fieldname': 'art', 'fieldtype': 'Select', 'label': __('Art'), 'options': 'telefonisch\npersönlich', 'reqd': 1, 'default': 'telefonisch'},
                {'fieldname': 'telefonnummer', 'fieldtype': 'Data', 'label': __('Telefonnummer'), 'depends_on': 'eval:doc.art=="telefonisch"'},
                {'fieldname': 'von', 'fieldtype': 'Datetime', 'label': __('Zeit von'), 'reqd': 1, 'default': default_von,
                    'change': function() {
                        var newDateObj = moment(d.get_value('von')).add(default_termindauer, 'm').toDate(); // default "bis"-Zeit = "von"-Zeit + 45'
                        d.set_value('bis',  newDateObj);
                    }
                },
                {'fieldname': 'bis', 'fieldtype': 'Datetime', 'label': __('Zeit bis'), 'reqd': 1},
                {'fieldname': 'notiz', 'fieldtype': 'Text Editor', 'label': __('Notiz (Intern)')}
              ],
              'primary_action': function() {
                    d.hide();
                    if (d.get_value('neue_beratung') == 1) {
                        var kwargs = {
                            'von': d.get_value('von'),
                            'bis': d.get_value('bis'),
                            'sektion_id': frappe.boot.default_sektion,
                            'mv_mitgliedschaft': d.get_value('mv_mitgliedschaft'),
                            'art': d.get_value('art'),
                            'ort': d.get_value('ort'),
                            'berater_in': d.get_value('kontaktperson'),
                            'beratungskategorie': d.get_value('beratungskategorie'),
                            'notiz': d.get_value('notiz'),
                            'telefonnummer': d.get_value('telefonnummer')
                        }
                    } else {
                        var kwargs = {
                            'beratung': d.get_value('beratung'),
                            'von': d.get_value('von'),
                            'bis': d.get_value('bis'),
                            'art': d.get_value('art'),
                            'ort': d.get_value('ort'),
                            'berater_in': d.get_value('kontaktperson'),
                            'beratungskategorie': d.get_value('beratungskategorie'),
                            'notiz': d.get_value('notiz'),
                            'mv_mitgliedschaft': d.get_value('mv_mitgliedschaft'),
                            'telefonnummer': d.get_value('telefonnummer')
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
                                frappe.set_route("Form", "Beratung", r.message);
                            }
                        }
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
