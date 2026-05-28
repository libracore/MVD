frappe.pages['rsvmandatsliste-over'].on_page_load = function(wrapper) {
    var me = this;
    var page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'RSV Mandatslisten Übersicht',
    single_column: true
    });

    me.page.set_primary_action('RSV Mandate Übersicht öffnen', () => {
        frappe.set_route('rsvmandat-overview');
    });

    $(page.body).html(`
        <div class="rsv-dashboard">
            <div class="rsv-header">
            <div>
                <h2>RSV Mandatslisten Übersicht</h2>
                <p>Anzahl RSV-Mandatslisten (sowie RSV-Mandate) nach Typ der RSV-Mandatslisten</p>
            </div>
            </div>
            <div class="rsv-status-grid" id="rsv-mandatsliste-overview"></div>
        </div>
    `);

    load_rsvmandatsliste_typ_counts();
};


function load_rsvmandatsliste_typ_counts() {
    frappe.call({
        method: 'mvd.mvd.page.rsvmandatsliste_over.rsvmandatsliste_over.get_rsvmandatsliste_typ_counts',
        callback: function(r) {
            let data = r.message || [];
            let html = '';

            const typColors = {
            'EM': '#3b82f6',   // blau
            'KGM': '#f59e0b',  // orange
            'GGM': '#10b981',  // grün
            'Ohne Typ': '#6b7280'
            };

            data.forEach(function(row) {
                let typ = row.typ || 'Ohne Typ';
                let listenCount = row.listen_count || 0;
                let mandatCount = row.mandat_count || 0;

                let color = typColors[typ] || '#4f46e5';
                let listen = row.listen ? row.listen.split(',') : [];

                html += `
                    <div
                        class="rsv-card"
                        data-typ="${frappe.utils.escape_html(typ)}"
                        data-listen="${encodeURIComponent(JSON.stringify(listen))}"
                        style="border-left-color: ${color};background: ${color}12;"
                    >
                        <div
                            class="rsv-card-title"
                            style="color: ${color};"
                        >
                            ${frappe.utils.escape_html(typ)}
                        </div>
                        <div class="rsv-card-count">
                            ${listenCount}
                            <span class="rsv-card-subcount">
                                (${mandatCount})
                            </span>
                        </div>
                        <div class="rsv-card-actions">
                            <a href="#" class="rsv-card-link js-show-mandate">
                                Mandate anzeigen
                            </a>
                            <a href="#" class="rsv-card-link js-show-listen">
                                Mandatslisten anzeigen
                            </a>
                        </div>
                    </div>
                `;
            });

            $('#rsv-mandatsliste-overview').html(html);

            $('.js-show-mandate').on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                let listen = JSON.parse(decodeURIComponent(
                    $(this).closest('.rsv-card').attr('data-listen') || '[]'
                ));

                frappe.route_options = {rsvmandatsliste: ['in', listen]};

                frappe.set_route('List', 'RSVMandat');
            });


            $('.js-show-listen').on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                let typ = $(this).closest('.rsv-card').attr('data-typ');

                frappe.route_options = {typ: typ};

                frappe.set_route('List', 'RSVMandatsliste');
            });
        }
    });
}