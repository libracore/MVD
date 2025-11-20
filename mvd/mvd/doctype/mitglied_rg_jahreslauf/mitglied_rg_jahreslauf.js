// Copyright (c) 2025, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mitglied RG Jahreslauf', {
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
                    {'fieldname': 'einzelmitglied', 'fieldtype': 'Data', 'label': 'Mitglied ID (optional für Einzelversand)', 'default': 0, 'description': "Zwingend folgenden Syntax einhalten:<br>'123456', '654321', '...'"}
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
