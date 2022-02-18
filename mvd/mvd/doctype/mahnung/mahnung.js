// Copyright (c) 2018-2021, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Reminder', {
    //~ refresh: function(frm) {
        //~ if (!frm.doc.company) {
            //~ cur_frm.set_value("company", frappe.defaults.get_user_default("company"));
        //~ }
    //~ },
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
