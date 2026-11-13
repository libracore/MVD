frappe.ui.form.on('Rechnungsbereinigung', {
    refresh: function(frm) {
        var method = 'mvd.mvd.doctype.rechnungsbereinigung.rechnungsbereinigung.';
        var busy = ['Wartet auf Prüfung', 'Prüfung läuft', 'Wartet auf Bereinigung', 'Bereinigung läuft'];
        var selection;
        try { selection = JSON.parse(frm.doc.job_auswahl || 'null'); } catch (error) { selection = null; }
        var review_job = selection && (selection.art === 'freigabe' || selection.art === 'pruefung');
        frm.set_df_property('verarbeitet', 'label', review_job ? 'Im letzten Prüf-/Freigabeauftrag verarbeitet' :
            'Im letzten Bereinigungslauf verarbeitet');
        frm.set_df_property('company', 'read_only', frm.doc.status !== 'Neu');
        if (frm.is_new()) return;
        frm.add_custom_button(__('Fälle öffnen'), function() {
            frappe.route_options = {prueflauf: frm.doc.name};
            frappe.set_route('List', 'Rechnungsbereinigung Fall');
        });
        frm.add_custom_button(__('Aktualisieren'), function() { frm.reload_doc(); });
        if (frm.doc.status === 'Neu') {
            frm.add_custom_button(__('Prüfung starten'), function() {
                frappe.call({method: method + 'start_scan', args: {name: frm.doc.name},
                    freeze: true, callback: function() { frm.reload_doc(); }});
            });
        }
        if (['Bereit', 'Fehler'].indexOf(frm.doc.status) !== -1 && frm.doc.freigegeben > 0) {
            frm.add_custom_button(__('Freigegebene Fälle bereinigen'), function() {
                frappe.confirm(__(
                    '{0} freigegebene Fälle werden anhand des gespeicherten Prüfbefunds bereinigt, ohne erneute Datenprüfung. Stapel zu 25 werden einzeln gespeichert. Fortfahren?',
                    [frm.doc.freigegeben]), function() {
                    frappe.call({method: method + 'start_cleanup', args: {name: frm.doc.name, confirmed: 1},
                        freeze: true, callback: function() { frm.reload_doc(); }});
                });
            });
        }
        if (busy.indexOf(frm.doc.status) !== -1) {
            var headline = review_job ? __('Prüfung/Freigabe im Hintergrund: {0} von {1} Fällen verarbeitet.',
                [frm.doc.verarbeitet || 0, selection.faelle.length]) : __('Die Verarbeitung läuft im Hintergrund.');
            frm.dashboard.set_headline_alert(headline + ' ' + __('Den Fortschritt mit «Aktualisieren» laden.'));
        }
    }
});
