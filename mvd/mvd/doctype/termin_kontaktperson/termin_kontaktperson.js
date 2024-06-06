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

frappe.ui.form.on('Arbeitsplan Standardzeit', {
    form_render: function(frm, cdt, cdn) {
        var open_row = cur_frm.get_field("arbeitsplan_standardzeit").grid.grid_rows[locals[cdt][cdn].idx - 1].get_open_form();
        $(open_row.wrapper.find(".grid-duplicate-row")).off("click");
        open_row.wrapper.find(".grid-duplicate-row")
        .on('click', function() {
            var idx = open_row.doc.idx;
            var copy_doc = open_row.doc;
            idx ++;

            var d = frappe.model.add_child(open_row.grid.frm.doc, open_row.grid.df.options, open_row.grid.df.fieldname, idx);
            d = open_row.grid.duplicate_row(d, copy_doc);
            d.__unedited = true;
            if (d.from) {
                // set to_time = old from_time + default sektion duration
                d.from = d.to;
                frappe.db.get_value("Sektion", cur_frm.doc.sektion_id, "default_termindauer").then(function(r){
                    var new_to_time = moment(`2000-01-01 ${d.to}`);
                    new_to_time.add(r.message.default_termindauer, 'minutes')
                    d.to = `${new_to_time.get('hour')}:${new_to_time.get('minute')}:${new_to_time.get('second')}`;

                    // show new row
                    open_row.frm.script_manager.trigger(open_row.grid.df.fieldname + "_add", d.doctype, d.name);
                    cur_frm.get_field("arbeitsplan_standardzeit").refresh();
                    open_row.grid.grid_rows[idx - 1].toggle_view(true, null);
                })
            } else {
                // show new row
                open_row.frm.script_manager.trigger(open_row.grid.df.fieldname + "_add", d.doctype, d.name);
                cur_frm.get_field("arbeitsplan_standardzeit").refresh();
                open_row.grid.grid_rows[idx - 1].toggle_view(true, null);
            }
        });
    }
});
