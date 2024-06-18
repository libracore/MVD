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
        
        // #1012
        configure_einteilung_order(frm);
    }
});

// #1012
function configure_einteilung_order(frm) {
    var table = $("[data-fieldname='einteilung']")[0];
    var heading_row = $(table).find(".grid-heading-row")[0];

    // Ort / Art
    var art_ort = $(heading_row).find("[data-fieldname='art_ort']")[0];
    var art_ort_static = $(art_ort).find(".static-area")[0];
    $(art_ort_static).css("cursor", "ns-resize");
    $(art_ort).off('click');
    $(art_ort).click(function(){
        if ($(art_ort_static).html() == 'Ort / Art') {
            $(art_ort_static).html('Ort / Art <i class="fa fa-arrow-up"></i>');
            order_einteilung(frm, 'art_ort', 'up');
        } else if ($(art_ort_static).html() == 'Ort / Art <i class="fa fa-arrow-up"></i>') {
            $(art_ort_static).html('Ort / Art <i class="fa fa-arrow-down"></i>');
            order_einteilung(frm, 'art_ort', 'down');
        } else if ($(art_ort_static).html() == 'Ort / Art <i class="fa fa-arrow-down"></i>') {
            $(art_ort_static).html('Ort / Art <i class="fa fa-arrow-up"></i>');
            order_einteilung(frm, 'art_ort', 'up');
        }
        reset_others('art_ort', heading_row);
    });

    // Datum
    var date = $(heading_row).find("[data-fieldname='date']")[0];
    var date_static = $(date).find(".static-area")[0];
    $(date_static).css("cursor", "ns-resize");
    $(date).off('click');
    $(date).click(function(){
        if ($(date_static).html() == 'Datum') {
            $(date_static).html('Datum <i class="fa fa-arrow-up"></i>');
            order_einteilung(frm, 'date', 'up');
        } else if ($(date_static).html() == 'Datum <i class="fa fa-arrow-up"></i>') {
            $(date_static).html('Datum <i class="fa fa-arrow-down"></i>');
            order_einteilung(frm, 'date', 'down');
        } else if ($(date_static).html() == 'Datum <i class="fa fa-arrow-down"></i>') {
            $(date_static).html('Datum <i class="fa fa-arrow-up"></i>');
            order_einteilung(frm, 'date', 'up');
        }
        reset_others('date', heading_row);
    });

    // Von
    var from_time = $(heading_row).find("[data-fieldname='from_time']")[0];
    var from_time_static = $(from_time).find(".static-area")[0];
    $(from_time_static).css("cursor", "ns-resize");
    $(from_time).off('click');
    $(from_time).click(function(){
        if ($(from_time_static).html() == 'Von') {
            $(from_time_static).html('Von <i class="fa fa-arrow-up"></i>');
            order_einteilung(frm, 'from_time', 'up');
        } else if ($(from_time_static).html() == 'Von <i class="fa fa-arrow-up"></i>') {
            $(from_time_static).html('Von <i class="fa fa-arrow-down"></i>');
            order_einteilung(frm, 'from_time', 'down');
        } else if ($(from_time_static).html() == 'Von <i class="fa fa-arrow-down"></i>') {
            $(from_time_static).html('Von <i class="fa fa-arrow-up"></i>');
            order_einteilung(frm, 'from_time', 'up');
        }
        reset_others('from_time', heading_row);
    });

    // Bis
    var to_time = $(heading_row).find("[data-fieldname='to_time']")[0];
    var to_time_static = $(to_time).find(".static-area")[0];
    $(to_time_static).css("cursor", "ns-resize");
    $(to_time).off('click');
    $(to_time).click(function(){
        if ($(to_time_static).html() == 'Bis') {
            $(to_time_static).html('Bis <i class="fa fa-arrow-up"></i>');
            order_einteilung(frm, 'to_time', 'up');
        } else if ($(to_time_static).html() == 'Bis <i class="fa fa-arrow-up"></i>') {
            $(to_time_static).html('Bis <i class="fa fa-arrow-down"></i>');
            order_einteilung(frm, 'to_time', 'down');
        } else if ($(to_time_static).html() == 'Bis <i class="fa fa-arrow-down"></i>') {
            $(to_time_static).html('Bis <i class="fa fa-arrow-up"></i>');
            order_einteilung(frm, 'to_time', 'up');
        }
        reset_others('to_time', heading_row);
    });

    // Berater*in
    var beratungsperson = $(heading_row).find("[data-fieldname='beratungsperson']")[0];
    var beratungsperson_static = $(beratungsperson).find(".static-area")[0];
    $(beratungsperson_static).css("cursor", "ns-resize");
    $(beratungsperson).off('click');
    $(beratungsperson).click(function(){
        if ($(beratungsperson_static).html() == 'Berater*in') {
            $(beratungsperson_static).html('Berater*in <i class="fa fa-arrow-up"></i>');
            order_einteilung(frm, 'beratungsperson', 'up');
        } else if ($(beratungsperson_static).html() == 'Berater*in <i class="fa fa-arrow-up"></i>') {
            $(beratungsperson_static).html('Berater*in <i class="fa fa-arrow-down"></i>');
            order_einteilung(frm, 'beratungsperson', 'down');
        } else if ($(beratungsperson_static).html() == 'Berater*in <i class="fa fa-arrow-down"></i>') {
            $(beratungsperson_static).html('Berater*in <i class="fa fa-arrow-up"></i>');
            order_einteilung(frm, 'beratungsperson', 'up');
        }
        reset_others('beratungsperson', heading_row);
    });
}

// #1012
function reset_others(exclude, heading_row) {
    if (exclude == 'art_ort') {
        var to_change = [['date', 'Datum'], ['from_time', 'Von'], ['to_time', 'Bis'], ['beratungsperson', 'Berater*in']];
        to_change.forEach(element => {
            var change = $(heading_row).find(`[data-fieldname='${element[0]}']`)[0];
            var change_static = $(change).find(".static-area")[0];
            $(change_static).html(`${element[1]}`);
        });
    }
    if (exclude == 'date') {
        var to_change = [['art_ort', 'Ort / Art'], ['from_time', 'Von'], ['to_time', 'Bis'], ['beratungsperson', 'Berater*in']];
        to_change.forEach(element => {
            var change = $(heading_row).find(`[data-fieldname='${element[0]}']`)[0];
            var change_static = $(change).find(".static-area")[0];
            $(change_static).html(`${element[1]}`);
        });
    }
    if (exclude == 'from_time') {
        var to_change = [['art_ort', 'Ort / Art'], ['date', 'Datum'], ['to_time', 'Bis'], ['beratungsperson', 'Berater*in']];
        to_change.forEach(element => {
            var change = $(heading_row).find(`[data-fieldname='${element[0]}']`)[0];
            var change_static = $(change).find(".static-area")[0];
            $(change_static).html(`${element[1]}`);
        });
    }
    if (exclude == 'to_time') {
        var to_change = [['art_ort', 'Ort / Art'], ['date', 'Datum'], ['from_time', 'Von'], ['beratungsperson', 'Berater*in']];
        to_change.forEach(element => {
            var change = $(heading_row).find(`[data-fieldname='${element[0]}']`)[0];
            var change_static = $(change).find(".static-area")[0];
            $(change_static).html(`${element[1]}`);
        });
    }
    if (exclude == 'beratungsperson') {
        var to_change = [['art_ort', 'Ort / Art'], ['date', 'Datum'], ['from_time', 'Von'], ['to_time', 'Bis']];
        to_change.forEach(element => {
            var change = $(heading_row).find(`[data-fieldname='${element[0]}']`)[0];
            var change_static = $(change).find(".static-area")[0];
            $(change_static).html(`${element[1]}`);
        });
    }
}

function order_einteilung(frm, column, order) {
    frm.call("order_einteilung", {'column': column, 'order': order}, (r) => {
        frm.reload_doc();
    });
}

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