// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Termin Kontaktperson', {
    monday: function(frm) {
        if ((!cur_frm.doc.monday_art)||(cur_frm.doc.monday_art=='')) {
            cur_frm.set_value('monday_art', 'Ohne Einschränkung');
        }
    },
    tuesday: function(frm) {
        if ((!cur_frm.doc.tuesday_art)||(cur_frm.doc.tuesday_art=='')) {
            cur_frm.set_value('tuesday_art', 'Ohne Einschränkung');
        }
    },
    wednesday: function(frm) {
        if ((!cur_frm.doc.wednesday_art)||(cur_frm.doc.wednesday_art=='')) {
            cur_frm.set_value('wednesday_art', 'Ohne Einschränkung');
        }
    },
    thursday: function(frm) {
        if ((!cur_frm.doc.thursday_art)||(cur_frm.doc.thursday_art=='')) {
            cur_frm.set_value('thursday_art', 'Ohne Einschränkung');
        }
    },
    friday: function(frm) {
        if ((!cur_frm.doc.friday_art)||(cur_frm.doc.friday_art=='')) {
            cur_frm.set_value('friday_art', 'Ohne Einschränkung');
        }
    },
    saturday: function(frm) {
        if ((!cur_frm.doc.saturday_art)||(cur_frm.doc.saturday_art=='')) {
            cur_frm.set_value('saturday_art', 'Ohne Einschränkung');
        }
    },
    sunday: function(frm) {
        if ((!cur_frm.doc.sunday_art)||(cur_frm.doc.sunday_art=='')) {
            cur_frm.set_value('sunday_art', 'Ohne Einschränkung');
        }
    }
});
