frappe.pages['rsvmitglied-overview'].on_page_load = function(wrapper) {
    var me = this;
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'RSV Mitglied Übersicht',
        single_column: true
    });

    me.page.set_primary_action('RSV-Mitglied Übersicht öffnen', () => {
        frappe.set_route('rsvmandat-overview');
    });

    prepare_page(page);
};

frappe.pages['rsvmitglied-overview'].refresh= function(wrapper){
    frappe.dom.unfreeze();
} 

function prepare_page(page) {
    $(page.body).html(`
        <div class="rsv-dashboard">
            <div class="rsv-header">
            <div>
                <h2>RSV-Mitglieder Übersicht</h2>
                <p>Status-Verteilung aller RSV-Mitglieder</p>
            </div>
            </div>
            <div class="rsv-status-grid" id="rsv-status-overview"></div>
            <div class="rsv-linklist">
                <ul>
                    <li><span class="indicator blue"><a href="/desk#List/RSVMandat/Report/Mandatsvergabe">Mandatsvergabe</a></span></li>
                </ul>
            </div>
        </div>
    `);

    load_rsv_status_counts();
    frappe.dom.unfreeze();
}

function load_rsv_status_counts() {
    frappe.call({
        method: 'mvd.mvd.page.rsvmitglied_overview.rsvmitglied_overview.get_rsvmitglied_status_counts',
        callback: function(r) {
            let status_data = r.message.status_counts || [];
            let new_entries = r.message.neue_rsvmitglieder || 0;
            let html = '';

            // Neue Einträge
            html += `
                <div 
                    class="rsv-card rsv-clickable-card"
                    data-status="Neue-Einträge"
                    style="border-left-color: #4f46e5; background: #4f46e512;"
                >
                    <div 
                        class="rsv-card-title"
                        style="color: #4f46e5;"
                    >
                        Neue
                    </div>
                    <div class="rsv-card-count">
                        ${new_entries}
                    </div>
                    <div class="rsv-card-footer">
                        Mandate anzeigen
                    </div>
                </div>
            `;

            const statusColors = {
                'Provisorisch EM': '#94a3b8',
                'Provisorisch GM': '#83c5e3',
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

            status_data.forEach(function(row) {
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
                if (status != 'Neue-Einträge') {
                    frappe.route_options = {status: status};
                    frappe.set_route('List', 'RSVMitglied');
                } else {
                    frappe.route_options = {status: ['in', ['Provisorisch EM','Provisorisch GM']], rsvmandat: ['is', 'not set']};
                    frappe.set_route('List', 'RSVMitglied');
                }
            });
        }
    });
}