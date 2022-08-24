// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Kunden', {
    refresh: function(frm) {
        frm.add_custom_button(__("Rechnung"),  function() {
            erstelle_rechnung(frm);
        }, __("Erstelle"));
        
        frm.add_custom_button(__("Interessent*in"),  function() {
            umwandlung_interessent(frm);
        }, __("Umwandlung"));
        
        frm.add_custom_button(__("Anmeldung"),  function() {
            umwandlung_anmeldung(frm);
        }, __("Umwandlung"));
        
        frm.add_custom_button(__("Mitglied (Regulär)"),  function() {
            umwandlung_mitglied(frm);
        }, __("Umwandlung"));
    }
});
