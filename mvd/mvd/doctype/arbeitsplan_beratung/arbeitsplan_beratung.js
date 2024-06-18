// Copyright (c) 2023, libracore and contributors
// For license information, please see license.txt

var get_beratungs_link = function(cd_name) {
    return new Promise(function (resolve) {
        resolve(
            frappe.db.get_value("Beratung Termin", {'abp_referenz': cd_name}, 'parent', null, 'Beratung').then(function(r){
                return r.message.parent;
            })
        );
    });
}

frappe.ui.form.on('Arbeitsplan Beratung', {
    refresh: function(frm) {
        frm.add_custom_button(__("Hole Berater*innen"), function() {
            if (cur_frm.is_dirty()) {
                frappe.throw("Bitte speichern Sie den Arbeitsplan zuerst.")
            } else {
                frappe.prompt([
                    {'fieldname': 'einzel', 'fieldtype': 'Check', 'label': 'Import von einzelnen Berater*innen', 'default': 0},
                    {'fieldname': 'person', 'fieldtype': 'Link', 'label': 'Berater*in für Import', 'options': 'Termin Kontaktperson', 'depends_on': 'eval:doc.einzel==1'}
                ],
                function(values){
                    console.log(cint(values.einzel))
                    if ((cur_frm.doc.einteilung.length > 0)&&(cint(values.einzel) != 1)) {
                        frappe.throw("Es wurden bereits Berater*innen hinzugefügt, Sie können nur noch einzelne Berater*innen hinzufügen.")
                    } else {
                        frm.call("get_personen", {'einzel': values.einzel, 'person': values.person || false}, (r) => {
                            frm.reload_doc();
                        });
                    }
                },
                'Age verification',
                'Subscribe me'
                )
            }
        });
        
        if (cur_frm.doc.einteilung.length > 0) {
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
            get_beratungs_link(cdn).then(function (beratung) {
                cur_frm.reload_doc();
                frappe.throw(`Dieser Terminblock wird <a href="/desk#Form/Beratung/${beratung}">in dieser Beratung</a> verwendet und kann nicht gelöscht werden.`);
            });
        }
    },
    art_ort: function(frm, cdt, cdn) {
        if (localStorage.getItem('einteilung_verwendet').includes(`-${cdn}`)) {
            var last_value = localStorage.getItem(cdn).split(",")[0]
            if (last_value != locals[cdt][cdn].art_ort) {
                locals[cdt][cdn].art_ort = last_value;
                cur_frm.refresh_field('einteilung');
                get_beratungs_link(cdn).then(function (beratung) {
                    frappe.throw(`Dieser Terminblock wird <a href="/desk#Form/Beratung/${beratung}">in dieser Beratung</a> verwendet und kann nicht gelöscht werden.`);
                });
            }
        }
    },
    date: function(frm, cdt, cdn) {
        if (localStorage.getItem('einteilung_verwendet').includes(`-${cdn}`)) {
            var last_value = localStorage.getItem(cdn).split(",")[1]
            if (last_value != locals[cdt][cdn].date) {
                locals[cdt][cdn].date = last_value;
                cur_frm.refresh_field('einteilung');
                get_beratungs_link(cdn).then(function (beratung) {
                    frappe.throw(`Dieser Terminblock wird <a href="/desk#Form/Beratung/${beratung}">in dieser Beratung</a> verwendet und kann nicht gelöscht werden.`);
                });
            }
        }
    },
    from_time: function(frm, cdt, cdn) {
        if (localStorage.getItem('einteilung_verwendet').includes(`-${cdn}`)) {
            var last_value = localStorage.getItem(cdn).split(",")[2]
            if (last_value != locals[cdt][cdn].from_time) {
                locals[cdt][cdn].from_time = last_value;
                cur_frm.refresh_field('einteilung');
                get_beratungs_link(cdn).then(function (beratung) {
                    frappe.throw(`Dieser Terminblock wird <a href="/desk#Form/Beratung/${beratung}">in dieser Beratung</a> verwendet und kann nicht gelöscht werden.`);
                });
            }
        }
    },
    to_time: function(frm, cdt, cdn) {
        if (localStorage.getItem('einteilung_verwendet').includes(`-${cdn}`)) {
            var last_value = localStorage.getItem(cdn).split(",")[3]
            if (last_value != locals[cdt][cdn].to_time) {
                locals[cdt][cdn].to_time = last_value;
                cur_frm.refresh_field('einteilung');
                get_beratungs_link(cdn).then(function (beratung) {
                    frappe.throw(`Dieser Terminblock wird <a href="/desk#Form/Beratung/${beratung}">in dieser Beratung</a> verwendet und kann nicht gelöscht werden.`);
                });
            }
        }
    },
    beratungsperson: function(frm, cdt, cdn) {
        if (localStorage.getItem('einteilung_verwendet').includes(`-${cdn}`)) {
            var last_value = localStorage.getItem(cdn).split(",")[4]
            if (last_value != locals[cdt][cdn].beratungsperson) {
                locals[cdt][cdn].beratungsperson = last_value;
                cur_frm.refresh_field('einteilung');
                get_beratungs_link(cdn).then(function (beratung) {
                    frappe.throw(`Dieser Terminblock wird <a href="/desk#Form/Beratung/${beratung}">in dieser Beratung</a> verwendet und kann nicht gelöscht werden.`);
                });
            }
        }
    },
    form_render: function(frm, cdt, cdn) {
        var open_row = cur_frm.get_field("einteilung").grid.grid_rows[locals[cdt][cdn].idx - 1].get_open_form();
        $(open_row.wrapper.find(".grid-duplicate-row")).off("click");
        open_row.wrapper.find(".grid-duplicate-row")
        .on('click', function() {
            var idx = open_row.doc.idx;
            var copy_doc = open_row.doc;
            idx ++;

            var d = frappe.model.add_child(open_row.grid.frm.doc, open_row.grid.df.options, open_row.grid.df.fieldname, idx);
            d = open_row.grid.duplicate_row(d, copy_doc);
            d.__unedited = true;
            if (d.to_time) {
                // set to_time = old from_time + default sektion duration
                d.from_time = d.to_time;
                frappe.db.get_value("Sektion", cur_frm.doc.sektion_id, "default_termindauer").then(function(r){
                    var new_to_time = moment(`2000-01-01 ${d.to_time}`);
                    new_to_time.add(r.message.default_termindauer, 'minutes')
                    d.to_time = `${new_to_time.get('hour')}:${new_to_time.get('minute')}:${new_to_time.get('second')}`;

                    // show new row
                    open_row.frm.script_manager.trigger(open_row.grid.df.fieldname + "_add", d.doctype, d.name);
                    cur_frm.get_field("einteilung").refresh();
                    open_row.grid.grid_rows[idx - 1].toggle_view(true, null);
                })
            } else {
                // show new row
                open_row.frm.script_manager.trigger(open_row.grid.df.fieldname + "_add", d.doctype, d.name);
                cur_frm.get_field("einteilung").refresh();
                open_row.grid.grid_rows[idx - 1].toggle_view(true, null);
            }
        });

        // set link zur Beratung
        var child = locals[cdt][cdn];
        var field_wrapper = frm.fields_dict[child.parentfield].grid.grid_rows_by_docname[cdn].grid_form.fields_dict['link_zur_beratung'].wrapper
        $(field_wrapper).empty();
        frappe.db.get_value("Beratung Termin", {'abp_referenz': cdn}, 'parent', null, 'Beratung').then(function(r){
            $(`<br><a href="/desk#Form/Beratung/${r.message.parent}">Link zur Beratung</a>`).appendTo(field_wrapper);
        });
    }
});