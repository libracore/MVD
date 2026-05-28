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

        if (frm._refresh_msg_running) return;
        frm._refresh_msg_running = true;

        if (
            frm.doc.manuelle_rsvmandatliste_auswahl &&
            !frm.doc.__islocal
        ) {
            frappe.msgprint("Die zugehörige RSV-Mandatliste muss selbst gewählt werden.");
        }

        // msgprint nach aktuellem refresh wieder freigeben
        setTimeout(() => {
            frm._refresh_msg_running = false;
        }, 0);
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
