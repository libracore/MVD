// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('RSVMitglied', {
    refresh(frm) {
        // check for TimestampMismatchError and reload
        if (!frm.doc.__islocal) {
            frappe.db.get_value(cur_frm.doctype, cur_frm.docname, 'modified').then(r => {
                if (r.message.modified != cur_frm.doc.modified) {
                    cur_frm.reload_doc();
                }
            });
        };

        // load html overview (Mitglied, Siedlungsadresse & RSV-Mandat)
        load_html_overview(frm);
        // Eventlistener für den Schlichtungsbehörden Knopf
        frappe.mvd.schlichtungsbehoerde_listener(frm, 'uebersicht_html');
        // "Öffne"-Buttons zu den VA-Extranet-Seiten
        // Hinweis: bewusst dupliziert (statt frappe.mvd.add_va_open_buttons zu nutzen) in rsvmandat.js
        // und rsvmitglied.js: Änderungen an DocType-Controller-JS werden clientseitig im localStorage
        // gecacht (Schlüssel "_doctype:<DocType>", versioniert über modified-Zeitstempel des DocType-
        // Datensatzes) und über einen Aufruf in mvd.js liess sich das zuverlässig nicht auflösen.
        frm.add_custom_button(__("Vergabeliste"),  function() {
            var domain = window.location.origin;
            window.open(`${domain}/va/vergabeliste`, '_blank');
        }, "Öffne");
        frm.add_custom_button(__("Meine-Mandate"),  function() {
            var domain = window.location.origin;
            window.open(`${domain}/va/meine-mandate`, '_blank');
        }, "Öffne");
        frm.add_custom_button(__("Coop-Liste"),  function() {
            var domain = window.location.origin;
            window.open(`${domain}/va/coop-mandate`, '_blank');
        }, "Öffne");

        if (frm.doc.rsvmandat) {
            frappe.db.get_value(
                'RSVMandat',
                frm.doc.rsvmandat,
                'anwalt',
                function(r) {
                    if (
                        !frm.doc.sendung_an_coop &&
                        r.anwalt &&
                        r.anwalt != ''
                    ) {
                        frm.add_custom_button(__("E-Mail an Coop senden"),  function() {
                            frm.trigger('email_an_coop_senden');
                        }).addClass('btn-primary');
                    }
                }
            );
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
    open_rsv_mandat: function(frm) {
        const url = `/desk#Form/RSVMandat/${cur_frm.doc.rsvmandat}`;
        window.open(url, '_self');
    },
    get_or_create_rsv_mandat: function(frm) {
        frappe.call({
            method: "get_or_create_rsv_mandat",
            doc: frm.doc,
            args: {
                for_lookup: 1
            },
            freeze: true,
            freeze_message: 'Suche zugehörige RSV-Mandate...',
            callback: function(rsv_mandat)
            {
                var response = rsv_mandat.message;
                if (response.qty > 0) {
                    rsv_mandat_selektion(frm, response.rsvmandat);
                } else {
                    frappe.confirm(
                        'Es wurde keine zugehörige RSV Mandat gefunden.<br>Möchten Sie ein neues Anlegen?',
                        function(){
                            // on yes
                            frappe.call({
                                method: "get_or_create_rsv_mandat",
                                doc: frm.doc,
                                args: {
                                    force_new_rsvmandat: 1
                                },
                                freeze: true,
                                freeze_message: 'Neuanlage RSV-Mandat...',
                                callback: function(rsv_mandat)
                                {
                                    var response = rsv_mandat.message;
                                    cur_frm.set_value("rsvmandat", response);
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
    },
    email_an_coop_senden: function(frm) {
        if (frm.is_new()) {
            frappe.msgprint(__('Bitte speichern Sie das Dokument zuerst, bevor Sie die E-Mail versenden.'));
            return;
        }
        frappe.call({
            method: 'mvd.mvd.doctype.rsvmitglied.rsvmitglied.get_coop_email_data',
            args: {
                "docname": frm.doc.name
            },
            freeze: true,
            freeze_message: __('E-Mail-Daten werden geladen (ZIP wird erstellt)...'),
            callback: function(r) {
                if (!r.exc && r.message) {
                    var mail_data = r.message;
                    new frappe.mvd.MailComposer({
                        doc: frm.doc,
                        frm: frm,
                        subject: mail_data.subject,
                        recipients: mail_data.recipients, 
                        cc: mail_data.cc,
                        attach_document_print: false,
                        txt: mail_data.content,
                        email_template: '', 
                        last_email: '',
                        is_a_reply: false,
                        sender: mail_data.sender
                    });
                    frm.reload_doc();
                }
            }
        });
    },
    open_mitglied: function(frm) {
        const url = `/desk#Form/Mitgliedschaft/${frm.doc.mv_mitgliedschaft}`;
        window.open(url, '_blank');
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
    } else {
        cur_frm.set_df_property('uebersicht_html','options', '<div>&nbsp;</div>');
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
    } else {
        cur_frm.set_df_property('siedlungs_adressen_html','options', '<div>&nbsp;</div>');
    }
    
    if (cur_frm.doc.rsvmandat) {
        // Lade Übersicht für das RSV-Mandat
        frappe.call({
            method: "mvd.mvd.doctype.rsvmitglied.rsvmitglied.get_rsv_mandat_html",
            args:{
                    'rsv_mandat': cur_frm.doc.rsvmandat
            },
            callback: function(r)
            {
                cur_frm.set_df_property('rsvmandat_html','options', r.message);
            }
        });
    } else {
        cur_frm.set_df_property('rsvmandat_html','options', '<div>&nbsp;</div>');
    }
}

function rsv_mandat_selektion(frm, rsv_mandat) {
    const input = rsv_mandat;
    const filter_names = Array.isArray(input) ? input.map(({ name }) => name) : [input];

    var d = new frappe.ui.Dialog({
        'fields': [
            {'fieldname': 'rsv_mandat', 'fieldtype': 'Link', 'options': 'RSVMandat', 'label': 'Gefundene RSV-Mandate', 'reqd': 1,
                'get_query': function() { return { filters: {'name': ['in', filter_names]}}},
                'description': "Sie können entweder im obigen Feld ein gefundenes RSV-Mandat auswählen und verknüpfen, oder nachfolgend eine Neuanlage erzwingen."
            },
            {'fieldname': 'neuanlage', 'fieldtype': 'Button', 'label': 'RSV-Mandat Neuanlage',
                'click': function() {
                    d.hide();
                    frappe.call({
                        method: "get_or_create_rsv_mandat",
                        doc: frm.doc,
                        args: {
                            force_new_rsvmandat: 1
                        },
                        freeze: true,
                        freeze_message: 'Neuanlage RSV-Mandat...',
                        callback: function(rsv_mandat)
                        {
                            var response = rsv_mandat.message;
                            cur_frm.set_value("rsvmandat", response);
                            cur_frm.save();
                        }
                    });
                }
            }
        ],
        primary_action: function(){
            d.hide();
            cur_frm.set_value("rsvmandat", d.get_value("rsv_mandat"));
            cur_frm.save();
        },
        primary_action_label: __('Verknüpfen'),
        title: __('Suchresultate')
    });
    d.show();
}

frappe.ui.form.on('RSV Mandat Dokumente', {
    inhalt_gepr: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        if (row.inhalt_gepr) {
            frappe.model.set_value(cdt, cdn, 'formal_gepr', 1);
        }
    }
});