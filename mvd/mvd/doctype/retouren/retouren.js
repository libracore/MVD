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

    ausgabe: function(frm) {
        if (frm.doc.ausgabe) {
            console.log('its set')
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'MW',
                    filters: {
                        ausgabe_kurz: frm.doc.ausgabe
                    },
                    fields: ['laufnummer'],
                    limit_page_length: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frm.set_value('retoure_mw_sequence_number', r.message[0].laufnummer);
                    } else {
                        frm.set_value('retoure_mw_sequence_number', '');
                        frappe.msgprint(__('Kein passender MW-Datensatz gefunden.'));
                    }
                }
            });
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
