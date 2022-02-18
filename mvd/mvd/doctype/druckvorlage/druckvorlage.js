// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Druckvorlage', {
    dokument: function(frm) {
        if (cur_frm.doc.dokument == 'Mahnung') {
            cur_frm.set_value('anzahl_seiten', '2');
        }
    },
    anzahl_seiten: function(frm) {
        if (cur_frm.doc.dokument == 'Mahnung') {
            if (cur_frm.doc.anzahl_seiten != '2') {
                cur_frm.set_value('anzahl_seiten', '2');
                frappe.msgprint("Die Anzahl Blätter wurde auf 2 zurückgesetzt weil es sich um eine Mahnungs Druckvorlage handelt.");
            }
        }
    }
});
