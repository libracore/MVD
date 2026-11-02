// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

// Dialog "Mandat erstellen" für das Formular Beratung.
// Wird über hooks.py (doctype_js "Beratung") geladen.

frappe.provide('frappe.mvd.mandat');

frappe.mvd.mandat.UEBERNEHMEN = 'Ich übernehme das Mandat';
frappe.mvd.mandat.NICHT_UEBERNEHMEN = 'Ich kann das Mandat nicht übernehmen';

frappe.mvd.mandat.erstellen = function(frm) {
    if (!frm.doc.beratungskategorie) {
        frappe.msgprint({
            title: __('Beratungskategorie fehlt'),
            indicator: 'red',
            message: __('Bitte zuerst in der Beratung die Beratungskategorie setzen und speichern.')
        });
        return;
    }
    // Ins Mandat kopiert wird die gespeicherte Beratung, darum keine ungespeicherten Änderungen zulassen
    if (frm.is_dirty()) {
        frappe.msgprint({
            title: __('Beratung nicht gespeichert'),
            indicator: 'red',
            message: __('Bitte zuerst die Beratung speichern.')
        });
        return;
    }

    // Eigene Vertrauensanwält*in (Termin Kontaktperson) der angemeldeten Person ermitteln
    frappe.call({
        method: "mvd.mvd.doctype.beratung.beratung.uebernahme",
        args: {
            'beratung': frm.doc.name,
            'user': frappe.session.user
        },
        callback: function(r) {
            frappe.mvd.mandat.erstellen_dialog(frm, r.message || null);
        }
    });
};

frappe.mvd.mandat.erstellen_dialog = function(frm, eigene_va) {
    // Vorbelegung: selbst Berater*in der Beratung -> übernehmen; keine eigene VA -> nicht übernehmen
    let uebernahme_default = '';
    if (eigene_va && frm.doc.kontaktperson == eigene_va) {
        uebernahme_default = frappe.mvd.mandat.UEBERNEHMEN;
    } else if (!eigene_va) {
        uebernahme_default = frappe.mvd.mandat.NICHT_UEBERNEHMEN;
    }

    let d = new frappe.ui.Dialog({
        title: 'Mandat erstellen',
        fields: [
            {'fieldname': 'prozess_html', 'fieldtype': 'HTML', 'options': '<div class="alert alert-info">Platzhalter: Hier folgt die Beschreibung des Mandats-Prozesses.</div>'},
            {'fieldname': 'beratungskategorie', 'fieldtype': 'Read Only', 'label': 'Beratungskategorie', 'default': frm.doc.beratungskategorie},
            {'fieldname': 'uebernahme', 'fieldtype': 'Select', 'label': 'Übernahme', 'reqd': 1,
             'options': ['', frappe.mvd.mandat.UEBERNEHMEN, frappe.mvd.mandat.NICHT_UEBERNEHMEN].join('\n'), 'default': uebernahme_default,
             'change': function() {
                if (d.get_value('uebernahme') == frappe.mvd.mandat.UEBERNEHMEN && !eigene_va) {
                    d.set_value('uebernahme', frappe.mvd.mandat.NICHT_UEBERNEHMEN);
                    frappe.msgprint({
                        title: __('Keine Vertrauensanwält*in'),
                        indicator: 'red',
                        message: __('Sie sind keiner Vertrauensanwält*in zugeordnet und können das Mandat darum nicht selbst übernehmen.')
                    });
                }
             }
            },
            {'fieldname': 'seki_hinweis', 'fieldtype': 'HTML', 'options': '<p class="text-muted">Das Sekretariat bemüht sich um eine geeignete VA.</p>', 'depends_on': `eval:doc.uebernahme=="${frappe.mvd.mandat.NICHT_UEBERNEHMEN}"`},
            {'fieldname': 'typ', 'fieldtype': 'Select', 'label': 'Typ', 'reqd': 1, 'options': "Rechtsschutzversicherung\nSolidaritätsfonds", 'default': 'Rechtsschutzversicherung'},
            {'fieldname': 'bemerkung', 'fieldtype': 'Small Text', 'label': 'Bemerkungen', 'description': 'Wird im Mandat gespeichert und ist für alle sichtbar, die das Mandat sehen. Wird nicht an die VA gemailt.'},
            {'fieldname': 'persoenliche_bemerkung', 'fieldtype': 'Small Text', 'label': 'Persönliche Bemerkung', 'depends_on': `eval:doc.uebernahme=="${frappe.mvd.mandat.UEBERNEHMEN}"`, 'description': 'Wird im Mandat gespeichert und in der Bestätigungsmail an die VA mitgeschickt (nur Typ Rechtsschutzversicherung).'}
        ],
        primary_action_label: 'Erstellen',
        primary_action: function(values) {
            let uebernehmen = values.uebernahme == frappe.mvd.mandat.UEBERNEHMEN;

            frappe.call({
                "method": "mvd.mvd.doctype.mandat.mandat.create_mandat",
                "args": {
                    "beratung": frm.doc.name,
                    "berater_in": uebernehmen ? eigene_va : null,
                    "typ": values.typ,
                    "bemerkung": values.bemerkung,
                    "persoenliche_bemerkung": uebernehmen ? values.persoenliche_bemerkung : null
                },
                "callback": function(r) {
                    d.hide();
                    frm.reload_doc();
                    frappe.msgprint(`Das Mandat (${r.message}) wurde erstellt.`);
                }
            });
        }
    });

    d.show();
};
