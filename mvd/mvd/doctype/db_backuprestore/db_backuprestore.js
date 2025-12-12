// Copyright (c) 2025, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('DB BackupRestore', {
    create_json: function(frm) {
        frappe.dom.freeze('Bitte warten, das JSON-File wird erzeugt...');
        frm.call('create_json', {}).then(r => {
            frappe.dom.unfreeze();
            cur_frm.reload_doc();
            frappe.msgprint("Das JSON wurde erzeugt");
        });
    },
    load_json: function(frm) {
        frappe.confirm(
            '<b>Achtung:</b> Alle Daten in der DB werden durch jene im JSON ersetzt!<br>Wollen Sie fortfahren?',
            function(){
                // on yes
                frappe.dom.freeze('Bitte warten, das JSON-File wird eingelesen...');
                frm.call('load_json', {}).then(r => {
                    frappe.dom.unfreeze();
                    frappe.msgprint("Das JSON wird via Backgroundjob eingelesen");
                });
            },
            function(){
                // on no
                frappe.show_alert('Einlesen abgebrochen')
            }
        )
    }
});
