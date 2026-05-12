frappe.pages['vbz_beratung_termine'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Verarbeitungszentrale',
        single_column: true
    });

    frappe.vbz_beratung_termine.page = page;
    frappe.vbz_beratung_termine.no_render_based_on_filter = true;
    frappe.vbz_beratung_termine.render_view(page);

    poll(page);
};

frappe.pages['vbz_beratung_termine'].refresh = function(wrapper) {
    frappe.dom.unfreeze();
};

frappe.vbz_beratung_termine = {
    page: null,

    no_render_based_on_filter: true,

    render_view: function(page) {
        var free_only_field_value = page.filter_fields ? page.filter_fields.free_only_field.get_value()||'0':'0';
        var beratungsort_field_value = page.filter_fields ? page.filter_fields.beratungsort_field.get_value()||'':'';
        var berater_in_field_value = page.filter_fields ? page.filter_fields.berater_in_field.get_value()||'':'';
        var art_field_value = page.filter_fields ? page.filter_fields.art_field.get_value()||'':'';
        var datum_field_value = page.filter_fields ? page.filter_fields.datum_field.get_value()||'':'';
        var language_field_value = page.filter_fields ? page.filter_fields.language_field.get_value()||'':'';
        var fachskill_field_value = page.filter_fields ? page.filter_fields.fachskill_field.get_value()||'':'';
        var my_reservations_field_value = page.filter_fields ? page.filter_fields.my_reservations_field.get_value()||'':'';
        
        frappe.call({
            method: "mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.get_open_data",
            args: {
                free_only: free_only_field_value,
                beratungsort: beratungsort_field_value,
                berater_in: berater_in_field_value,
                art: art_field_value,
                datum: datum_field_value,
                language: language_field_value,
                fachskill: fachskill_field_value,
                my_reservations_only: my_reservations_field_value
            },
            freeze: true,
            freeze_message: 'Lade Verarbeitungszentrale...',
            async: false,
            callback: function(r) {
                
                if (r.message) {
                    const html = frappe.render_template("vbz_beratung_termine", r.message);

                    // Alten Inhalt entfernen und neu rendern
                    $(page.main).empty().html(html);

                    // Filter Felder
                    page.filter_fields = {}
                    frappe.vbz_beratung_termine.no_render_based_on_filter = true;
                    // CB: "Nur freie und reservierte Termine"
                    page.filter_fields.free_only_field = frappe.vbz_beratung_termine.create_free_only_field(page);
                    $(page.filter_fields.free_only_field.label_span).html("Nur freie und reservierte Termine");
                    page.filter_fields.free_only_field.set_value(free_only_field_value);
                    page.filter_fields.free_only_field.refresh();
                    // Select: Beratungsort
                    page.filter_fields.beratungsort_field = frappe.vbz_beratung_termine.create_beratungsort_field(page);
                    page.filter_fields.beratungsort_field.set_value(beratungsort_field_value);
                    page.filter_fields.beratungsort_field.refresh();
                    // Select: Berater*in
                    page.filter_fields.berater_in_field = frappe.vbz_beratung_termine.create_berater_in_field(page);
                    page.filter_fields.berater_in_field.set_value(berater_in_field_value);
                    page.filter_fields.berater_in_field.refresh();
                    // Select: Art
                    page.filter_fields.art_field = frappe.vbz_beratung_termine.create_art_field(page);
                    page.filter_fields.art_field.set_value(art_field_value);
                    page.filter_fields.art_field.refresh();
                    // Date: Datum ab
                    page.filter_fields.datum_field = frappe.vbz_beratung_termine.create_datum_field(page);
                    page.filter_fields.datum_field.set_value(datum_field_value);
                    page.filter_fields.datum_field.refresh();
                    // Link: Sprache
                    page.filter_fields.language_field = frappe.vbz_beratung_termine.create_language_field(page);
                    page.filter_fields.language_field.set_value(language_field_value);
                    page.filter_fields.language_field.refresh();
                    // Link: Fachskill
                    page.filter_fields.fachskill_field = frappe.vbz_beratung_termine.create_fachskill_field(page);
                    page.filter_fields.fachskill_field.set_value(fachskill_field_value);
                    page.filter_fields.fachskill_field.refresh();
                    // CB: Zeige meine Reservationen
                    page.filter_fields.my_reservations_field = frappe.vbz_beratung_termine.create_my_reservations_field(page);
                    $(page.filter_fields.my_reservations_field.label_span).html("Nur meine reservierten Termine");
                    page.filter_fields.my_reservations_field.set_value(my_reservations_field_value);
                    page.filter_fields.my_reservations_field.refresh();

                    setTimeout(function() {frappe.vbz_beratung_termine.no_render_based_on_filter = false;}, 1000);

                    frappe.vbz_beratung_termine.add_click_handlers(page);
                    localStorage['datenstand_for_polling'] = r.message.datenstand_for_polling;
                    localStorage['anz_eingetroffen_for_polling'] = r.message.anz_eingetroffen_for_polling;
                    frappe.vbz_beratung_termine.first_load = false;
                }

                frappe.dom.unfreeze();
            }
        });
    },

    reload_view: function(page) {
        this.render_view(page);
    },

    create_free_only_field: function(page) {
        var free_only_field = frappe.ui.form.make_control({
            parent: page.main.find(".free_only"),
            df: {
                fieldtype: "Check",
                fieldname: "free_only",
                change: function(){
                    if (!frappe.vbz_beratung_termine.no_render_based_on_filter) {
                        frappe.vbz_beratung_termine.reload_view(page);
                    }
                }
            },
            only_input: true
        });
        return free_only_field
    },

    create_my_reservations_field: function(page) {
        var my_reservations_field = frappe.ui.form.make_control({
            parent: page.main.find(".my_reservations"),
            df: {
                fieldtype: "Check",
                fieldname: "my_reservations",
                change: function(){
                    if (!frappe.vbz_beratung_termine.no_render_based_on_filter) {
                        frappe.vbz_beratung_termine.reload_view(page);
                    }
                }
            },
            only_input: true
        });
        return my_reservations_field
    },

    create_beratungsort_field: function(page) {
        var beratungsort_field = frappe.ui.form.make_control({
            parent: page.main.find(".beratungsort"),
            df: {
                fieldtype: "Link",
                fieldname: "beratungsort",
                options: "Beratungsort",
                placeholder: "Beratungsort",
                change: function(){
                    if (!frappe.vbz_beratung_termine.no_render_based_on_filter) {
                        frappe.vbz_beratung_termine.reload_view(page);
                    }
                }
            },
            only_input: true
        });
        return beratungsort_field
    },

    create_berater_in_field: function(page) {
        var berater_in_field = frappe.ui.form.make_control({
            parent: page.main.find(".berater_in"),
            df: {
                fieldtype: "Link",
                fieldname: "berater_in",
                options: "Termin Kontaktperson",
                placeholder: "Berater*in",
                change: function(){
                    if (!frappe.vbz_beratung_termine.no_render_based_on_filter) {
                        frappe.vbz_beratung_termine.reload_view(page);
                    }
                }
            },
            only_input: true
        });
        return berater_in_field
    },

    create_art_field: function(page) {
        var art_field = frappe.ui.form.make_control({
            parent: page.main.find(".art"),
            df: {
                fieldtype: "Select",
                fieldname: "art",
                options: "\npersönlich\ntelefonisch",
                placeholder: "Art",
                change: function(){
                    if (!frappe.vbz_beratung_termine.no_render_based_on_filter) {
                        frappe.vbz_beratung_termine.reload_view(page);
                    }
                }
            },
            only_input: true
        });
        return art_field
    },

    create_language_field: function(page) {
        var language_field = frappe.ui.form.make_control({
            parent: page.main.find(".sprache"),
            df: {
                fieldtype: "Link",
                fieldname: "language",
                options: "Language",
                placeholder: "Sprache",
                change: function(){
                    if (!frappe.vbz_beratung_termine.no_render_based_on_filter) {
                        frappe.vbz_beratung_termine.reload_view(page);
                    }
                }
            },
            only_input: true
        });
        return language_field
    },

    create_datum_field: function(page) {
        var datum_field = frappe.ui.form.make_control({
            parent: page.main.find(".datum"),
            df: {
                fieldtype: "Date",
                fieldname: "datum",
                placeholder: "Datum ab",
                change: function(){
                    if (!frappe.vbz_beratung_termine.no_render_based_on_filter) {
                        frappe.vbz_beratung_termine.reload_view(page);
                    }
                }
            },
            only_input: true
        });
        return datum_field
    },

    create_fachskill_field: function(page) {
        var fachskill_field = frappe.ui.form.make_control({
            parent: page.main.find(".fachskill"),
            df: {
                fieldtype: "Link",
                fieldname: "fachskill",
                options: "Fachskill",
                placeholder: "Fachskill",
                change: function(){
                    if (!frappe.vbz_beratung_termine.no_render_based_on_filter) {
                        frappe.vbz_beratung_termine.reload_view(page);
                    }
                }
            },
            only_input: true
        });
        return fachskill_field
    },

    add_click_handlers: function(page) {
        $(".termin-tr").each(function() {
            if ($(this).attr('data-beratung')) {
                $(this).off('click').on('click', function() {
                    if ($(this).attr('data-beratung') != '---') {
                        if ($(this).attr('data-person_ist_eingetroffen') != 1) {
                            const beratung_name = $(this).attr('data-beratung');
                            const d = new frappe.ui.Dialog({
                                title: "Wählen Sie eine Aktion",
                                fields: [
                                    {
                                        fieldtype: "Button",
                                        fieldname: "open",
                                        label: "Beratung öffnen",
                                        click: function() {
                                            d.hide();
                                            frappe.set_route("Form", "Beratung", beratung_name);
                                        }
                                    },
                                    {
                                        fieldtype: "Button",
                                        fieldname: "mark_as_eingetroffen",
                                        label: 'Als "eingetroffen" markieren',
                                        click: function() {
                                            d.hide();
                                            frappe.call({
                                                method: "mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.person_ist_eingetroffen",
                                                args: {
                                                    'beratung': beratung_name
                                                },
                                                async: false,
                                                callback: function(r) {
                                                    frappe.vbz_beratung_termine.reload_view(page);
                                                }
                                            });
                                        }
                                    }
                                ]
                            });
                            d.show();
                        } else {
                            frappe.set_route("Form", "Beratung", $(this).attr('data-beratung'));
                        }
                    } else {
                        if ($(this).attr('data-name_for_reservation') != '---') {
                            const name_for_reservation = $(this).attr('data-name_for_reservation');
                            if ($(this).attr('data-is_reserved') != '1') {
                                frappe.confirm(
                                    'Dieser Termin ist noch frei, möchten Sie eine Proforma-Reservation vornehmen?',
                                    function(){
                                        // on yes
                                        frappe.call({
                                            method: "mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.add_reservation",
                                            args: {
                                                'termin': name_for_reservation
                                            },
                                            async: false,
                                            callback: function(r) {
                                                frappe.vbz_beratung_termine.reload_view(page);
                                            }
                                        });
                                    },
                                    function(){
                                        // on no
                                    }
                                )
                            } else {
                                frappe.confirm(
                                    'Dieser Termin besitzt eine Proforma-Reservation, möchten Sie diese entfernen?',
                                    function(){
                                        // on yes
                                        frappe.call({
                                            method: "mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.remove_reservation",
                                            args: {
                                                'termin': name_for_reservation
                                            },
                                            async: false,
                                            callback: function(r) {
                                                frappe.vbz_beratung_termine.reload_view(page);
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
            }
        });
    },

    open_beratung: function(beratung) {
        frappe.set_route("Form", "Beratung", beratung.beratung);
    }
};

async function poll(page) {
    try {
        if (frappe.get_route_str() !== 'vbz_beratung_termine') return;

        const since = localStorage['datenstand_for_polling'];
        const qty = localStorage['anz_eingetroffen_for_polling']
        const since_res = await fetch(`/api/method/mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.has_changed?since=${since}`);
        const since_data = await since_res.json();

        if (since_data.message > 0) {
            frappe.vbz_beratung_termine.reload_view(page);
        } else {
            const qty_res = await fetch(`/api/method/mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.get_anz_eingetroffen`);
            const qty_data = await qty_res.json();
            if (qty_data.message != qty) {
                frappe.vbz_beratung_termine.reload_view(page);
            }
        }
    } catch (err) {
        console.error(err);
    }

    setTimeout(() => poll(page), 2000);
}