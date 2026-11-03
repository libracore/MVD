{% include "mvd/mvd/doctype/mandat/solifonds_dialoge.js" %}

frappe.pages['vbz-solifonds'].on_page_load = function(wrapper) {
    frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Verarbeitungszentrale',
        single_column: true
    });
}
frappe.pages['vbz-solifonds'].refresh = function(wrapper) {
    frappe.vbz_solifonds.laden(wrapper);
    frappe.dom.unfreeze();
}

frappe.vbz_solifonds = {
    // Reihenfolge: was auf die GL wartet zuerst
    GRUPPEN: [
        {'status': 'Vorgeprüft', 'titel': 'Wartet auf Entscheid GL', 'datum_feld': 'vorgeprueft_am', 'datum_label': 'Vorgeprüft', 'aktion': 'entscheid', 'aktion_label': 'Entscheiden'},
        {'status': 'Antrag Vorstand', 'titel': 'Abstimmung Vorstand läuft', 'datum_feld': 'vorgeprueft_am', 'datum_label': 'Vorgeprüft', 'aktion': 'abstimmung', 'aktion_label': 'Abstimmung abschliessen'},
        {'status': 'Gesuch eingereicht', 'titel': 'Bei der Vorprüfung', 'datum_feld': 'gesuch_eingereicht_am', 'datum_label': 'Eingereicht'},
        {'status': 'Vorgemerkt', 'titel': 'Noch nicht eingereicht', 'datum_feld': 'creation', 'datum_label': 'Erstellt'},
        {'status': 'Unzugewiesen', 'titel': 'VA-Suche läuft (Sekretariat)', 'datum_feld': 'creation', 'datum_label': 'Erstellt'},
        {'status': 'Gutsprache', 'titel': 'Gutsprache erteilt', 'datum_feld': 'entscheid_datum', 'datum_label': 'Entscheid'},
        {'status': 'Abgelehnt', 'titel': 'Abgelehnt', 'datum_feld': 'entscheid_datum', 'datum_label': 'Entscheid'}
    ],
    laden: function(wrapper) {
        frappe.call({
            'method': frappe.mvd.solifonds.METHOD + 'get_dashboard',
            'freeze': true,
            'freeze_message': 'Lade Solidaritätsfonds...',
            'callback': function(r) {
                let mandate = r.message || [];
                let gruppen = frappe.vbz_solifonds.GRUPPEN.map(g => Object.assign({}, g, {
                    'mandate': mandate.filter(m => m.status == g.status)
                }));
                let $body = $(wrapper).find('.layout-main-section');
                $body.html(frappe.render_template('vbz_solifonds', {
                    'datenstand': frappe.datetime.now_datetime().split('.')[0],
                    'gruppen': gruppen
                }));
                frappe.vbz_solifonds.add_click_handlers(wrapper, $body);
            }
        });
    },
    add_click_handlers: function(wrapper, $body) {
        let neu_laden = function() { frappe.vbz_solifonds.laden(wrapper); };
        $body.off('click', '.solifonds-aktion').on('click', '.solifonds-aktion', function() {
            let mandat = $(this).attr('data-mandat');
            if ($(this).attr('data-aktion') == 'entscheid') {
                frappe.mvd.solifonds.entscheid_dialog(mandat, neu_laden);
            } else {
                frappe.confirm(__('Abstimmung für {0} abschliessen? Es gilt die einfache Mehrheit der abgegebenen Stimmen.', [mandat]), function() {
                    frappe.mvd.solifonds.abstimmung_abschliessen(mandat, neu_laden);
                });
            }
        });
    }
}
