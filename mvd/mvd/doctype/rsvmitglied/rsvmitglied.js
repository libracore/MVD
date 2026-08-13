// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('RSVMitglied', {
    refresh(frm) {
        cur_frm.fields_dict['thema'].get_query = function(doc) {
             return {
                 filters: {
                     "rsv": 1
                 }
             }
        }
        cur_frm.fields_dict['anwalt'].get_query = function(doc) {
             return {
                 filters: {
                     "ist_vertrauensanwaeltin": 1
                 }
             }
        }

        // load html overview
        load_html_overview(frm);
        // Eventlistener für den Schlichtungsbehörden Knopf
        frappe.mvd.schlichtungsbehoerde_listener(frm, 'uebersicht_html');

        if (cur_frm.doc.reason_missing_rsvmandatlist) {
            cur_frm.dashboard.add_comment(cur_frm.doc.reason_missing_rsvmandatlist, 'yellow', true);
        } else {
            cur_frm.dashboard.clear_comment();
        }
    },
    create_zip_file: function(frm) {
        cur_frm.save().then(() => {
            var all_files_checked = true;
            for (var i=0; i<cur_frm.doc.dokumente.length; i++) {
                if (cur_frm.doc.dokumente[i].kontrolliert != 1) {
                    all_files_checked = false;
                }
            }
            if (all_files_checked) {
                _create_zip_file(frm);
            } else {
                frappe.confirm(
                    'Es wurden (noch) nicht alle Dokumente geprüft, wollen Sie das ZIP-File trotzdem erzeugen?',
                    function(){
                        // on yes
                        _create_zip_file(frm);
                    },
                    function(){
                        // on no
                    }
                )
            }
        });
    },
    open_beratung: function(frm) {
        frappe.call({
            method: "open_beratung",
            doc: frm.doc,
            freeze: true,
            freeze_message: 'Suche und öffne zugehörige Beratung...',
            callback: function(r)
            {
                if (r.message) {
                    const url = `/desk#Form/Beratung/${r.message}`;
                    window.open(url, '_blank');
                }
            }
        });
    },
    get_or_create_rsv_mandat_list: function(frm) {
        frappe.call({
            method: "get_or_create_rsv_mandat_list",
            doc: frm.doc,
            args: {
                for_lookup: 1
            },
            freeze: true,
            freeze_message: 'Suche zugehörige Mandatslisten...',
            callback: function(rsv_mandat_list)
            {
                var response = rsv_mandat_list.message;
                if (response.qty > 0) {
                    rsv_mandat_listen_selektion(frm, response.rsvmandatsliste);
                } else {
                    frappe.confirm(
                        'Es wurde keine zugehörige RSV Mandatsliste gefunden.<br>Möchten Sie eine neue Anlegen?',
                        function(){
                            // on yes
                            frappe.call({
                                method: "get_or_create_rsv_mandat_list",
                                doc: frm.doc,
                                args: {
                                    force_new_rsvmandatliste: 1
                                },
                                freeze: true,
                                freeze_message: 'Neuanlage Mandatsliste...',
                                callback: function(rsv_mandat_list)
                                {
                                    var response = rsv_mandat_list.message;
                                    cur_frm.set_value("rsvmandatsliste", response);
                                    cur_frm.save();
                                }
                            });
                        },
                        function(){
                            // on no
                        }
                    )
                }
            }
        });
    }
});

function _create_zip_file(frm) {
    frappe.call({
        method: "create_zip",
        doc: frm.doc,
        freeze: true,
        freeze_message: 'Erstelle ZIP-File...',
        callback: function(r)
        {
            
            cur_frm.reload_doc();
        }
    });
}

function load_html_overview(frm) {
    var method = false;
    if (cur_frm.doc.mv_mitgliedschaft) {
        method = "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_uebersicht_html";
    } else {
        if (cur_frm.doc.faktura_kunde) {
            method = "mvd.mvd.doctype.kunden.kunden.get_uebersicht_html";
        }
    }

    if (method) {
        // Lade Übersicht für Mitglied/Faktura Kunde
        frappe.call({
            method: method,
            args:{
                    'name': cur_frm.doc.mv_mitgliedschaft ? cur_frm.doc.mv_mitgliedschaft:cur_frm.doc.faktura_kunde
            },
            callback: function(r)
            {
                cur_frm.set_df_property('uebersicht_html','options', r.message);
            }
        });
    }

    if (cur_frm.doc.adr_egaid) {
        // Lade Übersicht für die Siedlungsadresse
        frappe.call({
            method: "mvd.mvd.doctype.rsvmitglied.rsvmitglied.get_siedlungs_adressen_html",
            args:{
                    'adr_egaid': cur_frm.doc.adr_egaid
            },
            callback: function(r)
            {
                cur_frm.set_df_property('siedlungs_adressen_html','options', r.message);
            }
        });
    }
}

function rsv_mandat_listen_selektion(frm, rsv_mandatliste) {
    const input = rsv_mandatliste;
    const filter_names = Array.isArray(input) ? input.map(({ name }) => name) : [input];

    var d = new frappe.ui.Dialog({
        'fields': [
            {'fieldname': 'rsv_mandatliste', 'fieldtype': 'Link', 'options': 'RSVMandatsliste', 'label': 'Gefundene RSV-Mandatslisten', 'reqd': 1,
                'get_query': function() { return { filters: {'name': ['in', filter_names]}}},
                'description': "Sie können entweder im obigen Feld eine gefundene RSV-Mandatsliste auswählen und verknüpfen, oder nachfolgend eine Neuanlage erzwingen."
            },
            {'fieldname': 'neuanlage', 'fieldtype': 'Button', 'label': 'RSV-Mandatsliste Neuanlage',
                'click': function() {
                    d.hide();
                    frappe.call({
                        method: "get_or_create_rsv_mandat_list",
                        doc: frm.doc,
                        args: {
                            force_new_rsvmandatliste: 1
                        },
                        freeze: true,
                        freeze_message: 'Neuanlage Mandatsliste...',
                        callback: function(rsv_mandat_list)
                        {
                            var response = rsv_mandat_list.message;
                            cur_frm.set_value("rsvmandatsliste", response);
                            cur_frm.save();
                        }
                    });
                }
            }
        ],
        primary_action: function(){
            d.hide();
            cur_frm.set_value("rsvmandatsliste", d.get_value("rsv_mandatliste"));
            cur_frm.save();
        },
        primary_action_label: __('Verknüpfen'),
        title: __('Suchresultate')
    });
    d.show();
}