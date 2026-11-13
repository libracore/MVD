frappe.listview_settings['Rechnungsbereinigung Fall'] = {
    add_fields: ['status', 'prueflauf', 'ersatzrechnung'],
    get_indicator: function(doc) {
        var colors = {'Offen': 'orange', 'Prüfbar': 'blue', 'Freigegeben': 'purple',
            'Bereinigt': 'green', 'Blockiert': 'red', 'Zurückgestellt': 'gray'};
        return [__(doc.status), colors[doc.status], 'status,=,' + doc.status];
    },
    onload: function(listview) {
        var method = 'mvd.mvd.doctype.rechnungsbereinigung.rechnungsbereinigung.';
        function action(operation, approve) {
            var docs = listview.get_checked_items();
            var limit = operation === 'review_cases' ? 5000 : 100;
            if (!docs.length || docs.length > limit) {
                frappe.msgprint(__('Bitte 1 bis {0} Fälle desselben Prüflaufs auswählen.', [limit]));
                return;
            }
            if (docs.some(function(doc) { return doc.prueflauf !== docs[0].prueflauf; })) {
                frappe.msgprint(__('Bitte Fälle desselben Prüflaufs auswählen.'));
                return;
            }
            function submit() {
                var args = {names: docs.map(function(doc) { return doc.name; })};
                if (operation === 'review_cases') {
                    args.approve = approve ? 1 : 0;
                    args.confirmed = approve ? 1 : 0;
                    args.background = 1;
                }
                if (operation === 'start_cleanup') {
                    args.name = docs[0].prueflauf;
                    args.confirmed = 1;
                }
                frappe.call({method: method + operation, args: args, freeze: true,
                    callback: function(response) {
                        listview.refresh();
                        if (operation === 'review_cases') {
                            if (response.message && response.message.queued) {
                                frappe.msgprint(__('Der Prüf-/Freigabeauftrag für {0} Fälle läuft im Hintergrund. Den Fortschritt im Prüflauf ansehen.',
                                    [response.message.anzahl]));
                                return;
                            }
                            var rows = response.message || [];
                            var blocked = rows.filter(function(row) { return row.status === 'Blockiert'; }).length;
                            frappe.msgprint(__('Verarbeitet: {0}. Davon blockiert: {1}.', [rows.length, blocked]));
                        } else if (operation === 'start_cleanup') {
                            frappe.msgprint(__('Die Bereinigung läuft im Hintergrund. Fortschritt im Prüflauf ansehen.'));
                        }
                    }});
            }
            if (approve) {
                frappe.confirm(__('Ich gebe die {0} ausgewählten Fälle anhand des gespeicherten Prüfbefunds zur Bereinigung frei.', [docs.length]), submit);
            } else if (operation === 'start_cleanup') {
                frappe.confirm(__('Die ausgewählten freigegebenen Fälle werden anhand des gespeicherten Prüfbefunds bereinigt, ohne erneute Datenprüfung. Stapel zu 25 werden einzeln gespeichert. Fortfahren?'), submit);
            } else {
                submit();
            }
        }
        listview.page.add_action_item(__('Technisch prüfen'), function() { action('review_cases', false); });
        listview.page.add_action_item(__('Freigeben'), function() { action('review_cases', true); });
        listview.page.add_action_item(__('Zurückstellen'), function() { action('defer_cases', false); });
        listview.page.add_action_item(__('Freigegebene bereinigen'), function() { action('start_cleanup', false); });
    }
};
