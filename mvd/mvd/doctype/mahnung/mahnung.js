// Copyright (c) 2018-2021, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mahnung', {
    refresh: function(frm) {
        frm.add_custom_button(__("Differenz als Kulanz ausgleichen"), function() {
            if (frappe.user.has_role("MV Sektionsmitarbeiter*in RO")) {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            } else {
                kulanz_ausgleich(frm);
            }
        });
    },
    reminder_charge: function(frm) {
        update_total(frm);
    },
    total_before_charge: function(frm) {
        update_total(frm);
    }
});

//~ vorbereitung für auto add/remove mitgliedschaft links
//~ frappe.ui.form.on('Payment Reminder Invoice', {
    //~ sales_invoices_add: function(frm) {
      //~ console.log(frm.doc.sales_invoices);
      //~ console.log(frm.doc.mitgliedschaften);
   //~ },
   //~ sales_invoices_remove: function(frm) {
      //~ console.log(frm.doc.sales_invoices);
      //~ console.log(frm.doc.mitgliedschaften);
      //~ frm.doc.mitgliedschaften.forEach(function(entry){
         //~ if (entry.mv_mitgliedschaft 
      //~ });
   //~ }
//~ });

function update_total(frm) {
    cur_frm.set_value("total_with_charge", ((frm.doc.total_before_charge || 0) + (frm.doc.reminder_charge || 0)));
}


function kulanz_ausgleich(frm) {
    var sinvs = [];
    cur_frm.doc.sales_invoices.forEach(function(entry){
        sinvs.push(entry.sales_invoice);
    });
    frappe.prompt([
        {'fieldname': 'sinv', 'fieldtype': 'Link', 'label': 'Rechnung zum Ausgleichen', 'reqd': 0, 'options': 'Sales Invoice',
            'get_query': function() {
                return { 'filters': { 'name': ['in', eval(sinvs)] } };
            }
        }
    ],
    function(values){
        var mahnung = cur_frm.doc.name;
        var sinv = values.sinv;
        var amount = 0;
        var outstanding_amount = 0;
        var due_date = '';
        cur_frm.doc.sales_invoices.forEach(function(entry){
            if (entry.sales_invoice == values.sinv){
                amount = entry.amount;
                outstanding_amount = entry.outstanding_amount;
                due_date = entry.due_date;
            }
        });
        frappe.call({
            method: "mvd.mvd.doctype.mahnung.mahnung.kulanz_ausgleich",
            args:{
                    'mahnung': mahnung,
                    'sinv': sinv,
                    'amount': amount,
                    'outstanding_amount': outstanding_amount,
                    'due_date': due_date
            },
            freeze: true,
            freeze_message: 'Gleiche Rechnung mittels Kulanz aus...',
            callback: function(r)
            {
                var tbl = frm.doc.sales_invoices || [];
                var i = tbl.length;
                while (i--)
                {
                    if (cur_frm.get_field("sales_invoices").grid.grid_rows[i].doc.sales_invoice == sinv) {
                        cur_frm.get_field("sales_invoices").grid.grid_rows[i].remove();
                    }
                }
                cur_frm.refresh();
                cur_frm.save();
            }
        });
    },
    'Auswahl Rechnung zum Ausgleich',
    'Ausgleichen'
    )
}
