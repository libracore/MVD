// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Kunden', {
    onload: function(frm) {
        if (frm.doc.__islocal) {
            setTimeout(function(){ cur_frm.set_value("language", "de"); }, 500);
        }
    },
    refresh: function(frm) {
        // buttons
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__("Rechnung"), function() {
                erstelle_rechnung_sonstiges(frm);
            }, __("Erstelle"));
            
            if (!cur_frm.doc.mv_mitgliedschaft) {
                frm.add_custom_button(__("Interessent*in"), function() {
                    umwandlung(frm, 'Interessent*in');
                }, __("Umwandlung"));
                
                frm.add_custom_button(__("Anmeldung"), function() {
                    umwandlung(frm, 'Anmeldung');
                }, __("Umwandlung"));
                
                frm.add_custom_button(__("Mitglied (Regulär)"), function() {
                    umwandlung(frm, 'Regulär');
                }, __("Umwandlung"));
            }
        }
        
        // set strasse, plz und ort mandatory (Rechnungsempfänger)
        rechnungsadresse_mandatory(frm);
        // set firma mandatory (Kunde)
        firmenkunde_mandatory(frm);
        // set nachname und vorname mandatory (Eigener Rechnungsempfänger)
        rechnungsempfaenger_mandatory(frm);
        // set firma mandatory (Eigener Rechnungsempfänger)
        firmenrechnungsempfaenger_mandatory(frm);
        
        // erstelle Debitorenübersicht in Dashboard
        set_party_dashboard_indicators(frm);
    },
    abweichende_rechnungsadresse: function(frm) {
        // set strasse, plz und ort mandatory (Rechnungsempfänger)
        rechnungsadresse_mandatory(frm);
        // set nachname und vorname mandatory (Rechnungsempfänger)
        rechnungsempfaenger_mandatory(frm);
    },
    kundentyp: function(frm) {
        // set firma mandatory (Kunde)
        firmenkunde_mandatory(frm);
    },
    unabhaengiger_debitor: function(frm) {
        // set nachname und vorname mandatory (Rechnungsempfänger)
        rechnungsempfaenger_mandatory(frm);
    },
    rg_kundentyp: function(frm) {
        // set firma mandatory (Rechnungsempfänger)
        firmenrechnungsempfaenger_mandatory(frm);
    },
    plz: function(frm) {
        pincode_lookup(cur_frm.doc.plz, 'ort');
    },
    rg_plz: function(frm) {
        pincode_lookup(cur_frm.doc.rg_plz, 'rg_ort');
    }
});

function rechnungsadresse_mandatory(frm) {
    // set strasse, plz und ort mandatory (Rechnungsempfänger)
    if (cur_frm.doc.abweichende_rechnungsadresse) {
        cur_frm.set_df_property('rg_strasse', 'reqd', 1);
        cur_frm.set_df_property('rg_plz', 'reqd', 1);
        cur_frm.set_df_property('rg_ort', 'reqd', 1);
    } else {
        cur_frm.set_df_property('rg_strasse', 'reqd', 0);
        cur_frm.set_df_property('rg_plz', 'reqd', 0);
        cur_frm.set_df_property('rg_ort', 'reqd', 0);
    }
}

function firmenkunde_mandatory(frm) {
    // set firma mandatory (Kunde)
    if (cur_frm.doc.kundentyp == 'Unternehmen') {
        cur_frm.set_df_property('firma', 'reqd', 1);
        cur_frm.set_df_property('nachname', 'reqd', 0);
        cur_frm.set_df_property('vorname', 'reqd', 0);
    } else {
        cur_frm.set_df_property('firma', 'reqd', 0);
        cur_frm.set_df_property('nachname', 'reqd', 1);
        cur_frm.set_df_property('vorname', 'reqd', 1);
    }
}

function rechnungsempfaenger_mandatory(frm) {
    // set nachname und vorname mandatory (Eigener Rechnungsempfänger)
    if (cur_frm.doc.abweichende_rechnungsadresse) {
        cur_frm.set_df_property('rg_nachname', 'reqd', 1);
        cur_frm.set_df_property('rg_vorname', 'reqd', 1);
    } else {
        cur_frm.set_df_property('rg_nachname', 'reqd', 0);
        cur_frm.set_df_property('rg_vorname', 'reqd', 0);
    }
}

function firmenrechnungsempfaenger_mandatory(frm) {
    // set firma mandatory (Kunde)
    if (cur_frm.doc.rg_kundentyp == 'Unternehmen') {
        cur_frm.set_df_property('rg_firma', 'reqd', 1);
    } else {
        cur_frm.set_df_property('rg_firma', 'reqd', 0);
    }
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
                frappe.prompt([
                    {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage',
                        'get_query': function() {
                            return { 'filters': { 'name': ['in', eval(druckvorlagen.alle_druckvorlagen)] } };
                        }
                    },
                    {'fieldname': 'bar_bezahlt', 'fieldtype': 'Check', 'label': 'Barzahlung', 'reqd': 0, 'default': 0, 'hidden': 0},
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
                                    var rate_field = this.grid_row.on_grid_fields[2];
                                    var qty_field = this.grid_row.on_grid_fields[1];
                                    frappe.call({
                                        method: "mvd.mvd.utils.manuelle_rechnungs_items.get_item_price",
                                        args:{
                                                'item': this.get_value()
                                        },
                                        callback: function(r)
                                        {
                                            rate_field.set_value(r.message);
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
                        }]
                    }
                ],
                function(values){
                    if (values.bar_bezahlt == 1) {
                        var bar_bezahlt = true;
                    } else {
                        var bar_bezahlt = null;
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
                                'kunde': cur_frm.doc.name,
                                'bezahlt': bar_bezahlt,
                                'attach_as_pdf': true,
                                'submit': true,
                                'druckvorlage': values.druckvorlage,
                                'rechnungs_artikel': values.rechnungs_artikel,
                                'mv_mitgliedschaft': cur_frm.doc.mv_mitgliedschaft,
                                'ignore_pricing_rule': ignore_pricing_rule
                        },
                        freeze: true,
                        freeze_message: 'Erstelle Rechnung...',
                        callback: function(r)
                        {
                            cur_frm.reload_doc();
                            cur_frm.timeline.insert_comment("Rechnung " + r.message + " erstellt.");
                            frappe.msgprint("Die Rechnung wurde erstellt, Sie finden sie in den Anhängen.");
                            cur_frm.reload_doc();
                        }
                    });
                },
                'Rechnungs Erstellung',
                'Erstellen'
                )
            }
        });
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

function set_party_dashboard_indicators(frm) {
    if(frm.doc.__onload && frm.doc.__onload.dashboard_info) {
        var company_wise_info = frm.doc.__onload.dashboard_info;
        frm.dashboard.add_indicator(__('Annual Billing: {0}',
            [format_currency(company_wise_info[0].billing_this_year, company_wise_info[0].currency)]), 'blue');
        frm.dashboard.add_indicator(__('Total Unpaid: {0}',
            [format_currency(company_wise_info[0].total_unpaid, company_wise_info[0].currency)]),
        company_wise_info[0].total_unpaid ? 'orange' : 'green');
    }
}

function pincode_lookup(pincode, field) {
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
                        cur_frm.set_value(field, city);
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
                                cur_frm.set_value(field, city);
                            },
                            __('City'),
                            __('Set')
                        );
                    }
                } else {
                    // got no match
                    cur_frm.set_value(field, city);
                }
            }
        });
    }
}

function umwandlung(frm, status) {
    frappe.call({
        'method': "mvd.mvd.doctype.kunden.kunden.anlage_prozess",
        'args':{
                'anlage_daten': frm.doc,
                'status': status
        },
        'freeze': true,
        'freeze_message': 'Wandle um zu ' + status + '...',
        'callback': function(r)
        {
            if (r.message) {
                cur_frm.set_value("mv_mitgliedschaft", r.message);
                cur_frm.save();
                frappe.set_route("Form", "Mitgliedschaft", r.message);
            }
        }
    });
}
