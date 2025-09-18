// Copyright (c) 2025, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mitglied RG Jahreslauf', {
    refresh: function(frm) {
        frm.call('get_overview', {}).then(r => {
            const sektionen = r.message;
            const mapLegend = {
                0: "⚠️",
                1: "✅",
                2: ""
            };
            const rows = sektionen.map(s => {
                const symbols = s.docs.map(d => mapLegend[d]).join(" ");
                return `
                    <tr>
                        <td>${s.sektion}</td>
                        <td><center>${symbols}</center></td>
                    </tr>`
            }).join(" ");
            const table = `<table style="width: 50%;"><tr><th>Sektion</th><th><center>Status</center></th></tr>${rows}</table>`
            cur_frm.set_df_property('sektions_overview', 'options', table);
        });
    },
    start_rg: function(frm) {
        frm.call('check_start_rg', {}).then(r => {
            if (r.message > 0) {
                frappe.confirm(
                    'Es wurden noch nicht alle Sektions Selektionen verbucht, wollen Sie den RG Erstellungsprozess trotzdem starten?',
                    function(){
                        // on yes
                        frm.call('start_rg', {}).then(r => {
                            frappe.msg_print("Der RG Erstellungsprozess wurde gestartet")
                            cur_frm.reload_doc();
                        });
                    },
                    function(){
                        // on no do nothing
                    }
                )
            } else {
                frm.call('start_rg', {}).then(r => {
                    frappe.msg_print("Der RG Erstellungsprozess wurde gestartet")
                    cur_frm.reload_doc();
                });
            }
        });
    },
    stop_rg: function(frm) {
        frm.call('stop_rg', {}).then(r => {
            frappe.msg_print("Der RG Erstellungsprozess wurde abgebrochen")
            cur_frm.reload_doc();
        });
    }
});
