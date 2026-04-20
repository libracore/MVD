frappe.pages['vbz_beratung_termine'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Verarbeitungszentrale',
        single_column: true
    });

    frappe.vbz_beratung_termine.page = page;
    frappe.vbz_beratung_termine.render_view(page);
    poll(page);
};

frappe.pages['vbz_beratung_termine'].refresh = function(wrapper) {
    frappe.dom.unfreeze();
};

frappe.vbz_beratung_termine = {
    page: null,

    render_view: function(page) {
        frappe.call({
            method: "mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.get_open_data",
            args: {},
            freeze: true,
            freeze_message: 'Lade Verarbeitungszentrale...',
            async: false,
            callback: function(r) {
                if (r.message) {
                    const html = frappe.render_template("vbz_beratung_termine", r.message);

                    // Alten Inhalt entfernen und neu rendern
                    $(page.main).empty().html(html);

                    frappe.vbz_beratung_termine.add_click_handlers(page);
                    localStorage['datenstand_for_polling'] = r.message.datenstand_for_polling;
                }

                frappe.dom.unfreeze();
            }
        });
    },

    reload_view: function(page) {
        this.render_view(page);
    },

    add_click_handlers: function(page) {
        $(".termin-tr").each(function() {
            if ($(this).attr('data-beratung')) {
                $(this).off('click').on('click', function() {
                    if ($(this).attr('data-beratung') != '---') {
                        frappe.set_route("Form", "Beratung", $(this).attr('data-beratung'));
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
        const res = await fetch(`/api/method/mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.has_changed?since=${since}`);
        const data = await res.json();

        if (data.message > 0) {
            frappe.vbz_beratung_termine.reload_view(page);
        }
    } catch (err) {
        console.error(err);
    }

    setTimeout(() => poll(page), 2000);
}