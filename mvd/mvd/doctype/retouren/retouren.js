// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Retouren', {
    mv_mitgliedschaft: function(frm) {
        if (frm.doc.mv_mitgliedschaft) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Mitgliedschaft',
                    name: frm.doc.mv_mitgliedschaft
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('sektion_id', r.message.sektion_id);
                    }
                }
            });
        }
    },
    open_retoure_sendungsbild: function(frm) {
        let field = frm.fields_dict.retoure_sendungsbild;

        if (field && frm.doc.retoure_sendungsbild) {
            const url = frm.doc.retoure_sendungsbild;
            window.open(url, '_blank');
        } else if (field) {
            frappe.msgprint("Es ist kein Sendungsbild hinterlegt.")
        }
    },
    refresh: function(frm) {
        cur_frm.page.add_action_icon(__("fa fa-envelope-o"), function() {
            send_mail(frm);
        });
    },
    onload: function(frm) {
        // Load `ausgabe` options from MW
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'MW',
                fields: ['ausgabe_kurz'],
                limit_page_length: 1000,
                distinct: true
            },
            callback: function(r) {
                if (r.message) {
                    const options = r.message.map(row => row.ausgabe_kurz).filter(opt => !!opt);
                    frm.fields_dict.ausgabe.df.options = options.join('\n');
                    frm.refresh_field('ausgabe');
                }
            }
        });

        // Load `grund_bezeichnung` options from Retouren itself
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Retouren',
                fields: ['grund_bezeichnung'],
                limit_page_length: 1000,
                distinct: true
            },
            callback: function(r) {
                if (r.message) {
                    // Deduplicate values
                    const unique_options = [...new Set(r.message.map(row => row.grund_bezeichnung).filter(opt => !!opt))];
                    frm.fields_dict.grund_bezeichnung.df.options = unique_options.join('\n');
                    frm.refresh_field('grund_bezeichnung');
                }
            }
        });
    }
});

function send_mail(frm) {
    frappe.call({
        method: "mvd.mvd.doctype.retouren.retouren.get_mail_data",
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
