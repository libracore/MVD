// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

// Gemeinsame Dialoge Solidaritätsfonds (#2183) für das Formular Mandat und die Page vbz-solifonds.
// Eingebunden per include-Anweisung am Anfang von mandat.js und vbz_solifonds.js.

frappe.provide('frappe.mvd.solifonds');

frappe.mvd.solifonds.METHOD = 'mvd.mvd.doctype.mandat.solifonds.';
frappe.mvd.solifonds.OHNE_PERSONENDATEN = 'Ohne Personendaten – wird dem Vorstand anonymisiert angezeigt.';


frappe.mvd.solifonds.entscheid_dialog = function(mandat, callback) {
    let d = new frappe.ui.Dialog({
        title: __('Entscheid Geschäftsleitung'),
        fields: [
            {'fieldname': 'entscheid', 'fieldtype': 'Select', 'label': __('Entscheid'), 'reqd': 1,
             'options': ['', 'Kostengutsprache', 'Antrag Vorstand', 'Abgelehnt'],
             'description': __('Kostengutsprache: Status «Laufend (Solifonds)», Mail mit PDF an die VA · Antrag Vorstand: Abstimmungslinks an den Vorstand · Abgelehnt: Info an die Vorprüfung')},
            {'fieldname': 'bemerkung', 'fieldtype': 'Small Text', 'label': __('Bemerkung zum Entscheid'), 'description': frappe.mvd.solifonds.OHNE_PERSONENDATEN}
        ],
        primary_action_label: __('Entscheiden'),
        primary_action: function(values) {
            d.hide();
            frappe.call({
                method: frappe.mvd.solifonds.METHOD + 'gl_entscheid',
                args: {'mandat': mandat, 'entscheid': values.entscheid, 'bemerkung': values.bemerkung},
                freeze: true,
                callback: function() { if (callback) callback(); }
            });
        }
    });
    d.show();
};

frappe.mvd.solifonds.abstimmung_abschliessen = function(mandat, callback, patt_entscheid) {
    frappe.call({
        method: frappe.mvd.solifonds.METHOD + 'abstimmung_abschliessen',
        args: {'mandat': mandat, 'patt_entscheid': patt_entscheid || null},
        freeze: true,
        callback: function(r) {
            if (r.message && r.message.patt) {
                let s = r.message.stand;
                frappe.prompt([{'fieldname': 'entscheid', 'fieldtype': 'Select', 'label': __('Entscheid GL'), 'reqd': 1,
                        'options': ['', 'Kostengutsprache', 'Abgelehnt']}],
                    function(values) {
                        frappe.mvd.solifonds.abstimmung_abschliessen(mandat, callback, values.entscheid);
                    },
                    __('Patt: Ja {0}, Nein {1}, Enthaltung {2}, offen {3}', [s.ja, s.nein, s.enthaltung, s.offen]),
                    __('Entscheiden'));
                return;
            }
            if (callback) callback();
        }
    });
};
