// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('MV Mitgliedschaft', {
	refresh: function(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__("Kündigung"),  function() {
                    frappe.msgprint("tbd...");
            }, __("Mutation"));
            frm.add_custom_button(__("Ausschluss"),  function() {
                    frappe.msgprint("tbd...");
            }, __("Mutation"));
            frm.add_custom_button(__("Sektionswechsel"),  function() {
                    sektionswechsel(frm);
            }, __("Mutation"));
            frm.add_custom_button(__("Mitgliedschafts-Rechnung"),  function() {
                    erstelle_rechnung(frm);
            }, __("Erstelle"));
            
            get_adressdaten(frm);
        } else {
            frm.add_custom_button(__("Beziehe Mitgliedschaftsnummer"),  function() {
                    frappe.msgprint("tbd...");
            });
        }
        
        remove_sinv_plus(frm);
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

function sektionswechsel(frm) {
    frappe.prompt([
        {'fieldname': 'sektion_neu', 'fieldtype': 'Link', 'label': 'Neue Sektion', 'reqd': 1, 'options': 'Sektion'}  
    ],
    function(values){
        frappe.msgprint("Der Wechsel zur Sektion " + values.sektion_neu + " erfolgt. (TBD!)");
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
