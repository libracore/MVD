frappe.ui.form.on('Rechnungsbereinigung Fall', {
    setup: function(frm) {
        frm.set_query('ersatzrechnung', function() {
            return {filters: {customer: frm.doc.kunde, company: frm.doc.company, docstatus: 1, is_return: 0}};
        });
    },
    refresh: function(frm) {
        var method = 'mvd.mvd.doctype.rechnungsbereinigung.rechnungsbereinigung.';
        frm.set_df_property('ersatzrechnung', 'description', 'Optional. Eine Freigabe ist auch ohne Ersatzrechnung möglich.');
        frm.set_df_property('ersatzrechnung', 'read_only', frm.doc.status === 'Bereinigt');
        if (frm.is_new()) return;
        function review(approve) {
            function submit() {
                function call() {
                    frappe.call({method: method + 'review_cases',
                        args: {names: [frm.doc.name], approve: approve ? 1 : 0, confirmed: approve ? 1 : 0},
                        freeze: true, callback: function() { frm.reload_doc(); }});
                }
                if (frm.is_dirty()) frm.save().then(call); else call();
            }
            if (approve) {
                frappe.confirm(__('Ich gebe diesen Fall anhand des gespeicherten Prüfbefunds zur Bereinigung frei.'), submit);
            } else submit();
        }
        if (frm.doc.status !== 'Bereinigt') {
            frm.add_custom_button(__('Technisch prüfen'), function() { review(false); });
            frm.add_custom_button(__('Freigeben'), function() { review(true); });
        }
        frm.add_custom_button(__('Prüflauf öffnen'), function() {
            frappe.set_route('Form', 'Rechnungsbereinigung', frm.doc.prueflauf);
        });
        var requested_name = frm.doc.name;
        var requested_replacement = frm.doc.ersatzrechnung;
        frappe.call({method: method + 'case_details', args: {name: requested_name}, callback: function(response) {
            if (frm.doc.name !== requested_name || frm.doc.ersatzrechnung !== requested_replacement) return;
            var data = response.message;
            var esc = function(value) { return $('<span>').text(value == null ? '' : String(value)).html(); };
            function table(rows, columns) {
                var html = '<div class="table-responsive"><table class="table table-bordered"><thead><tr>';
                columns.forEach(function(column) { html += '<th>' + esc(column[1]) + '</th>'; });
                html += '</tr></thead><tbody>';
                rows.forEach(function(row) {
                    html += '<tr>';
                    columns.forEach(function(column) { html += '<td>' + esc(row[column[0]]) + '</td>'; });
                    html += '</tr>';
                });
                return html + '</tbody></table></div>';
            }
            function section(title, state) {
                if (!state) return '<h4>' + esc(title) + '</h4><p>Keine Ersatzrechnung ausgewählt.</p>';
                return '<h4>' + esc(title) + '</h4>' + table(state.hauptbuch,
                    [['account', 'Konto'], ['posting_date', 'Datum'], ['party', 'Kunde'], ['account_currency', 'Währung'],
                        ['debit', 'Soll (Basiswährung)'], ['credit', 'Haben (Basiswährung)']]) + table(state.positionen,
                    [['item_code', 'Artikel'], ['item_name', 'Bezeichnung'], ['qty', 'Menge'], ['rate', 'Preis'], ['amount', 'Betrag']]) +
                    '<p>Weitere Bezüge: ' + esc(state.bezuege.length) + '</p>' + table(state.bezuege,
                    [['doctype', 'Belegart'], ['beleg', 'Beleg']]);
            }
            var candidates = (data.kandidaten || []).map(function(name) {
                return '<a href="#Form/Sales%20Invoice/' + encodeURIComponent(name) + '">' + esc(name) + '</a>';
            }).join(', ');
            frm.fields_dict.vergleich.$wrapper.html('<p>Mögliche Ersatzrechnungen: ' +
                (candidates || 'Keine Vorschläge') + '</p><p>Originaldaten aus dem gespeicherten Prüfbefund; Ersatzdaten aktuell.</p>' +
                section('Fehlende Rechnung', data.original) + section('Ersatzrechnung', data.ersatz));
        }});
    }
});
