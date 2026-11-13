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
    // Gruppen (je Status eine aufklappbare Tabelle). aktion: Knopf in der Zeile, nur für die GL (Server prüft zusätzlich).
    GRUPPEN: {
        'Gesuch eingereicht': {'titel': 'Wartet auf Vorprüfung', 'datum_feld': 'gesuch_eingereicht_am', 'datum_label': 'Eingereicht'},
        'Vorgeprüft': {'titel': 'Vorgeprüft, wartet auf Entscheid GL', 'datum_feld': 'vorgeprueft_am', 'datum_label': 'Vorgeprüft', 'aktion': 'entscheid', 'aktion_label': 'Entscheiden'},
        'Antrag Vorstand': {'titel': 'Abstimmung Vorstand läuft', 'datum_feld': 'vorgeprueft_am', 'datum_label': 'Vorgeprüft', 'aktion': 'abstimmung', 'aktion_label': 'Abstimmung abschliessen'},
        'Vorgemerkt': {'titel': 'Noch nicht eingereicht', 'datum_feld': 'creation', 'datum_label': 'Erstellt'},
        'Unzugewiesen': {'titel': 'VA-Suche läuft (Sekretariat)', 'datum_feld': 'creation', 'datum_label': 'Erstellt'},
        'Nicht vergeben': {'titel': 'Nicht vergeben (keine VA gefunden)', 'datum_feld': 'creation', 'datum_label': 'Erstellt'},
        'Laufend (Solifonds)': {'titel': 'Laufend (Kostengutsprache erteilt)', 'datum_feld': 'entscheid_datum', 'datum_label': 'Entscheid'},
        'Abgelehnt': {'titel': 'Abgelehnt', 'datum_feld': 'entscheid_datum', 'datum_label': 'Entscheid'}
    },
    // Ansichten je Rolle: die ERSTE passende Zeile gilt (Rollenname oder '*').
    // Liste [Status, aufgeklappt] in der gewünschten Reihenfolge; nicht aufgeführte Gruppen erscheinen nicht.
    ANSICHTEN: [
        ['MV_Solifonds_GL', [['Vorgeprüft', true], ['Antrag Vorstand', true], ['Gesuch eingereicht', false], ['Vorgemerkt', false],
            ['Unzugewiesen', false], ['Nicht vergeben', false], ['Laufend (Solifonds)', false], ['Abgelehnt', false]]],
        ['MV_Solifonds_Vorpruefung', [['Gesuch eingereicht', true], ['Vorgeprüft', false], ['Antrag Vorstand', false], ['Vorgemerkt', false],
            ['Unzugewiesen', false], ['Nicht vergeben', false], ['Laufend (Solifonds)', false], ['Abgelehnt', false]]],
        ['*', [['Vorgeprüft', true], ['Antrag Vorstand', true], ['Gesuch eingereicht', true], ['Vorgemerkt', false],
            ['Unzugewiesen', false], ['Nicht vergeben', false], ['Laufend (Solifonds)', false], ['Abgelehnt', false]]]
    ],
    get_ansicht: function() {
        let zeile = frappe.vbz_solifonds.ANSICHTEN.find(a => a[0] == '*' || frappe.user.has_role(a[0]));
        let gl = frappe.user.has_role('MV_Solifonds_GL');
        return (zeile ? zeile[1] : []).filter(g => frappe.vbz_solifonds.GRUPPEN[g[0]]).map(g => {
            let gruppe = Object.assign({'status': g[0], 'offen': g[1] ? 1 : 0}, frappe.vbz_solifonds.GRUPPEN[g[0]]);
            if (!gl) {
                delete gruppe.aktion;
            }
            return gruppe;
        });
    },
    laden: function(wrapper) {
        frappe.call({
            'method': frappe.mvd.solifonds.METHOD + 'get_dashboard',
            'freeze': true,
            'freeze_message': 'Lade Solidaritätsfonds...',
            'callback': function(r) {
                let mandate = r.message || [];
                let gruppen = frappe.vbz_solifonds.get_ansicht().map(g => Object.assign({}, g, {
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
