// Copyright (c) 2023, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Arbeitsplan Beratung', {
    refresh: function(frm) {
        if (cur_frm.doc.einteilung.length < 1) {
            frm.add_custom_button(__("Hole Berater*innen"), function() {
                frm.call("get_personen", {}, (r) => {
                    frm.reload_doc();
                });
            });
        } else {
            // holen der bereits verwendeten Termin-Blocks (um zu verhindern dass diese gelöscht/geändert werden)
            frappe.call({
                "method": "mvd.mvd.doctype.arbeitsplan_beratung.arbeitsplan_beratung.verwendete_einteilungen",
                "args": {
                    "arbeitsplan_beratung": cur_frm.doc.name
                },
                "async": true,
                "callback": function(response) {
                    localStorage.setItem('einteilung_verwendet', response.message.einteilung_verwendet);
                    response.message.reset_values.forEach(element => {
                        localStorage.setItem(element.referenz, element.reset_data);
                    });
                }
            });
        }
    }
});

frappe.ui.form.on('APB Zuweisung', {
    before_einteilung_remove: function(frm, cdt, cdn) {
        if (localStorage.getItem('einteilung_verwendet').includes(`-${cdn}`)) {
            frappe.throw("Dieser Terminblock wird verwendet und kann nicht gelöscht werden.");
        }
    },
    art_ort: function(frm, cdt, cdn) {
        if (localStorage.getItem('einteilung_verwendet').includes(`-${cdn}`)) {
            var last_value = localStorage.getItem(cdn).split(",")[0]
            if (last_value != locals[cdt][cdn].art_ort) {
                locals[cdt][cdn].art_ort = last_value;
                cur_frm.refresh_field('einteilung');
                frappe.throw("Dieser Terminblock wird verwendet und kann nicht verändert werden.");
            }
        }
    },
    date: function(frm, cdt, cdn) {
        if (localStorage.getItem('einteilung_verwendet').includes(`-${cdn}`)) {
            var last_value = localStorage.getItem(cdn).split(",")[1]
            if (last_value != locals[cdt][cdn].date) {
                locals[cdt][cdn].date = last_value;
                cur_frm.refresh_field('einteilung');
                frappe.throw("Dieser Terminblock wird verwendet und kann nicht verändert werden.");
            }
        }
    },
    from_time: function(frm, cdt, cdn) {
        if (localStorage.getItem('einteilung_verwendet').includes(`-${cdn}`)) {
            var last_value = localStorage.getItem(cdn).split(",")[2]
            if (last_value != locals[cdt][cdn].from_time) {
                locals[cdt][cdn].from_time = last_value;
                cur_frm.refresh_field('einteilung');
                frappe.throw("Dieser Terminblock wird verwendet und kann nicht verändert werden.");
            }
        }
    },
    to_time: function(frm, cdt, cdn) {
        if (localStorage.getItem('einteilung_verwendet').includes(`-${cdn}`)) {
            var last_value = localStorage.getItem(cdn).split(",")[3]
            if (last_value != locals[cdt][cdn].to_time) {
                locals[cdt][cdn].to_time = last_value;
                cur_frm.refresh_field('einteilung');
                frappe.throw("Dieser Terminblock wird verwendet und kann nicht verändert werden.");
            }
        }
    },
    beratungsperson: function(frm, cdt, cdn) {
        if (localStorage.getItem('einteilung_verwendet').includes(`-${cdn}`)) {
            var last_value = localStorage.getItem(cdn).split(",")[4]
            if (last_value != locals[cdt][cdn].beratungsperson) {
                locals[cdt][cdn].beratungsperson = last_value;
                cur_frm.refresh_field('einteilung');
                frappe.throw("Dieser Terminblock wird verwendet und kann nicht verändert werden.");
            }
        }
    }
});