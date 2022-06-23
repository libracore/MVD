// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Retouren MW', {
    refresh: function(frm) {
        cur_frm.page.add_action_icon(__("fa fa-envelope-o"), function() {
            send_mail(frm);
        });
    }
});

function send_mail(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.retouren_mw.retouren_mw.get_mail_data",
        args:{
                'mitgliedschaft': cur_frm.doc.mv_mitgliedschaft,
                'retoure': cur_frm.doc.name,
                'grund_bezeichnung': cur_frm.doc.grund_bezeichnung || 'Keine Angaben'
        },
        callback: function(r)
        {
            if (r.message) {
                var mail_data = r.message;
                var email = mail_data.email;
                var cc = mail_data.cc;
                var subject = mail_data.subject;
                var email_body = mail_data.email_body;
                document.location = "mailto:"+email+"?cc="+cc+"&subject="+subject+"&body="+email_body;
            } else {
                frappe.msgprint("Das Mitglied besitzt keine E-Mail Adresse");
            }
        }
    });
};
