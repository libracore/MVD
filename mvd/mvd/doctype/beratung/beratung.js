// Copyright (c) 2023, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Beratung', {
    refresh: function(frm) {
        if ((!frm.doc.__islocal)&&(cur_frm.doc.mv_mitgliedschaft)) {
            // load html overview
            load_html_overview(frm);
        }
        
        if (!frm.doc.__islocal) {
            // load html verknüpfungen
            load_html_verknuepfungen(frm);
        }
        
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__("Verknüpfen"),  function() {
                verknuepfen(cur_frm.doc.name, '9c572a3e99', false);
            });
        }
    },
    mv_mitgliedschaft: function(frm) {
        if ((!frm.doc.__islocal)&&(cur_frm.doc.mv_mitgliedschaft)) {
            // load html overview
            load_html_overview(frm);
        }
    }
});

function load_html_overview(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.get_uebersicht_html",
        args:{
                'name': cur_frm.doc.mv_mitgliedschaft
        },
        callback: function(r)
        {
            cur_frm.set_df_property('uebersicht_html','options', r.message);
        }
    });
}

function load_html_verknuepfungen(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.beratung.beratung.get_verknuepfungsuebersicht",
        args:{
                'beratung': cur_frm.doc.name
        },
        callback: function(r)
        {
            cur_frm.set_df_property('verknuepfungen_html','options', r.message);
        }
    });
}

function verknuepfen(beratung_parent, beratung, remove) {
    if (!remove) {
        frappe.call({
            'method': "mvd.mvd.doctype.beratung.beratung.verknuepfen",
            'args': {
                'beratung': beratung_parent,
                'verknuepfung': beratung
            },
            'callback': function(r) {
                cur_frm.reload_doc()
            }
        });
    } else {
        frappe.call({
            'method': "mvd.mvd.doctype.beratung.beratung.verknuepfung_entfernen",
            'args': {
                'beratung': beratung_parent,
                'verknuepfung': beratung
            },
            'callback': function(r) {
                cur_frm.reload_doc()
            }
        });
    }
}
