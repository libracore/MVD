frappe.pages['rsvmandat-overview'].on_page_load = function(wrapper) {
    var me = this;
    var page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'RSV-Mandat Übersicht',
    single_column: true
    });

    me.page.set_primary_action('RSV-Mitglied Übersicht öffnen', () => {
        frappe.set_route('rsvmitglied-overview');
    });

    $(page.body).html(`
        <div class="rsv-dashboard">
            <div class="rsv-header">
            <div>
                <h2>RSV-Mandat Übersicht</h2>
                <p>Anzahl RSV-Mandate (sowie RSV-Mitglieder) nach Typ der RSV-Mandate</p>
            </div>
            </div>
            <div class="rsv-status-grid" id="rsv-mandat-overview"></div>
        </div>
    `);

    load_rsvmandat_typ_counts();
};


function load_rsvmandat_typ_counts() {
    frappe.call({
        method: 'mvd.mvd.page.rsvmandat_overview.rsvmandat_overview.get_rsvmandat_typ_counts',
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
                            <a href="#" class="rsv-card-link js-show-mitglieder">
                                RSV-Mitglieder anzeigen
                            </a>
                            <a href="#" class="rsv-card-link js-show-mandate">
                                RSV-Mandate anzeigen
                            </a>
                        </div>
                    </div>
                `;
            });

            $('#rsv-mandat-overview').html(html);

            $('.js-show-mitglieder').on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                let listen = JSON.parse(decodeURIComponent(
                    $(this).closest('.rsv-card').attr('data-listen') || '[]'
                ));

                frappe.route_options = {rsvmandat: ['in', listen]};

                frappe.set_route('List', 'RSVMitglied');
            });


            $('.js-show-mandate').on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                let typ = $(this).closest('.rsv-card').attr('data-typ');

                frappe.route_options = {typ: typ};

                frappe.set_route('List', 'RSVMandat');
            });
        }
    });
}