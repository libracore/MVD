// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('RSVMandat', {
    refresh: function(frm) {
        // Ausblenden des Dashboards
        frm.dashboard.hide();

        // check for TimestampMismatchError and reload
        if (!frm.doc.__islocal) {
            frappe.db.get_value(cur_frm.doctype, cur_frm.docname, 'modified').then(r => {
                if (r.message.modified != cur_frm.doc.modified) {
                    cur_frm.reload_doc();
                }
            });
        };

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

        // Lade Übersicht für die RSV-Mitglieder
        frappe.call({
            method: "mvd.mvd.doctype.rsvmandat.rsvmandat.get_rsvmitglieder_html",
            args:{
                    'rsv_mandat': cur_frm.doc.name
            },
            callback: function(r)
            {
                cur_frm.set_df_property('rsv_mitglieder_html','options', r.message);
            }
        });

        // Lade Übersicht für die Siedlungsadressen
        frappe.call({
            method: "mvd.mvd.doctype.siedlungsfall.siedlungsfall.get_siedlungsadressen_html",
            args:{
                    'siedlung': cur_frm.doc.siedlung
            },
            callback: function(r)
            {
                cur_frm.set_df_property('siedlung_html','options', r.message);
            }
        });
    }
});
