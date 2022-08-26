// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Kunden', {
    refresh: function(frm) {
        // buttons
        if (!frm.doc.__islocal) {
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
        
        // set strasse, plz und ort mandatory (Rechnungsempfänger)
        rechnungsadresse_mandatory(frm);
        // set firma mandatory (Kunde)
        firmenkunde_mandatory(frm);
        // set nachname und vorname mandatory (Eigener Rechnungsempfänger)
        rechnungsempfaenger_mandatory(frm);
        // set firma mandatory (Eigener Rechnungsempfänger)
        firmenrechnungsempfaenger_mandatory(frm);
    },
    abweichende_rechnungsadresse: function(frm) {
        // set strasse, plz und ort mandatory (Rechnungsempfänger)
        rechnungsadresse_mandatory(frm);
    },
    kundentyp: function(frm) {
        // set firma mandatory (Kunde)
        firmenkunde_mandatory(frm);
    },
    unabhaengiger_debitor: function(frm) {
        // set nachname und vorname mandatory (Eigener Rechnungsempfänger)
        rechnungsempfaenger_mandatory(frm);
    },
    rg_kundentyp: function(frm) {
        // set firma mandatory (Eigener Rechnungsempfänger)
        firmenrechnungsempfaenger_mandatory(frm);
    }
});

function rechnungsadresse_mandatory(frm) {
    // set strasse, plz und ort mandatory (Rechnungsempfänger)
    if (cur_frm.doc.abweichende_rechnungsadresse) {
        cur_frm.set_df_property('rg_strasse', 'reqd', 1);
        cur_frm.set_df_property('rg_plz', 'reqd', 1);
        cur_frm.set_df_property('rg_ort', 'reqd', 1);
    } else {
        cur_frm.set_df_property('rg_strasse', 'reqd', 0);
        cur_frm.set_df_property('rg_plz', 'reqd', 0);
        cur_frm.set_df_property('rg_ort', 'reqd', 0);
    }
}

function firmenkunde_mandatory(frm) {
    // set firma mandatory (Kunde)
    if (cur_frm.doc.kundentyp == 'Unternehmen') {
        cur_frm.set_df_property('firma', 'reqd', 1);
    } else {
        cur_frm.set_df_property('firma', 'reqd', 0);
    }
}

function rechnungsempfaenger_mandatory(frm) {
    // set nachname und vorname mandatory (Eigener Rechnungsempfänger)
    if (cur_frm.doc.abweichende_rechnungsadresse) {
        cur_frm.set_df_property('rg_nachname', 'reqd', 1);
        cur_frm.set_df_property('rg_vorname', 'reqd', 1);
    } else {
        cur_frm.set_df_property('rg_nachname', 'reqd', 0);
        cur_frm.set_df_property('rg_vorname', 'reqd', 0);
    }
}

function firmenrechnungsempfaenger_mandatory(frm) {
    // set firma mandatory (Kunde)
    if (cur_frm.doc.rg_kundentyp == 'Unternehmen') {
        cur_frm.set_df_property('rg_firma', 'reqd', 1);
    } else {
        cur_frm.set_df_property('rg_firma', 'reqd', 0);
    }
}
