// Copyright (c) 2022, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('CAMT Import', {
    refresh: function(frm) {
        // hidding Version 1 of CAMT Importer
        if (cur_frm.doc.version_1) {
            cur_frm.set_df_property('section_steuerung','hidden', 1);
            cur_frm.set_df_property('overview','hidden', 1);
            cur_frm.set_df_property('section_verarbeitungs_daten','hidden', 1);
            cur_frm.set_df_property('section_redesign','hidden', 1);
            cur_frm.set_df_property('section_ungebucht','hidden', 1);
            cur_frm.set_df_property('section_import','hidden', 1);
        }
        
        // auto save
        if (frm.doc.__islocal) {
           if (frappe.boot.default_sektion) {
               cur_frm.set_value("sektion_id", frappe.boot.default_sektion);
           }
           cur_frm.save();
        }
        // filter account
        cur_frm.fields_dict['account'].get_query = function(doc) {
            return {
                filters: {
                    'account_type': 'Bank',
                    'company': cur_frm.doc.company
                }
            }
        }
        
        if (cur_frm.doc.status != 'Open') {
            cur_frm.set_df_property('account','read_only',1);
            cur_frm.set_df_property('company','read_only',1);
            cur_frm.set_df_property('sektion_id','read_only',1);
            cur_frm.set_df_property('camt_file','read_only',1);
            if (cur_frm.doc.status == 'Aktualisierung notwendig') {
                aktualisiere_camt_uebersicht(frm);
            }
            cur_frm.set_df_property('html_report','options', cur_frm.doc.report);
        }
        
        if (frappe.user.has_role("System Manager")) {
            frm.add_custom_button(__("Manuelle Status Änderung"), function() {
                change_state_manual(frm);
            }).addClass("btn-warning")
        }
    },
    account: function(frm) {
        cur_frm.save();
    },
    import: function(frm) {
        if (cur_frm.doc.account) {
            if (cur_frm.is_dirty()) {
                cur_frm.save();
                import_payments(frm, 1, 1, 1);
            } else {
                import_payments(frm, 1, 1, 1);
            }
        } else {
            frappe.msgprint("Bitte zuerst eine Sektion / ein Account auswählen");
        }
    },
    nur_zahlungen_einlesen: function(frm) {
        if (cur_frm.doc.account) {
            if (cur_frm.is_dirty()) {
                cur_frm.save();
                import_payments(frm, 1, 0, 0);
            } else {
                import_payments(frm, 1, 0, 0);
            }
        } else {
            frappe.msgprint("Bitte zuerst eine Sektion / ein Account auswählen");
        }
    },
    zahlungen_matchen: function(frm) {
        if (cur_frm.doc.account) {
            if (cur_frm.is_dirty()) {
                cur_frm.save();
                import_payments(frm, 0, 1, 0);
            } else {
                import_payments(frm, 0, 1, 0);
            }
        } else {
            frappe.msgprint("Bitte zuerst eine Sektion / ein Account auswählen");
        }
    },
    zahlungen_verbuchen: function(frm) {
        if (cur_frm.doc.account) {
            if (cur_frm.is_dirty()) {
                cur_frm.save();
                import_payments(frm, 0, 0, 1);
            } else {
                import_payments(frm, 0, 0, 1);
            }
        } else {
            frappe.msgprint("Bitte zuerst eine Sektion / ein Account auswählen");
        }
    },
    show_overpaid: function(frm) {
        frappe.route_options = {
            "camt_import": cur_frm.doc.name,
            "camt_status": 'Überbezahlt'
        }
        frappe.set_route("List", "Payment Entry");
    },
    show_unassigned: function(frm) {
        frappe.route_options = {
            "camt_import": cur_frm.doc.name,
            "camt_status": 'Nicht zugewiesen',
            "docstatus": 0
        }
        frappe.set_route("List", "Payment Entry");
    },
    //~ close_camt_import: function(frm) {
        //~ frappe.confirm(
            //~ 'Es wurden nicht alle Zahlungen zugewiesen/verbucht, möchten Sie den CAMT Import trotzdem schliessen?',
            //~ function(){
                //~ // on yes
                //~ cur_frm.set_value("status", "Closed");
                //~ cur_frm.save();
            //~ },
            //~ function(){
                //~ // on no
            //~ }
        //~ )
    //~ },
    aktualisiere_camt_uebersicht: function(frm) {
        aktualisiere_camt_uebersicht(frm);
    },
    show_imported_payments: function(frm) {
        frappe.route_options = {"camt_import": cur_frm.doc.name}
        frappe.set_route("List", "Payment Entry");
    },
    //~ show_unsubmitted_payments: function(frm) {
        //~ frappe.route_options = {
            //~ "camt_import": cur_frm.doc.name,
            //~ "docstatus": 0
        //~ }
        //~ frappe.set_route("List", "Payment Entry");
    //~ },
    //~ show_submitted_payments: function(frm) {
        //~ frappe.route_options = {
            //~ "camt_import": cur_frm.doc.name,
            //~ "docstatus": 1
        //~ }
        //~ frappe.set_route("List", "Payment Entry");
    //~ },
    //~ show_matched_payments: function(frm) {
        //~ frappe.route_options = {
            //~ "camt_import": cur_frm.doc.name,
            //~ "camt_status": ['!=', 'Nicht zugewiesen']
        //~ }
        //~ frappe.set_route("List", "Payment Entry");
    //~ },
    //~ show_canceled_payments: function(frm) {
        //~ frappe.route_options = {
            //~ "camt_import": cur_frm.doc.name,
            //~ "docstatus": 2
        //~ }
        //~ frappe.set_route("List", "Payment Entry");
    //~ },
    //~ show_doppelte_mitgliedschaft: function(frm) {
        //~ frappe.route_options = {
            //~ "camt_import": cur_frm.doc.name,
            //~ "camt_status": 'Doppelte Mitgliedschafts-Zahlung'
        //~ }
        //~ frappe.set_route("List", "Payment Entry");
    //~ },
    //~ show_wegzuege: function(frm) {
        //~ frappe.route_options = {
            //~ "camt_import": cur_frm.doc.name,
            //~ "camt_status": 'Wegzug'
        //~ }
        //~ frappe.set_route("List", "Payment Entry");
    //~ },
    //~ show_underpaid: function(frm) {
        //~ frappe.route_options = {
            //~ "camt_import": cur_frm.doc.name,
            //~ "camt_status": 'Unterbezahlt'
        //~ }
        //~ frappe.set_route("List", "Payment Entry");
    //~ },
    show_zugewiesen_unverbucht: function(frm) {
        frappe.route_options = {
            "camt_import": cur_frm.doc.name,
            "camt_status": 'Zugewiesen',
            "docstatus": 0
        }
        frappe.set_route("List", "Payment Entry");
    }
});

function import_payments(frm, einlesen, matchen, verbuchen) {
    cur_frm.set_value("status", "In Verarbeitung");
    cur_frm.save().then(function(){
        frappe.call({
            method: 'mvd.mvd.doctype.camt_import.camt_import.lese_camt_file',
            args: {
                'file_path': cur_frm.doc.camt_file,
                'camt_import': cur_frm.doc.name,
                'einlesen': einlesen,
                'matchen': matchen,
                'verbuchen': verbuchen
            },
            callback: function(r) {
                //~ frappe.dom.freeze('Bitte warten, die Zahlungen werden importiert...');
                //~ let import_refresher = setInterval(import_refresh_handler, 3000);
                //~ function import_refresh_handler() {
                    //~ if (cur_frm.doc.status == 'In Verarbeitung') {
                        //~ cur_frm.reload_doc();
                    //~ } else {
                        //~ clearInterval(import_refresher);
                        //~ frappe.dom.unfreeze();
                        //~ aktualisiere_camt_uebersicht(frm);
                    //~ }
                //~ }
                frappe.msgprint("Der CAMT-Import wurde gestartet.<br>Sie können den Fortschritt <a href='/desk#background_jobs'>hier</a> verfolgen.");
            }
        });
    });
}

function aktualisiere_camt_uebersicht(frm) {
    //~ cur_frm.set_value("status", "In Verarbeitung");
    //~ cur_frm.save().then(function(){
    if (!cur_frm.doc.version_1) {
        frappe.call({
            method: 'mvd.mvd.doctype.camt_import.camt_import.aktualisiere_camt_uebersicht',
            args: {
                'camt_import': cur_frm.doc.name
            },
            freeze: true,
            freeze_message: 'Analysiere Daten...',
            callback: function(r) {
                cur_frm.reload_doc();
            }
        });
    } else {
        frappe.msgprint("Dieser Datensatz wurde mit einer vorgänger Version des CAMT Importers erzeugt.", "Diese Funktion steht leider nicht zur Verfügung");
    }
    //~ });
}

function change_state_manual(frm) {
    frappe.prompt([
        {'fieldname': 'new_state', 'fieldtype': 'Select', 'label': 'Neuer Astatus', 'options': "Open\nZahlungen eingelesen\nZahlungen zugeordnet\nClosed", 'reqd': 1}  
    ],
    function(values){
        cur_frm.set_value("status", values.new_state);
        cur_frm.save()
    },
    'Manuelle Status Änderung',
    'Ändern'
    )
}
