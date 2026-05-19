// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mandat', {
	email_1: function(frm) {
		open_mandat_email(frm, 'mandat_email_1');
	},
	email_2: function(frm) {
		open_mandat_email(frm, 'mandat_email_2');
	},
	email_3: function(frm) {
		open_mandat_email(frm, 'mandat_email_3');
	}
});

function open_mandat_email(frm, template_prefix) {
	if (!frm.doc.kontaktperson) {
		frappe.msgprint(__("Bitte zuerst eine*n Berater*in auswählen."));
		return;
	}

	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Termin Kontaktperson',
			name: frm.doc.kontaktperson
		},
		callback: function(r) {
			if (r.message && r.message.user && r.message.user.length > 0) {
				var recipient = r.message.user[0].user;
				var email_template = template_prefix + '-' + frm.doc.sektion_id;

				new frappe.mvd.MailComposer({
					doc: frm.doc,
					frm: frm,
					subject: __('Mandat') + ': ' + frm.docname,
					recipients: recipient,
					attach_document_print: false,
					txt: '',
					email_template: email_template
				});
			} else {
				frappe.msgprint(__("Keine/r Benutzer*in für die/den ausgewählte/n Berater*in gefunden."));
			}
		}
	});
}
