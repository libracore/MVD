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
                frappe.prompt([
                    {'fieldname': 'beratung', 'fieldtype': 'Link', 'options': 'Beratung', 'label': 'Beratung', 'reqd': 1}  
                ],
                function(values){
                    verknuepfen(cur_frm.doc.name, values.beratung, false);
                },
                'Beratungs Verknüpfung',
                'Verknüpfen'
                );
            });
        }
        
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__("Übernehmen"),  function() {
                //~ frappe.call({
                    //~ method: "mvd.mvd.doctype.beratung.beratung.uebernahme",
                    //~ args:{
                            //~ 'beratung': cur_frm.doc.name,
                            //~ 'user': frappe.session.user
                    //~ },
                    //~ callback: function(r)
                    //~ {
                        //~ cur_frm.reload_doc();
                        //~ frappe.msgprint("Beratung übernommen");
                    //~ }
                //~ });
                frappe.msgprint("TBD");
            });
        }
        
        if (cur_frm.doc.kontaktperson&&cur_frm.doc.create_todo) {
            frappe.call({
                method: "mvd.mvd.doctype.beratung.beratung.new_todo",
                args:{
                        'beratung': cur_frm.doc.name,
                        'kontaktperson': cur_frm.doc.kontaktperson
                },
                callback: function(r)
                {
                    cur_frm.reload_doc();
                    frappe.msgprint("ToDo erstellt");
                }
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
            add_jump_icons_event_handler(frm);
            add_trash_icons_event_handler(frm);
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

function add_trash_icons_event_handler(frm) {
    // event handler für trash icons (verknüpfungen)
    $(".verknuepfung_trash").each(function() {
        $(this).bind( "click", function() {
            $(this).parent().parent().css({"background-color": "red"});
            verknuepfen(cur_frm.doc.name, $(this).attr("data-remove"), true);
        });
    });
}

function add_jump_icons_event_handler(frm) {
    // event handler für kump icons (verknüpfungen)
    $(".verknuepfung_jump").each(function() {
        $(this).bind( "click", function() {
            frappe.set_route("Form", "Beratung", $(this).attr("data-jump"));
        });
    });
}
