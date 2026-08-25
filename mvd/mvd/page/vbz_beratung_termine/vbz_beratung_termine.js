frappe.pages["vbz_beratung_termine"].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Verarbeitungszentrale",
        single_column: true
    });

    frappe.vbz_beratung_termine.initialize(page);
};

frappe.pages["vbz_beratung_termine"].refresh = function() {
    if (frappe.vbz_beratung_termine.page) {
        frappe.vbz_beratung_termine.start_polling();
    }
};

frappe.vbz_beratung_termine = {
    page: null, // Referenz auf das von frappe.ui.make_app_page() erzeugte Seitenobjekt
    first_load: true, // Kennzeichnet den allerersten Datenabruf. Dabei wird der sektionabhängige Defaultfilter gesetzt.
    default_sektion: null, // User Standardsektion
    filter_values: null, // Filterzustand ausserhalb der UI-Controls
    filter_reload_timer: null, // Timer für das Bündeln mehrfacher Filter-Change-Events
    suppress_filter_change: false, // Unterdrückt Change-Events von set_value()
    is_loading: false, // Flag ob get_open_data() momentan läuft
    reload_requested: false, // Merkt einen weiteren Reload vor, falls während eines laufenden Requests erneut eine Aktualisierung verlangt wird.
    is_mutating: false, // Sperre für schreibende Aktionen wie Reservationen oder als "eingetroffen" markieren
    poll_timer: null, // ID des aktuell geplanten Polling-Timers
    poll_interval: 2000, // Polling-Intervall in ms
    last_data_signature: null, // Signatur der zuletzt tatsächlich gerenderten Daten
    filter_is_active: false, // Flag ob gerade ein Filter-Control aktiv bedient wird
    pending_poll_result: null, // Zwischenspeicher für ein Polling-Resultat während einer aktiven Filtereingabe

    /*
        Vergleichswerte der zuletzt gerenderten, gefilterten Ergebnismenge.
        Beim Polling werden diese Werte mit einem neuen Aufruf von
        get_open_data() unter identischen Filtern verglichen.
     */
    polling_state: {
        datenstand: null,
        anz_eingetroffen: null
    },
    initialize: async function(page) {
        this.page = page;

        this.stop_polling();
        this.clear_filter_reload_timer();

        this.first_load = true;
        this.default_sektion = null;
        this.filter_values = null;
        this.is_loading = false;
        this.reload_requested = false;
        this.is_mutating = false;
        this.last_data_signature = null;
        this.filter_is_active = false;
        this.pending_poll_result = null;

        this.polling_state = {
            datenstand: null,
            anz_eingetroffen: null
        };

        try {
            const response = await this.call({
                method: "mvd.mvd.utils.mvd_bootinfo.get_default_sektion"
            });

            this.default_sektion = response.message[0] || null;
            
            await this.render_view();
            this.start_polling();
        } catch (error) {
            this.handle_error(
                error,
                "Die Verarbeitungszentrale konnte nicht geladen werden."
            );
        }
    },
    call: function(options) {
        // Promise-Wrapper für frappe.call()
        return new Promise(function(resolve, reject) {
            frappe.call({
                method: options.method,
                args: options.args || {},
                freeze: options.freeze === true,
                freeze_message: options.freeze_message,

                callback: function(response) {
                    resolve(response);
                },

                error: function(error) {
                    reject(error);
                }
            });
        });
    },
    get_filter_value: function(fieldname, fallback) {
        // Liest den Wert eines Filter-Controls
        // Existiert das Control noch nicht oder ist sein Wert leer, wird der angegebene Fallback zurückgegeben.
        const page = this.page;

        if (
            !page ||
            !page.filter_fields ||
            !page.filter_fields[fieldname]
        ) {
            return fallback;
        }

        const value = page.filter_fields[fieldname].get_value();

        if (
            value === undefined ||
            value === null ||
            value === ""
        ) {
            return fallback;
        }

        return value;
    },
    read_filter_values_from_controls: function() {
        // Liest den aktuellen Filterzustand aus den sichtbaren Frappe-Controls (inkl. Fallbacks)
        return {
            free_only: this.get_filter_value(
                "free_only_field",
                "0"
            ),

            termine_heute: this.get_filter_value(
                "termine_heute_field",
                "0"
            ),

            termine_gebucht: this.get_filter_value(
                "termine_gebucht_field",
                "0"
            ),

            beratungsort: this.get_filter_value(
                "beratungsort_field",
                ""
            ),

            berater_in: this.get_filter_value(
                "berater_in_field",
                ""
            ),

            art: this.get_filter_value(
                "art_field",
                "Art"
            ),

            datum: this.get_filter_value(
                "datum_field",
                ""
            ),

            datum_bis: this.get_filter_value(
                "datum_bis_field",
                ""
            ),

            language: this.get_filter_value(
                "language_field",
                ""
            ),

            fachskill: this.get_filter_value(
                "fachskill_field",
                ""
            ),

            geschaeftsstelle: this.get_filter_value(
                "geschaeftsstelle_field",
                "Geschäftsstelle"
            ),

            my_reservations_only: this.get_filter_value(
                "my_reservations_field",
                "0"
            ),

            beratungstyp: this.get_filter_value(
                "beratungstyp_field",
                "Beratungstyp"
            ),

            chronologische_termine: this.get_filter_value(
                "chronologische_termine_field",
                "0"
            )
        };
    },
    get_filter_values: function() {
        // Liefert den Filterzustand für den nächsten Datenabruf
        // Beim allerersten Laden wird für MVZH automatisch free_only = "1" und chronologische_termine = "1" gesetzt
        if (this.filter_values) {
            return Object.assign({}, this.filter_values);
        }

        const filter_values =
            this.read_filter_values_from_controls();

        if (
            this.first_load &&
            this.default_sektion === "MVZH"
        ) {
            filter_values.free_only = "1";
            filter_values.chronologische_termine = "1";
        }

        this.filter_values = Object.assign(
            {},
            filter_values
        );

        return filter_values;
    },
    render_view: async function() {
        /*
            Lädt die aktuellen Daten vom Server und rendert danach die Seite
            Schutz vor parallelen Requests:
            - Läuft bereits ein Render-Request, wird nur das Flag reload_requested gesetzt
            - Nach Abschluss wird genau ein zusätzlicher Reload ausgeführt
        */
        if (!this.page) {
            return;
        }

        // ggf. Reload vormerkung
        if (this.is_loading) {
            this.reload_requested = true;
            return;
        }

        this.is_loading = true;

        const filter_values = this.get_filter_values();
        const is_initial_render = this.first_load;

        try {
            const response = await this.call({
                method: "mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.get_open_data",
                args: filter_values,
                freeze: true,
                freeze_message: "Lade Beratungsterminübersicht..."
            });

            if (!response.message) {
                return;
            }

            // Sicherung Filterzustand
            this.filter_values = Object.assign(
                {},
                filter_values
            );

            this.render_result(
                response.message,
                filter_values
            );

            if (is_initial_render) {
                this.first_load = false;
            }
        } catch (error) {
            this.handle_error(
                error,
                "Die Beratungstermine konnten nicht geladen werden."
            );
        } finally {
            this.is_loading = false;

            // ggf. Durchführung des angeforderten Reload
            if (this.reload_requested) {
                this.reload_requested = false;
                await this.render_view();
            }
        }
    },
    render_result: function(data, filter_values) {
        /*
            Diese Funktion rendert das HTML Template mit den Daten von get_open_data()
            Das Template besteht aus zwei getrennten Bereichen:
            - .vbz-filter-container
            - .vbz-data-container
            Beim ersten Render wird das vollständige Template in page.main eingesetzt und die Filter-Controls werden erzeugt.
            Bei Filteränderungen, Reservationen und Polling wird nur der Inhalt von .vbz-data-container ersetzt.
        */
        const page = this.page;

        const rendered_html = frappe.render_template(
            "vbz_beratung_termine",
            data
        );

        const $rendered = $("<div>")
            .html(rendered_html);

        const $existing_filter_container =
            $(page.main).find(
                ".vbz-filter-container"
            );

        const $existing_data_container =
            $(page.main).find(
                ".vbz-data-container"
            );

        const $new_data_container =
            $rendered.find(
                ".vbz-data-container"
            );

        
        if (
            $existing_filter_container.length === 0 ||
            $existing_data_container.length === 0
        ) {
            // vollständiges Template Rendering
            $(page.main).empty().html(
                rendered_html
            );

            // Filteraufbau
            this.create_filter_fields(
                filter_values
            );

            this.add_filter_focus_handlers();
        } else {
            // Nur aktualisierung der Daten
            $existing_data_container.html(
                $new_data_container.html()
            );
        }

        // Datenstand aktualisieren
        $(page.main)
            .find("#datenstand_as")
            .text(
                "Datenstand: " +
                (data.datenstand_as || "")
            );

        // Click-Handler für Terminzeilen
        this.add_click_handlers();

        // Speichern der Polling-Vergleichswerte
        this.polling_state.datenstand =
            data.datenstand_for_polling;

        this.polling_state.anz_eingetroffen =
            data.anz_eingetroffen_for_polling;

        // Signatur des dargestellten Inhalts speichern
        this.last_data_signature =
            this.get_data_signature(data);

        // Reset eines ggf. vorgemerkten Polling-Resultat
        this.pending_poll_result = null;
    },
    reload_view: function() {
        return this.render_view();
    },
    get_filter_definitions: function() {
        // Zentrale Konfiguration sämtlicher Filterfelder
        return [
            {
                property_name: "free_only_field",
                value_name: "free_only",
                parent_selector: ".free_only",
                fieldtype: "Check",
                fieldname: "free_only",
                label: "Nur freie und reservierte Termine"
            },
            {
                property_name: "termine_heute_field",
                value_name: "termine_heute",
                parent_selector: ".termine_heute",
                fieldtype: "Check",
                fieldname: "termine_heute",
                label: "Nur Termine von Heute"
            },
            {
                property_name: "termine_gebucht_field",
                value_name: "termine_gebucht",
                parent_selector: ".termine_gebucht",
                fieldtype: "Check",
                fieldname: "termine_gebucht",
                label: "Nur gebuchte Termine"
            },
            {
                property_name: "beratungsort_field",
                value_name: "beratungsort",
                parent_selector: ".beratungsort",
                fieldtype: "Link",
                fieldname: "beratungsort",
                options: "Beratungsort",
                placeholder: "Beratungsort"
            },
            {
                property_name: "berater_in_field",
                value_name: "berater_in",
                parent_selector: ".berater_in",
                fieldtype: "Link",
                fieldname: "berater_in",
                options: "Termin Kontaktperson",
                placeholder: "Berater*in"
            },
            {
                property_name: "art_field",
                value_name: "art",
                parent_selector: ".art",
                fieldtype: "Select",
                fieldname: "art",
                options: "Art\npersönlich\ntelefonisch",
                placeholder: "Art"
            },
            {
                property_name: "datum_field",
                value_name: "datum",
                parent_selector: ".datum",
                fieldtype: "Date",
                fieldname: "datum",
                placeholder: "Datum ab"
            },
            {
                property_name: "datum_bis_field",
                value_name: "datum_bis",
                parent_selector: ".datum_bis",
                fieldtype: "Date",
                fieldname: "datum_bis",
                placeholder: "Datum bis"
            },
            {
                property_name: "language_field",
                value_name: "language",
                parent_selector: ".sprache",
                fieldtype: "Link",
                fieldname: "language",
                options: "Language",
                placeholder: "Sprache"
            },
            {
                property_name: "fachskill_field",
                value_name: "fachskill",
                parent_selector: ".fachskill",
                fieldtype: "Link",
                fieldname: "fachskill",
                options: "Fachskill",
                placeholder: "Fachskill"
            },
            {
                property_name: "my_reservations_field",
                value_name: "my_reservations_only",
                parent_selector: ".my_reservations",
                fieldtype: "Check",
                fieldname: "my_reservations",
                label: "Nur meine reservierten Termine"
            },
            {
                property_name: "beratungstyp_field",
                value_name: "beratungstyp",
                parent_selector: ".beratungstyp",
                fieldtype: "Select",
                fieldname: "beratungstyp",
                options: "Beratungstyp\nPrivat\nGeschäft",
                placeholder: "Beratungstyp"
            },
            {
                property_name: "chronologische_termine_field",
                value_name: "chronologische_termine",
                parent_selector: ".chronologische_termine",
                fieldtype: "Check",
                fieldname: "chronologische_termine",
                label: "Termine chronologisch sortieren"
            },
            {
                property_name: "geschaeftsstelle_field",
                value_name: "geschaeftsstelle",
                parent_selector: ".geschaeftsstelle",
                fieldtype: "Select",
                fieldname: "geschaeftsstelle",
                options: "Geschäftsstelle\nZürich\nWinterthur",
                placeholder: "Geschäftsstelle"
            }
        ];
    },
    create_filter_fields: function(filter_values) {
        // Erstellt nach jedem Template-Render sämtliche Filter-Controls neu und stellt deren vorherige Werte wieder her
        const page = this.page;

        page.filter_fields = {};
        this.suppress_filter_change = true;

        const definitions = this.get_filter_definitions();

        definitions.forEach((definition) => {
            const field = this.create_filter_field(
                definition
            );

            page.filter_fields[
                definition.property_name
            ] = field;

            const value =
                filter_values[definition.value_name];

            field.set_value(value);
            field.refresh();

            if (
                definition.label &&
                field.label_span
            ) {
                $(field.label_span).html(
                    definition.label
                );
            }
        });

        this.filter_values = Object.assign(
            {},
            filter_values
        );

        window.setTimeout(() => {
            this.suppress_filter_change = false;
        }, 100);
    },
    create_filter_field: function(definition) {
        // Erstellt ein Frappe-Control
        const page = this.page;

        const field_definition = {
            fieldtype: definition.fieldtype,
            fieldname: definition.fieldname,

            change: () => {
                this.handle_filter_change();
            }
        };

        if (definition.options !== undefined) {
            field_definition.options =
                definition.options;
        }

        if (definition.placeholder !== undefined) {
            field_definition.placeholder =
                definition.placeholder;
        }

        return frappe.ui.form.make_control({
            parent: $(page.main).find(
                definition.parent_selector
            ),
            df: field_definition,
            only_input: true
        });
    },
    handle_filter_change: function() {
        // Filter-Change Handler
        if (this.suppress_filter_change) {
            return;
        }

        this.clear_filter_reload_timer();

        this.filter_reload_timer = window.setTimeout(
            () => {
                this.filter_reload_timer = null;

                const new_filter_values =
                    this.read_filter_values_from_controls();

                if (
                    this.filter_values_are_equal(
                        new_filter_values,
                        this.filter_values
                    )
                ) {
                    return;
                }

                this.filter_values = Object.assign(
                    {},
                    new_filter_values
                );

                this.reload_view();
            },
            150
        );
    },
    clear_filter_reload_timer: function() {
        // Löscht einen noch ausstehenden Filter-Debounce-Timer sodass immer nur ein geplanter Filter-Reload vorhanden ist
        if (this.filter_reload_timer) {
            window.clearTimeout(
                this.filter_reload_timer
            );

            this.filter_reload_timer = null;
        }
    },
    filter_values_are_equal: function(values_a, values_b) {
        // Vergleicht zwei Filterzustände um änderungen zu erkennen
        if (!values_a || !values_b) {
            return false;
        }

        const keys = [
            "free_only",
            "termine_heute",
            "termine_gebucht",
            "beratungsort",
            "berater_in",
            "art",
            "datum",
            "datum_bis",
            "language",
            "fachskill",
            "my_reservations_only",
            "beratungstyp",
            "chronologische_termine",
            "geschaeftsstelle"
        ];

        return keys.every(function(key) {
            return String(values_a[key] || "") ===
                String(values_b[key] || "");
        });
    },
    get_data_signature: function(data) {
        // Erstellt eine Vergleichssignatur
        if (!data) {
            return "";
        }

        const comparable_data = Object.assign({}, data);

        delete comparable_data.datenstand_for_polling;
        delete comparable_data.anz_eingetroffen_for_polling;

        return JSON.stringify(comparable_data);
    },
    add_filter_focus_handlers: function() {
        // Registriert Fokus-Handler für alle Filter-Controls
        const $main = $(this.page.main);

        // Verhinderung Mehrfachregistrierungen.
        $main.off(".vbz_filter_focus");

        $main.on(
            "focusin.vbz_filter_focus",
            ".frappe-control input, .frappe-control select, .frappe-control textarea",
            () => {
                this.filter_is_active = true;
            }
        );

        $main.on(
            "focusout.vbz_filter_focus",
            ".frappe-control input, .frappe-control select, .frappe-control textarea",
            () => {
                window.setTimeout(() => {
                    const active_element =
                        document.activeElement;

                    const $active_element =
                        $(active_element);

                    const still_inside_page =
                        $active_element.closest(
                            this.page.main
                        ).length > 0;

                    const still_inside_filter =
                        $active_element.closest(
                            ".frappe-control"
                        ).length > 0;

                    this.filter_is_active =
                        still_inside_page &&
                        still_inside_filter;
                    
                    if (
                        !this.filter_is_active &&
                        this.pending_poll_result
                    ) {
                        const pending =
                            this.pending_poll_result;

                        this.pending_poll_result = null;

                        this.render_result(
                            pending.data,
                            pending.filter_values
                        );
                    }
                }, 100);
            }
        );
    },
    add_click_handlers: function() {
        // Registriert einen delegierten Click-Handler in page.main
        const $main = $(this.page.main);

        $main.off(
            "click.vbz_beratung_termine",
            ".termin-tr"
        );

        $main.on(
            "click.vbz_beratung_termine",
            ".termin-tr",
            (event) => {
                this.handle_termin_click(event);
            }
        );
    },
    handle_termin_click: function(event) {
        // Definiert anhand der data-Attribute, welche Aktion beim Klick auf eine Terminzeile ausgeführt werden soll
        if ($(event.target).closest("a, button").length) {
            return;
        }

        const $row = $(event.currentTarget);
        const beratung = $row.attr("data-beratung");

        if (!beratung) {
            return;
        }

        if (beratung !== "---") {
            this.handle_existing_beratung(
                $row,
                beratung
            );

            return;
        }

        this.handle_reservation($row);
    },
    handle_existing_beratung: function($row, beratung) {
        const person_ist_eingetroffen =
            $row.attr(
                "data-person_ist_eingetroffen"
            ) === "1";

        if (person_ist_eingetroffen) {
            this.open_beratung_in_new_tab(
                beratung
            );

            return;
        }

        this.show_beratung_action_dialog(
            beratung
        );
    },
    show_beratung_action_dialog: function(beratung) {
        const dialog = new frappe.ui.Dialog({
            title: "Wählen Sie eine Aktion",

            fields: [
                {
                    fieldtype: "Button",
                    fieldname: "open",
                    label: "Beratung öffnen",

                    click: () => {
                        dialog.hide();

                        this.open_beratung_in_new_tab(
                            beratung
                        );
                    }
                },
                {
                    fieldtype: "Button",
                    fieldname: "mark_as_eingetroffen",
                    label: 'Als "eingetroffen" markieren',

                    click: () => {
                        dialog.hide();

                        this.run_action({
                            method: "mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.person_ist_eingetroffen",

                            args: {
                                beratung: beratung
                            },

                            freeze_message:
                                'Person wird als "eingetroffen" markiert...'
                        });
                    }
                }
            ]
        });

        dialog.show();
    },
    handle_reservation: function($row) {
        // Abfrage Proforma-Reservation
        const termin = $row.attr(
            "data-name_for_reservation"
        );

        if (!termin || termin === "---") {
            return;
        }

        const is_reserved =
            $row.attr("data-is_reserved") === "1";

        if (is_reserved) {
            this.confirm_remove_reservation(
                termin
            );
        } else {
            this.confirm_add_reservation(
                termin
            );
        }
    },
    confirm_add_reservation: function(termin) {
        frappe.confirm(
            "Dieser Termin ist noch frei, möchten Sie eine Proforma-Reservation vornehmen?",

            () => {
                this.run_action({
                    method: "mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.add_reservation",

                    args: {
                        termin: termin
                    },

                    freeze_message:
                        "Proforma-Reservation wird erstellt..."
                });
            }
        );
    },
    confirm_remove_reservation: function(termin) {
        frappe.confirm(
            "Dieser Termin besitzt eine Proforma-Reservation, möchten Sie diese entfernen?",

            () => {
                this.run_action({
                    method: "mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.remove_reservation",

                    args: {
                        termin: termin
                    },

                    freeze_message:
                        "Proforma-Reservation wird entfernt..."
                });
            }
        );
    },
    run_action: async function(options) {
        if (this.is_mutating) {
            return;
        }

        this.is_mutating = true;

        try {
            await this.call({
                method: options.method,
                args: options.args,

                freeze: true,
                freeze_message:
                    options.freeze_message ||
                    "Bitte warten..."
            });

            await this.reload_view();
        } catch (error) {
            this.handle_error(
                error,
                "Die Aktion konnte nicht ausgeführt werden."
            );
        } finally {
            this.is_mutating = false;
        }
    },
    open_beratung_in_new_tab: function(beratung) {
        const url =
            "/desk#Form/Beratung/" +
            encodeURIComponent(beratung);

        window.open(url, "_blank");
    },
    start_polling: function() {
        this.stop_polling();

        if (!this.is_current_route()) {
            return;
        }

        this.schedule_next_poll();
    },
    schedule_next_poll: function() {
        this.stop_polling();

        this.poll_timer = window.setTimeout(
            async () => {
                await this.poll();
            },
            this.poll_interval
        );
    },
    stop_polling: function() {
        if (this.poll_timer) {
            window.clearTimeout(
                this.poll_timer
            );

            this.poll_timer = null;
        }
    },
    is_current_route: function() {
        return (
            frappe.get_route_str() ===
            "vbz_beratung_termine"
        );
    },

    poll: async function() {
        if (!this.is_current_route()) {
            this.stop_polling();
            return;
        }

        try {
            if (
                !this.is_loading &&
                !this.is_mutating
            ) {
                await this.poll_once();
            }
        } catch (error) {
            console.error(
                "Fehler beim Polling der Beratungstermine:",
                error
            );
        } finally {
            if (this.is_current_route()) {
                this.schedule_next_poll();
            }
        }
    },
    poll_once: async function() {
        // Prüft ob sich die DB-Daten und "sichtbaren"-Daten unterscheiden
        const filter_values = this.get_filter_values();

        const response = await this.call({
            method: "mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.get_open_data",

            args: filter_values
        });

        if (!response.message) {
            return;
        }

        const new_signature =
            this.get_data_signature(
                response.message
            );

        //Daten sind unverändert
        if (
            new_signature ===
            this.last_data_signature
        ) {
            return;
        }

        // Zwischenspeicherung der neuen Daten bis Filtereingabe beendet
        if (this.filter_is_active) {
            this.pending_poll_result = {
                data: response.message,

                filter_values: Object.assign(
                    {},
                    filter_values
                )
            };

            return;
        }

        // Aktualisieren der Daten
        this.render_result(
            response.message,
            filter_values
        );
    },
    handle_error: function(error, message) {
        console.error(message, error);

        frappe.msgprint({
            title: "Fehler",
            indicator: "red",
            message: message
        });
    }
};
