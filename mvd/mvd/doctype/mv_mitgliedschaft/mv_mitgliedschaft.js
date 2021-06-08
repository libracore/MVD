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
                    frappe.msgprint("tbd...");
            }, __("Erstelle"));
            
            get_adressdaten(frm);
        } else {
            frm.add_custom_button(__("Beziehe Mitgliedschaftsnummer"),  function() {
                    frappe.msgprint("tbd...");
            });
        }
	}
});

function get_adressdaten(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.mv_mitgliedschaft.mv_mitgliedschaft.get_address_overview",
        args:{
                'mvd': cur_frm.doc.name
        },
        callback: function(r)
        {
            cur_frm.dashboard.add_section(frappe.render_template('mv_mitgliedschaft_dashboard', {
				data: r.message
			}));
        }
    });
}

function sektionswechsel(frm) {
    frappe.prompt([
        {'fieldname': 'sektion_neu', 'fieldtype': 'Link', 'label': 'Neue Sektion', 'reqd': 1, 'options': 'MV Sektion'}  
    ],
    function(values){
        frappe.msgprint("Der Wechsel zur Sektion " + values.sektion_neu + " erfolgt.");
    },
    'Sektionswechsel',
    'Übertragen'
    )
}


