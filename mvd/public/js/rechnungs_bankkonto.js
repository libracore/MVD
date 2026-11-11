frappe.provide('frappe.mvd');

frappe.mvd.rechnungs_bankkonto_feld = function(options) {
    return Object.assign({
        fieldname: 'rechnungs_bankkonto',
        fieldtype: 'Link',
        label: 'Rechnungs-Bankkonto',
        options: 'Account',
        hidden: 1,
        reqd: 1
    }, options || {});
};

frappe.mvd.set_bankkonto_vorgabe = function(holder, args, reset, vorbelegen) {
    var field = holder.fields_dict.rechnungs_bankkonto;
    var get_value = function() {
        return holder.doc ? holder.doc.rechnungs_bankkonto : holder.get_value('rechnungs_bankkonto');
    };
    var previous_company = holder.rechnungs_bankkonto_company;
    holder.rechnungs_bankkonto_company = args.company || (reset === true ? null : previous_company) || null;

    field.get_query = function() {
        return {filters: {
            company: holder.rechnungs_bankkonto_company || '__kein_unternehmen__',
            account_type: 'Bank', is_group: 0, disabled: 0
        }};
    };

    if (reset === true) {
        holder.set_value('rechnungs_bankkonto', '');
    }

    var previous = get_value();
    holder.bankkonto_abfrage = (holder.bankkonto_abfrage || 0) + 1;
    var abfrage = holder.bankkonto_abfrage;

    if (!args.sektion && !args.company && !args.druckvorlage) return;

    frappe.call({
        method: 'mvd.mvd.utils.rechnungs_bankkonto.get_bankkonto_vorgabe',
        args: Object.assign({}, args, holder.doc ? {} : {mit_bankkonten: 1}),
        callback: function(r) {
            if (abfrage !== holder.bankkonto_abfrage || !r.message) return;

            holder.rechnungs_bankkonto_company = r.message.company;

            if (!holder.doc && Object.prototype.hasOwnProperty.call(r.message, 'einziges_bankkonto')) {
                var einziges_bankkonto = r.message.einziges_bankkonto;
                holder.set_df_property('rechnungs_bankkonto', 'hidden', einziges_bankkonto ? 1 : 0);
                if (einziges_bankkonto) {
                    holder.set_value('rechnungs_bankkonto', einziges_bankkonto);
                    return;
                }
            }

            if (reset === 'company' && previous_company !== r.message.company && get_value() === previous) {
                holder.set_value('rechnungs_bankkonto', r.message.rechnungs_bankkonto || '');
                return;
            }

            if (vorbelegen !== false && !previous && !get_value()) {
                holder.set_value('rechnungs_bankkonto', r.message.rechnungs_bankkonto || '');
            }
        }
    });
};

frappe.mvd.bankkonto_dialog = function(dialog, sektion, aus_druckvorlage) {
    frappe.mvd.set_bankkonto_vorgabe(dialog, {sektion: sektion});
    if (aus_druckvorlage) {
        dialog.fields_dict.druckvorlage.df.change = function() {
            frappe.mvd.set_bankkonto_vorgabe(dialog, {
                sektion: sektion, druckvorlage: dialog.get_value('druckvorlage')
            }, 'company');
        };
    }
};

[
    'Sales Invoice',
    'Fakultative Rechnung',
    'MRJ Sektions Selektion',
    'Rechnungs Jahresversand',
    'MV Jahresversand',
    'Spendenversand'
].forEach(function(doctype) {
    var update = function(frm, reset) {
        if (frm.doc.docstatus !== 0) return;

        var args = frm.doc.company ? {company: frm.doc.company} : {sektion: frm.doc.sektion_id};
        if (doctype === 'Spendenversand' && (!frm.doc.sektionsspezifisch || frm.doc.data_only)) {
            args = {};
            reset = true;
        }

        var is_invoice = doctype === 'Sales Invoice' || doctype === 'Fakultative Rechnung';

        frappe.mvd.set_bankkonto_vorgabe(frm, args, reset, reset || frm.is_new() || !is_invoice);
    };

    frappe.ui.form.on(doctype, {
        onload: function(frm) { update(frm, false); },
        company: function(frm) { update(frm, true); },
        sektion_id: function(frm) { update(frm, true); },
        sektionsspezifisch: function(frm) { update(frm, true); },
        data_only: function(frm) { update(frm, false); }
    });
});
