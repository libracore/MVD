frappe.pages['rsvmandat-overview'].on_page_load = function(wrapper) {
    var me = this;
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'RSV Mandate Übersicht',
        single_column: true
    });

    me.page.set_primary_action('RSV Mandatslisten Übersicht öffnen', () => {
        frappe.set_route('rsvmandatsliste-over');
    });

    prepare_page(page);
};

frappe.pages['rsvmandat-overview'].refresh= function(wrapper){
    frappe.dom.unfreeze();
} 

function prepare_page(page) {
    $(page.body).html(`
        <div class="rsv-dashboard">
            <div class="rsv-header">
            <div>
                <h2>RSV-Mandate Übersicht</h2>
                <p>Status-Verteilung aller RSV-Mandate</p>
            </div>
            </div>
            <div class="rsv-status-grid" id="rsv-status-overview"></div>
        </div>
    `);

    load_rsv_status_counts();
    frappe.dom.unfreeze();
}

function load_rsv_status_counts() {
    frappe.call({
        method: 'mvd.mvd.page.rsvmandat_overview.rsvmandat_overview.get_rsvmandat_status_counts',
        callback: function(r) {
            let data = r.message || [];
            let html = '';

            const statusColors = {
                'Provisorisch': '#94a3b8',
                'Vorprüfung': '#0ea5e9',
                'Geprüft': '#6366f1',
                'manuelle Vergabe': '#8b5cf6',
                'Eingereicht': '#f59e0b',
                'Vergeben': '#10b981',
                'Abgelehnt': '#ef4444',
                'Abgeschlossen': '#059669',
                'Rückzug': '#78716c',
                'keine Antwort': '#f97316',
                'Doppelversicherung': '#dc2626',
                'Ohne Status': '#6b7280'
            };

            data.forEach(function(row) {
                let status = row.status || 'Ohne Status';
                let count = row.count || 0;

                let color = statusColors[status] || '#4f46e5';

                html += `
                    <div 
                        class="rsv-card rsv-clickable-card"
                        data-status="${frappe.utils.escape_html(status)}"
                        style="border-left-color: ${color}; background: ${color}12;"
                    >
                        <div 
                            class="rsv-card-title"
                            style="color: ${color};"
                        >
                            ${frappe.utils.escape_html(status)}
                        </div>
                        <div class="rsv-card-count">
                            ${count}
                        </div>
                        <div class="rsv-card-footer">
                            Mandate anzeigen
                        </div>
                    </div>
                `;
            });

            $('#rsv-status-overview').html(html);

            $('.rsv-clickable-card').on('click', function() {
                let status = $(this).data('status');
                frappe.route_options = {status: status};
                frappe.set_route('List', 'RSVMandat');
            });
        }
    });
}