// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('MV Mitgliedschaft', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__("Sektionswechsel"),  function() {
                    sektionswechsel(frm);
            }, __("Mutation"));
            frm.add_custom_button(__("Kündigung"),  function() {
                    kuendigung(frm);
            }, __("Mutation"));
            frm.add_custom_button(__("Ausschluss"),  function() {
                    ausschluss(frm);
            }, __("Mutation"));
            frm.add_custom_button(__("Todesfall"),  function() {
                    todesfall(frm);
            }, __("Mutation"));
            frm.add_custom_button(__("Mitgliedschafts-Rechnung"),  function() {
                    erstelle_rechnung(frm);
            }, __("Erstelle"));
            
            get_adressdaten(frm);
        }
        
        remove_sinv_plus(frm);
        
        if (cur_frm.doc.status_c == 'Wegzug') {
            setze_read_only(frm);
        }
    }
});

function get_adressdaten(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft.get_uebersicht_html",
        args:{
                'name': cur_frm.doc.name
        },
        callback: function(r)
        {
            cur_frm.set_df_property('uebersicht_html','options', r.message);
        }
    });
}

function kuendigung(frm) {
    frappe.prompt([
        {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Kündigung erfolgt per', 'reqd': 1, 'default': frappe.datetime.year_end()},
        {'fieldname': 'massenlauf', 'fieldtype': 'Check', 'label': 'Für Massenlauf vormerken', 'default': 1}
    ],
    function(values){
        frappe.call({
            method: "mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft.make_kuendigungs_prozess",
            args:{
                    'mitgliedschaft': cur_frm.doc.name,
                    'datum_kuendigung': values.datum,
                    'massenlauf': values.massenlauf
            },
            freeze: true,
            freeze_message: 'Erstelle Kündigung inkl. Bestätigung...',
            callback: function(r)
            {
                cur_frm.reload_doc();
                frappe.msgprint("Die Kündigung wurde per " + frappe.datetime.obj_to_user(values.datum) + " erfasst.<br>Die Kündigungsbestätigung finden Sie in den Anhängen.");
            }
        });
        
    },
    'Kündigung',
    'Erfassen'
    )
}

function todesfall(frm) {
    frappe.prompt([
        {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Todesfall bedingte Kündigung erfolgt per', 'reqd': 1, 'default': frappe.datetime.year_end()},
        {'fieldname': 'todesfall_uebernahme', 'fieldtype': 'Data', 'label': 'Übernahem durch'}
    ],
    function(values){
        cur_frm.set_value("kuendigung", values.datum);
        cur_frm.set_value("status_c", 'Gestorben');
        if (values.todesfall_uebernahme) {
            cur_frm.set_value("todesfall_uebernahme", values.todesfall_uebernahme);
        }
        cur_frm.save();
        frappe.msgprint("Der Todesfall sowie die damit verbundene Kündigung wurde per " + frappe.datetime.obj_to_user(values.datum) + " erfasst.");
    },
    'Todesfall',
    'Erfassen'
    )
}

function ausschluss(frm) {
    frappe.prompt([
        {'fieldname': 'datum', 'fieldtype': 'Date', 'label': 'Ausschluss per', 'reqd': 1, 'default': frappe.datetime.get_today()},
        {'fieldname': 'grund', 'fieldtype': 'Text', 'label': 'Ausschluss Begründung'}
    ],
    function(values){
        cur_frm.set_value("austritt", values.datum);
        cur_frm.set_value("status_c", 'Ausschluss');
        if (values.grund) {
            var alte_infos = cur_frm.doc.wichtig;
            var neue_infos = "Ausschluss:\n" + values.grund + "\n\n";
            neue_infos = neue_infos + alte_infos;
            cur_frm.set_value("wichtig", neue_infos);
        }
        cur_frm.save();
        frappe.msgprint("Der Ausschluss wurde per " + frappe.datetime.obj_to_user(values.datum) + " erfasst.");
    },
    'Ausschluss',
    'Erfassen'
    )
}

function sektionswechsel(frm) {
    frappe.prompt([
        {'fieldname': 'sektion_neu', 'fieldtype': 'Link', 'label': 'Neue Sektion', 'reqd': 1, 'options': 'Sektion'}  
    ],
    function(values){
        frappe.call({
            method: "mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft.sektionswechsel",
            args:{
                    'mitgliedschaft': cur_frm.doc.name,
                    'neue_sektion': values.sektion_neu,
                    'zuzug_per': frappe.datetime.get_today()
            },
            callback: function(r)
            {
                if (r.message == 1) {
                    cur_frm.set_value("wegzug", frappe.datetime.get_today());
                    cur_frm.set_value("wegzug_zu", values.sektion_neu);
                    cur_frm.set_value("status_c", 'Wegzug');
                    cur_frm.save();
                    frappe.msgprint("Der Wechsel zur Sektion " + values.sektion_neu + " erfolgt.");
                } else {
                    frappe.msgprint("oops, da ist etwas schiefgelaufen!");
                }
            }
        });
    },
    'Sektionswechsel',
    'Übertragen'
    )
}

function erstelle_rechnung(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft.create_mitgliedschaftsrechnung",
        args:{
                'mitgliedschaft': cur_frm.doc.name
        },
        callback: function(r)
        {
            cur_frm.reload_doc();
        }
    });
}

function remove_sinv_plus(frm) {
    $(":button[data-doctype='Sales Invoice']").remove();
}

function setze_read_only(frm) {
    var i = 0;
    for (i; i<cur_frm.fields.length; i++) {
        cur_frm.set_df_property(cur_frm.fields[i].df.fieldname,'read_only', 1);
    }
}
