// Copyright (c) 2026, libracore AG and contributors
// For license information, please see license.txt

frappe.provide('frappe.mvd');

frappe.mvd.camt_aktions_button = function(frm, aktion, label, handler) {
    const anchor = frm.fields_dict.zahlungen_verbuchen.$wrapper;
    let area = anchor.next('.camt-zusatzaktionen');
    if (!area.length) {
        area = $('<div class="camt-zusatzaktionen"></div>').insertAfter(anchor);
        ['firmenverrechnung', 'firmenverrechnung_stornieren', 'bankkonto'].forEach(name => {
            $('<div class="frappe-control hide-control"></div>')
                .attr('data-camt-aktion', name).appendTo(area);
        });
    }
    const slot = area.find('[data-camt-aktion="' + aktion + '"]');
    slot.empty().toggleClass('hide-control', !handler);
    if (handler) {
        const group = $('<div class="form-group"></div>').appendTo(slot);
        $('<button type="button" class="btn btn-default btn-xs"></button>')
            .text(label).on('click', handler).appendTo(group);
    }
    frm.layout.refresh_sections();
};

frappe.mvd.aktualisiere_verrechnungs_buttons = function(frm) {
    const request = (frm.__camt_verrechnung_request || 0) + 1;
    frm.__camt_verrechnung_request = request;
    frm.remove_custom_button(__('Firmenverrechnung'));
    frm.remove_custom_button(__('Firmenverrechnung stornieren'));
    frappe.mvd.camt_aktions_button(frm, 'firmenverrechnung', __('Firmenverrechnung'), null);
    frappe.mvd.camt_aktions_button(frm, 'firmenverrechnung_stornieren', __('Firmenverrechnung stornieren'), null);
    if (frm.doc.__islocal || frm.is_dirty() || frm.doc.status === 'In Verarbeitung' ||
        !['System Manager', 'MV_RW', 'MV_GL'].some(role => frappe.user.has_role(role))) return;
    const name = frm.doc.name;
    frappe.call({
        method: 'mvd.mvd.doctype.camt_import.verrechnung.verfuegbare_aktionen',
        args: {camt_import: name},
        callback: function(r) {
            if (frm.__camt_verrechnung_request !== request || frm.doc.name !== name ||
                frm.is_dirty() || frm.doc.status === 'In Verarbeitung') return;
            if (r.message && r.message.verrechnen) {
                frappe.mvd.camt_aktions_button(frm, 'firmenverrechnung', __('Firmenverrechnung'),
                    () => frappe.mvd.camt_verrechnung(frm));
            }
            if (r.message && r.message.stornieren) {
                frappe.mvd.camt_aktions_button(frm, 'firmenverrechnung_stornieren', __('Firmenverrechnung stornieren'),
                    () => frappe.mvd.camt_verrechnung_stornieren(frm));
            }
        }
    });
};

frappe.mvd.camt_verrechnung = function(frm) {
    if (frm.is_dirty()) {
        frappe.msgprint('Bitte speichern Sie den CAMT-Import zuerst.');
        return;
    }
    const method = 'mvd.mvd.doctype.camt_import.verrechnung.';
    const esc = value => frappe.utils.escape_html(String(value == null ? '' : value));
    const link = (doctype, name) => '<a href="/desk#Form/' + encodeURIComponent(doctype) + '/' +
        encodeURIComponent(name) + '">' + esc(name) + '</a>';
    frappe.call({
        method: method + 'kandidaten', args: {camt_import: frm.doc.name},
        callback: function(r) {
            const candidates = r.message.kandidaten;
            if (!candidates.length) {
                frappe.msgprint('Keine verrechenbaren Zahlungen gefunden.<br>' +
                    r.message.ausgelassen.map(row => esc(row.payment_entry) + ': ' + esc(row.grund)).join('<br>'));
                return;
            }
            let dialog;
            const selected = () => candidates.find(row => row.payment_entry === dialog.get_value('payment_entry'));
            dialog = new frappe.ui.Dialog({
                title: 'Firmenverrechnung vorbereiten',
                no_submit_on_enter: true,
                fields: [
                    {fieldname: 'payment_entry', fieldtype: 'Select', label: 'Blockierte Zahlung', reqd: 1,
                        options: candidates.map(row => row.payment_entry).join('\n'),
                        change: function() {
                            if (!dialog) return;
                            apply_defaults();
                        }},
                    {fieldname: 'context', fieldtype: 'HTML'},
                    {fieldname: 'alle_vorbereiten', fieldtype: 'Button',
                        label: 'Alle gemeinsam vorbereiten (' + candidates.length + ')',
                        hidden: candidates.length < 2, click: show_batch_dialog},
                    {fieldname: 'verbindlichkeit', fieldtype: 'Link', options: 'Account', reqd: 1,
                        label: 'Verbindlichkeitskonto der Importfirma gegenüber der Rechnungsfirma',
                        description: 'Passiv-Bilanzkonto ohne Debitoren- oder Kreditorentyp.',
                        get_query: () => ({filters: {company: selected().source_company, root_type: 'Liability',
                            is_group: 0, disabled: 0, account_type: ['not in', ['Bank', 'Cash', 'Receivable', 'Payable']]}})},
                    {fieldname: 'forderung', fieldtype: 'Link', options: 'Account', reqd: 1,
                        label: 'Forderungskonto der Rechnungsfirma gegenüber der Importfirma',
                        description: 'Aktiv-Bilanzkonto ohne Debitoren- oder Kreditorentyp.',
                        get_query: () => ({filters: {company: selected().target_company, root_type: 'Asset',
                            is_group: 0, disabled: 0, account_type: ['not in', ['Bank', 'Cash', 'Receivable', 'Payable']]}})}
                ],
                primary_action_label: 'Vorschau anzeigen',
                primary_action: function(values) {
                    frappe.call({method: method + 'vorschau', args: {camt_import: frm.doc.name,
                        payment_entry: values.payment_entry, verbindlichkeit: values.verbindlichkeit, forderung: values.forderung},
                        callback: response => show_preview(response.message)});
                }
            });
            function apply_defaults() {
                const row = selected();
                dialog.set_value('verbindlichkeit', row && row.default_verbindlichkeit || '');
                dialog.set_value('forderung', row && row.default_forderung || '');
                show_context();
            }
            function show_context() {
                const row = selected();
                if (!row) return;
                dialog.set_df_property('context', 'options', '<p>' + esc(row.amount.toFixed(2)) + ' ' + esc(row.currency) +
                    ' von <b>' + esc(row.source_company) + '</b> an <b>' + esc(row.target_company) + '</b> verrechnen.</p>' +
                    '<p>Eingangskonto: ' + esc(row.bank_account) + '<br>Rechnung: ' + link(row.reference_doctype, row.reference_name) + '</p>');
            }
            function preview_html(plan) {
                const rows = plan.buchungen.map(row => '<tr><td>' + esc(row.firma) + '</td><td>' + esc(row.soll) +
                    '</td><td>' + esc(row.haben) + '</td><td>' + esc(row.betrag.toFixed(2)) + ' ' + esc(plan.currency) + '</td></tr>').join('');
                return '<p>Zahlung ' + link('Payment Entry', plan.payment_entry) + ' für ' +
                    link(plan.reference_doctype, plan.reference_name) + '.</p>' +
                    '<p>Buchungsdatum: ' + esc(plan.posting_date) + '<br>Offener Rechnungsbetrag: ' +
                    esc(plan.outstanding_amount.toFixed(2)) + ' → ' + esc((plan.outstanding_amount - plan.amount).toFixed(2)) +
                    ' ' + esc(plan.currency) + '</p>' +
                    '<table class="table table-bordered"><thead><tr><th>Firma</th><th>Soll</th><th>Haben</th><th>Betrag</th></tr></thead><tbody>' +
                    rows + '</tbody></table>';
            }
            function show_batch_dialog() {
                const groups = [];
                const group_keys = {};
                const selected_row = selected();
                function group_for(row, role) {
                    const source = role === 'verbindlichkeit';
                    const company = source ? row.source_company : row.target_company;
                    const section = (source ? row.source_section : row.target_section) || company;
                    const partner_company = source ? row.target_company : row.source_company;
                    const partner = (source ? row.target_section : row.source_section) || partner_company;
                    const key = JSON.stringify([role, section, company, partner, partner_company]);
                    if (!group_keys[key]) {
                        const current_section = (source ? selected_row.source_section : selected_row.target_section) ||
                            (source ? selected_row.source_company : selected_row.target_company);
                        const current_partner = (source ? selected_row.target_section : selected_row.source_section) ||
                            (source ? selected_row.target_company : selected_row.source_company);
                        const manual = section === current_section && partner === current_partner ? dialog.get_value(role) : '';
                        group_keys[key] = {fieldname: 'konto_' + groups.length, company: company,
                            section: section, partner: partner, role: role, root_type: source ? 'Liability' : 'Asset',
                            value: manual || row['default_' + role] || ''};
                        groups.push(group_keys[key]);
                    }
                    return group_keys[key];
                }
                const selection = candidates.map(row => ({payment_entry: row.payment_entry,
                    verbindlichkeit: group_for(row, 'verbindlichkeit').fieldname,
                    forderung: group_for(row, 'forderung').fieldname}));
                const skipped = r.message.ausgelassen || [];
                const fields = [{fieldname: 'info', fieldtype: 'HTML', options:
                    '<p><b>' + esc(candidates.length) + ' verrechenbare Zahlungen gemeinsam vorbereiten.</b> ' +
                    'Bitte ergänzen oder prüfen Sie die Konten je Sektion. Danach werden alle Buchungen zur Prüfung angezeigt.</p>' +
                    (skipped.length ? '<p>Nicht enthalten: ' + skipped.map(row => esc(row.payment_entry) + ': ' + esc(row.grund)).join('<br>') + '</p>' : '')}];
                groups.forEach(group => fields.push({fieldname: group.fieldname, fieldtype: 'Link', options: 'Account', reqd: 1,
                    label: (group.role === 'verbindlichkeit' ? 'Verbindlichkeitskonto: ' : 'Forderungskonto: ') +
                        group.section + ' gegenüber ' + group.partner,
                    get_query: () => ({filters: {company: group.company, root_type: group.root_type,
                        is_group: 0, disabled: 0, account_type: ['not in', ['Bank', 'Cash', 'Receivable', 'Payable']]}})}));
                const batch = new frappe.ui.Dialog({title: 'Alle Firmenverrechnungen vorbereiten',
                    no_submit_on_enter: true, fields: fields, primary_action_label: 'Gemeinsame Vorschau anzeigen',
                    primary_action: function(values) {
                        const payments = selection.map(row => ({payment_entry: row.payment_entry,
                            verbindlichkeit: values[row.verbindlichkeit], forderung: values[row.forderung]}));
                        frappe.call({method: method + 'vorschau_alle',
                            args: {camt_import: frm.doc.name, zahlungen: JSON.stringify(payments)},
                            callback: response => show_batch_preview(response.message, payments, batch)});
                    }});
                groups.forEach(group => batch.set_value(group.fieldname, group.value));
                batch.show();
            }
            function show_batch_preview(plan, payments, batch) {
                const preview = new frappe.ui.Dialog({title: 'Vorschau aller Firmenverrechnungen', no_submit_on_enter: true,
                    fields: [{fieldname: 'preview', fieldtype: 'HTML', options:
                        '<p><b>' + esc(plan.anzahl) + ' Zahlungen, insgesamt ' + esc(plan.betrag.toFixed(2)) + ' ' + esc(plan.currency) + '.</b></p>' +
                        '<p>Alle angezeigten Buchungen werden gemeinsam ausgeführt. Bei einem Fehler wird die gesamte Sammelbuchung zurückgenommen. ' +
                        'Es wird kein Bankübertrag erfasst. Die normalen Mitgliedschaftsprozesse und Zahlungsbestätigungen folgen nach erfolgreichem Abschluss.</p>' +
                        plan.plaene.map(preview_html).join('<hr>')}],
                    primary_action_label: 'Alle ' + plan.anzahl + ' Verrechnungen buchen',
                    primary_action: function() {
                        preview.get_primary_btn().prop('disabled', true);
                        frappe.call({method: method + 'buchen_alle',
                            args: {camt_import: frm.doc.name, zahlungen: JSON.stringify(payments), token: plan.token},
                            freeze: true, freeze_message: 'Buche Firmenverrechnungen...',
                            error: () => preview.get_primary_btn().prop('disabled', false),
                            callback: function(response) {
                                preview.hide();
                                batch.hide();
                                dialog.hide();
                                frm.reload_doc();
                                frappe.msgprint(esc(response.message.anzahl) + ' Firmenverrechnungen gebucht:<br>' +
                                    response.message.buchungen.map(row => link('Payment Entry', row.payment_entry) + ' / ' +
                                        link('Journal Entry', row.journal_entry) + ' / ' + link('Sales Invoice', row.sales_invoice)).join('<br>'));
                            }});
                    }});
                preview.show();
            }
            function show_preview(plan) {
                const preview = new frappe.ui.Dialog({
                    title: 'Vorschau Firmenverrechnung',
                    no_submit_on_enter: true,
                    fields: [{fieldname: 'preview', fieldtype: 'HTML', options:
                        preview_html(plan) + '<p>Die Zahlung der Importfirma wird ohne Rechnungsreferenz gebucht. ' +
                        'Ein Journal Entry in der Rechnungsfirma verrechnet den Betrag mit der Rechnung. Es wird kein Bankübertrag erfasst. ' +
                        'Die Salden auf den beiden Verrechnungskonten bleiben bestehen.</p>' +
                        (plan.reference_doctype === 'Fakultative Rechnung' ? '<p>Die fakultative Rechnung wird dafür in eine Sales Invoice umgewandelt.</p>' : '') +
                        '<p>Nach Abschluss beider Buchungen werden im Hintergrund dieselben Mitgliedschaftsprozesse und ' +
                        'Zahlungsbestätigungen wie bei einer normalen Rechnungszahlung ausgeführt, gemäss den bestehenden Einstellungen.</p>'}],
                    primary_action_label: 'Verrechnung buchen',
                    primary_action: function() {
                        preview.get_primary_btn().prop('disabled', true);
                        frappe.call({
                            method: method + 'buchen',
                            args: {camt_import: frm.doc.name, payment_entry: plan.payment_entry,
                                verbindlichkeit: plan.verbindlichkeit, forderung: plan.forderung, token: plan.token},
                            freeze: true, freeze_message: 'Buche Firmenverrechnung...',
                            error: () => preview.get_primary_btn().prop('disabled', false),
                            callback: function(result) {
                                preview.hide();
                                dialog.hide();
                                frm.reload_doc();
                                frappe.msgprint('Firmenverrechnung gebucht:<br>Zahlung: ' + link('Payment Entry', result.message.payment_entry) +
                                    '<br>Gegenbuchung: ' + link('Journal Entry', result.message.journal_entry) +
                                    '<br>Rechnung: ' + link('Sales Invoice', result.message.sales_invoice));
                            }
                        });
                    }
                });
                preview.show();
            }
            dialog.set_value('payment_entry', candidates[0].payment_entry);
            apply_defaults();
            dialog.show();
        }
    });
};

frappe.mvd.camt_verrechnung_stornieren = function(frm) {
    if (frm.is_dirty()) {
        frappe.msgprint('Bitte speichern Sie den CAMT-Import zuerst.');
        return;
    }
    const method = 'mvd.mvd.doctype.camt_import.verrechnung.';
    frappe.call({method: method + 'gebuchte_verrechnungen', args: {camt_import: frm.doc.name}, callback: function(r) {
        if (!r.message.length) {
            frappe.msgprint('Dieser CAMT-Import enthält keine gebuchten Firmenverrechnungen.');
            return;
        }
        frappe.prompt([
            {fieldname: 'payment_entry', fieldtype: 'Select', label: 'Zu stornierende Zahlung', reqd: 1,
                options: r.message.map(row => row.name).join('\n')},
            {fieldname: 'info', fieldtype: 'HTML', options: '<p>Die Zahlung und ihre Gegenbuchung werden gemeinsam storniert. ' +
                'Die Rechnung wird wieder offen. Eine neue ungebuchte Zahlung wird zur erneuten Bearbeitung angelegt. ' +
                'Eine für eine FAK erzeugte Sales Invoice bleibt als offene Rechnung bestehen. ' +
                'Bereits ausgelöste Beitrittsprozesse und erstellte Korrespondenz werden durch den Belegstorno nicht zurückgenommen.</p>'}
        ], function(values) {
            frappe.call({method: method + 'stornieren', args: {camt_import: frm.doc.name, payment_entry: values.payment_entry},
                freeze: true, freeze_message: 'Storniere Firmenverrechnung...', callback: function(result) {
                    frm.reload_doc();
                    frappe.msgprint('Firmenverrechnung storniert. Neue ungebuchte Zahlung: ' + frappe.utils.escape_html(result.message.payment_entry));
                }});
        }, 'Firmenverrechnung stornieren', 'Gemeinsam stornieren');
    }});
};

frappe.mvd.aktualisiere_bankkonto_button = function(frm) {
    const request = (frm.__camt_bankkonto_request || 0) + 1;
    frm.__camt_bankkonto_request = request;
    frm.remove_custom_button(__('Bankkonto zuordnen'));
    frappe.mvd.camt_aktions_button(frm, 'bankkonto', __('Bankkonto zuordnen'), null);
    if (frm.doc.__islocal || frm.is_dirty() || frm.doc.status === 'In Verarbeitung' ||
        !['System Manager', 'MV_RW', 'MV_GL'].some(role => frappe.user.has_role(role))) return;
    const name = frm.doc.name;
    frappe.call({
        method: 'mvd.mvd.doctype.camt_import.bankkonto_zuordnung.verfuegbar',
        args: {camt_import: name},
        callback: function(r) {
            if (frm.__camt_bankkonto_request !== request || frm.doc.name !== name ||
                frm.is_dirty() || frm.doc.status === 'In Verarbeitung') return;
            if (r.message) {
                frappe.mvd.camt_aktions_button(frm, 'bankkonto', __('Bankkonto zuordnen'),
                    () => frappe.mvd.camt_bankkonto_zuordnen(frm));
            }
        }
    });
};

frappe.mvd.camt_bankkonto_zuordnen = function(frm) {
    if (frm.is_dirty()) {
        frappe.msgprint('Bitte speichern Sie den CAMT-Import zuerst.');
        return;
    }
    const method = 'mvd.mvd.doctype.camt_import.bankkonto_zuordnung.';
    const esc = value => frappe.utils.escape_html(String(value == null ? '' : value));
    frappe.call({method: method + 'kandidaten', args: {camt_import: frm.doc.name}, callback: function(r) {
        const candidates = r.message || [];
        if (!candidates.length) {
            frappe.msgprint('Keine offenen Zahlungen mit ausschliesslicher Bankkonto-Abweichung gefunden.');
            return;
        }
        let dialog;
        const selected = () => candidates.find(row => row.payment_entry === dialog.get_value('payment_entry'));
        function show_context() {
            const row = selected();
            if (!row) return;
            dialog.set_df_property('context', 'options', '<p>Rechnung: <a href="/desk#Form/' +
                encodeURIComponent(row.reference_doctype) + '/' + encodeURIComponent(row.reference_name) + '">' +
                esc(row.reference_name) + '</a><br>Betrag: ' + esc(row.amount.toFixed(2)) + ' ' + esc(row.currency) +
                '<br>Firma / Sektion: ' + esc(row.company) + ' / ' + esc(row.sektion) + '</p>' +
                '<p>Bankkonto aus CAMT-Import: <b>' + esc(row.import_bankkonto) + '</b><br>' +
                'Bankkonto aus Rechnung: <b>' + esc(row.rechnungs_bankkonto || 'nicht hinterlegt') + '</b></p>' +
                (!row.rechnungskonto_verfuegbar ? '<p>Das Rechnungskonto ist nicht verfügbar. Es muss ein aktives, zugängliches Bankkonto derselben Firma und Währung sein.</p>' : '') +
                '<p>Die Auswahl bestimmt das Eingangskonto der Zahlung. Bei Auswahl des Rechnungskontos wird der Eingang dort gebucht. ' +
                'Es wird kein Bankübertrag erfasst. Die Rechnung bleibt unverändert.</p>');
            dialog.set_df_property('bankkonto_quelle', 'options', row.rechnungskonto_verfuegbar ?
                '\nCAMT-Import\nRechnung' : '\nCAMT-Import');
            dialog.set_value('bankkonto_quelle', '');
        }
        dialog = new frappe.ui.Dialog({title: 'Bankkonto für Zahlung wählen', no_submit_on_enter: true,
            fields: [
                {fieldname: 'payment_entry', fieldtype: 'Select', label: 'Blockierte Zahlung', reqd: 1,
                    options: candidates.map(row => row.payment_entry).join('\n'), change: function() { if (dialog) show_context(); }},
                {fieldname: 'context', fieldtype: 'HTML'},
                {fieldname: 'bankkonto_quelle', fieldtype: 'Select', label: 'Bankkonto verwenden aus', reqd: 1,
                    options: '\nCAMT-Import\nRechnung'}
            ],
            primary_action_label: 'Auswahl übernehmen',
            primary_action: function(values) {
                const row = selected();
                dialog.get_primary_btn().prop('disabled', true);
                frappe.call({method: method + 'zuordnen', args: {camt_import: frm.doc.name,
                    payment_entry: row.payment_entry, bankkonto_quelle: values.bankkonto_quelle, token: row.token},
                    freeze: true, freeze_message: 'Ordne Zahlung zu...',
                    error: () => dialog.get_primary_btn().prop('disabled', false),
                    callback: function(response) {
                        dialog.hide();
                        frm.reload_doc();
                        const result = response.message;
                        frappe.msgprint('Zahlung ' + esc(result.payment_entry) + ' zugeordnet. Eingangskonto: ' +
                            esc(result.bankkonto) + '.<br>' + (result.camt_status === 'Rechnungs Match' ?
                                'Sie kann nun über «Zahlungen verbuchen» gebucht werden.' :
                                'Die Zahlung ist als «Überbezahlt» markiert. Bitte prüfen Sie die Zuordnung vor dem Verbuchen.'));
                    }});
            }});
        dialog.set_value('payment_entry', candidates[0].payment_entry);
        show_context();
        dialog.show();
    }});
};
