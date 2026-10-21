// Copyright (c) 2025, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mitglied RG Jahreslauf', {
    refresh: function(frm) {
        if (!frm.is_new() && !frm.is_dirty() && frappe.user.has_role('System Manager') &&
            ['PDFs erstellt', 'Test E-Mails versendet', 'E-Mails versendet',
             'Abgeschlossen', 'Abgebrochen', 'Fehlgeschlagen'].includes(frm.doc.status)) {
            frm.add_custom_button(frm.doc.pdf_recreation_documents ? 'PDF-Neuerstellung fortsetzen' : 'PDFs neu erstellen', function() {
                const recreate_pdfs = function(pdf_type = 'Alle PDFs') {
                    frm.call('recreate_pdfs', {preview: 1, pdf_type: pdf_type}).then(r => {
                        const summary = r.message;
                        if (!summary.documents && !summary.resume) {
                            frappe.msgprint('Für diese Auswahl wurden keine Jahreslauf-PDFs an gebuchten Rechnungen gefunden.');
                            return;
                        }
                        const action = summary.resume ?
                            'Die PDF-Neuerstellung wird mit ' + summary.documents + ' verbleibenden Dokumenten fortgesetzt. Die gespeicherte Auswahl bleibt bestehen.' :
                            'Auswahl: ' + pdf_type + '<br>' + summary.files + ' bestehende Jahreslauf-PDFs von ' + summary.documents +
                            ' Dokumenten werden mit der aktuellen Druckvorlage ersetzt, einschliesslich bezahlter Rechnungen.' +
                            '<br><br>Bitte prüfen Sie zuerst die korrigierte Vorlage anhand einer Rechnung.';
                        frappe.confirm(
                            action +
                            '<br>Rechnungen und Versandmarkierungen bleiben unverändert. Es werden keine E-Mails versendet.' +
                            (summary.resume ? '<br><br>Neuerstellung jetzt fortsetzen?' : '<br><br>PDFs jetzt neu erstellen?'),
                            function() {
                                frm.call('recreate_pdfs', {preview: 0, pdf_type: pdf_type}).then(() => {
                                    frappe.msgprint('Die PDF-Neuerstellung wurde gestartet.');
                                    frm.reload_doc();
                                });
                            }
                        );
                    });
                };
                if (frm.doc.pdf_recreation_documents) {
                    recreate_pdfs();
                } else {
                    frappe.prompt([
                        {fieldname: 'pdf_type', fieldtype: 'Select', label: 'PDFs neu erstellen für',
                         options: 'Alle PDFs\nFakultative Rechnung\nMitgliedschaftsrechnung', default: 'Alle PDFs', reqd: 1}
                    ], function(values) {
                        recreate_pdfs(values.pdf_type);
                    }, 'Auswahl der PDFs', 'Weiter');
                }
            });
        }
    },
    start_rg: function(frm) {
        frm.call('check_start_rg', {}).then(r => {
            if (r.message > 0) {
                frappe.confirm(
                    'Es wurden noch nicht alle Sektions Selektionen verbucht, wollen Sie den RG Erstellungsprozess trotzdem starten?',
                    function(){
                        // on yes
                        frm.call('start_rg', {}).then(r => {
                            frappe.msgprint("Der RG Erstellungsprozess wurde gestartet")
                            cur_frm.reload_doc();
                        });
                    },
                    function(){
                        // on no do nothing
                    }
                )
            } else {
                frm.call('start_rg', {}).then(r => {
                    frappe.msgprint("Der RG Erstellungsprozess wurde gestartet")
                    cur_frm.reload_doc();
                });
            }
        });
    },
    stop_rg: function(frm) {
        frm.call('stop_rg', {}).then(r => {
            frappe.msgprint("Der RG Erstellungsprozess wurde abgebrochen")
            cur_frm.reload_doc();
        });
    },
    create_pdf: function(frm) {
        frm.call('create_pdf', {}).then(r => {
            frappe.msgprint("Der PDF Erstellungsprozess wurde gestartet")
            cur_frm.reload_doc();
        });
    },
    stop_pdf: function(frm) {
        if (frm.doc.status === 'Erstelle PDFs neu') {
            frappe.call({
                method: 'mvd.mvd.doctype.mitglied_rg_jahreslauf.mitglied_rg_jahreslauf.stop_pdf_recreation',
                args: {mrj: frm.doc.name},
                callback: function() {
                    frappe.msgprint('Die PDF-Neuerstellung wird nach dem aktuellen Beleg gestoppt. Sie kann später fortgesetzt werden.');
                    frm.reload_doc();
                }
            });
            return;
        }
        frm.call('stop_pdf', {}).then(r => {
            frappe.msgprint("Der PDF Erstellungsprozess wurde abgebrochen")
            cur_frm.reload_doc();
        });
    },
    send_test_mails: function(frm) {
        frm.call('get_mail_accounts', {}).then(mail_accounts => {
            const mail_accs = mail_accounts.message
            if ((mail_accs)&&(mail_accs.length > 0)) {
                frappe.prompt([
                    {'fieldname': 'mail_account', 'fieldtype': 'Data', 'label': 'Test E-Mail Empfänger', 'reqd': 1},
                    {'fieldname': 'sender_mail_account', 'fieldtype': 'Select', 'label': 'Absender E-Mail Account', 'reqd': 1, 'options': mail_accs, 'description': "<b>Achtung</b><br>Als Reply-To Adresse wird bei der oben ausgewählten Absenderadresse alles vor dem @ durch das Sektionskürzel ersetzt."},
                    {'fieldname': 'qty', 'fieldtype': 'Int', 'label': 'Anz. Test E-Mails', 'default': 1, 'reqd': 1},
                    {'fieldname': 'einzelmitglied', 'fieldtype': 'Data', 'label': 'Mitglied ID (optional für Einzelversand)', 'default': 0, 'description': "Zwingend folgenden Syntax einhalten:<br>123456,654321,...'"}
                ],
                function(values){
                    frm.call('send_test_mails', {sender_account: values.sender_mail_account, mail_account: values.mail_account, qty: values.qty, test_mail_mitglied: values.einzelmitglied}).then(r => {
                        frappe.msgprint("Der Test E-Mail Versand wurde gestartet")
                        cur_frm.reload_doc();
                    });
                },
                'Test E-Mail Versand',
                'Versenden'
                );
            } else {
                frappe.msgprint("Sie verfügen über keinen aktiven, ausgehenden, E-Mail Account");
            }
        });
    },
    send_mails: function(frm) {
        frappe.confirm(
            'Wollen Sie als Absender die Sektionsspezifischen E-Mail Accounts verwenden?',
            function(){
                // on yes
                frm.call('send_mails', {mail_from_sektion: 1}).then(r => {
                    frappe.msgprint("Der E-Mail Versand wurde gestartet")
                    cur_frm.reload_doc();
                });
            },
            function(){
                // on no
                frm.call('get_mail_accounts', {}).then(mail_accounts => {
                    const mail_accs = mail_accounts.message
                    if ((mail_accs)&&(mail_accs.length > 0)) {
                        frappe.prompt([
                            {'fieldname': 'mail_account', 'fieldtype': 'Select', 'label': 'E-Mail Account', 'reqd': 1, 'options': mail_accs, 'description': "<b>Achtung</b><br>Als Reply-To Adresse wird bei der oben ausgewählten Absenderadresse alles vor dem @ durch das Sektionskürzel ersetzt."}
                        ],
                        function(values){
                            frm.call('send_mails', {mail_from_sektion: 0, mail_account: values.mail_account}).then(r => {
                                frappe.msgprint("Der E-Mail Versand wurde gestartet")
                                cur_frm.reload_doc();
                            });
                        },
                        'Auswahl E-Mail Account',
                        'Versenden'
                        );
                    } else {
                        frappe.msgprint("Sie verfügen über keinen aktiven, ausgehenden, E-Mail Account");
                    }
                });
            }
        );
    },
    stop_mail: function(frm) {
        frm.call('stop_mail', {}).then(r => {
            frappe.msgprint("Der E-Mail Versand wurde abgebrochen")
            cur_frm.reload_doc();
        });
    },
    create_csv: function(frm) {
        frm.call('create_csv', {}).then(r => {
            frappe.msgprint("Das CSV wird erstellt...")
            cur_frm.reload_doc();
        });
    }
});
