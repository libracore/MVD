// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('MVD Settings', {
    // Dieser Trigger feuert, wenn der Button im Formular geklickt wird
    btn_create_nichtzahler_statistik: function(frm) {
        
        let d = new frappe.ui.Dialog({
            title: __('Jahr für Statistik auswählen'),
            fields: [
                {
                    label: __('Berichtsjahr'),
                    fieldname: 'year',
                    fieldtype: 'Int',
                    default: new Date().getFullYear() - 1,
                    reqd: 1
                }
            ],
            primary_action_label: __('Starten'),
            primary_action(values) {
                d.hide();
                
                frappe.call({
                    method: 'mvd.mvd.doctype.yearly_snap.yearly_snap.erstelle_nichtzahler_statistik',
                    args: {
                        year: values.year
                    },
                    freeze: true,
                    freeze_message: __('Generiere Statistik...'),
                    callback: function(r) {
                        if (r.message) {
                            frappe.show_alert({
                                message: __('Statistik für {0} erfolgreich erstellt', [values.year]),
                                indicator: 'green'
                            });
                        }
                    }
                });
            }
        });
        d.show();
    }
});