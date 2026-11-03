frappe.pages['vbz-mandate'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Verarbeitungszentrale',
        single_column: true
    });
    frappe.vbz_mandate.add_views(page);
}
frappe.pages['vbz-mandate'].refresh = function(wrapper){
    frappe.vbz_mandate.show_view('vbz_mandate');
    frappe.dom.unfreeze();
}

frappe.vbz_mandate = {
    add_views: function(page) {
        frappe.call({
            'method': "mvd.mvd.page.vbz_mandate.vbz_mandate.get_status_uebersicht",
            'args': {},
            'freeze': true,
            'freeze_message': 'Lade Mandate...',
            'async': false,
            'callback': function(r)
            {
                if (r.message) {
                    page.add_view('vbz_mandate', frappe.render_template("vbz_mandate", r.message));
                    frappe.vbz_mandate.add_click_handlers();
                }
            }
        });
    },
    show_view: function(view) {
        cur_page.page.page.set_view(view);
    },
    add_click_handlers: function() {
        // Klick auf die Zeile: Listenansicht Mandat mit Statusfilter (alle Typen), Total-Zeile ohne Statusfilter
        // Klick auf eine Zahl: zusätzlich mit Filter auf den Typ der Spalte
        // Zeilen und Zahlen mit 0 sowie Zeilen ohne Status sind nicht klickbar (siehe vbz_mandate.html)
        $("#table_mandat_uebersicht").on("click", "tr.mandat-status", function(e) {
            var route_options = {};
            if (!$(this).attr("data-alle")) {
                route_options["status"] = $(this).attr("data-status");
            }
            var zelle = $(e.target).closest("td.mandat-anzahl");
            if (zelle.length) {
                var typ = zelle.attr("data-typ");
                // "ist nicht gesetzt" geht bei Select-Feldern in der Filterleiste verloren (ergibt "is ''" -> SQL-Fehler)
                route_options["typ"] = typ ? typ : ['not in', ['Rechtsschutzversicherung', 'Solidaritätsfonds']];
            }
            // Ohne Filter würde die Liste die zuletzt gespeicherten Filter behalten
            if ($.isEmptyObject(route_options)) {
                route_options["name"] = ['is', 'set'];
            }
            frappe.route_options = route_options;
            frappe.set_route("List", "Mandat", "List");
        });
    }
}
