// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('RSVMandat', {
    refresh(frm) {
        cur_frm.fields_dict['thema'].get_query = function(doc) {
             return {
                 filters: {
                     "rsv": 1
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
    if (cur_frm.doc.mv_mitgliedschaft) {
        // Lade Übersicht für Mitglied
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
}
