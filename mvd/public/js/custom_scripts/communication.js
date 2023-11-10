// Copyright (c) 2021-2022, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Communication', {
    refresh: function(frm) {
        if(frm.doc.communication_type=="Communication"
            && frm.doc.communication_medium == "Email"
            && frm.doc.sent_or_received == "Received") {
                
                frm.remove_custom_button("Reply");
                frm.add_custom_button(__("Reply"), function() {
                    new frappe.mvd.MailComposer({
                        doc: cur_frm.doc,
                        frm: cur_frm,
                        subject: __("Re: {0}", [frm.doc.subject]),
                        recipients: frm.doc.sender,
                        attach_document_print: false,
                        real_name: cur_frm.doc.real_name || cur_frm.doc.contact_display || cur_frm.doc.contact_name
                    });
                });
                
                $("[data-label='" + __("Reply All") + "']").remove();
                $("[data-label='" + __("Allen%20antworten") + "']").remove();
                frm.add_custom_button(__("Reply All"), function() {
                    new frappe.mvd.MailComposer({
                        doc: cur_frm.doc,
                        frm: cur_frm,
                        subject: __("Re: {0}", [frm.doc.subject]),
                        recipients: frm.doc.sender,
                        attach_document_print: false,
                        real_name: cur_frm.doc.real_name || cur_frm.doc.contact_display || cur_frm.doc.contact_name
                    });
                }, "Actions");
                
                $("[data-label='" + __("Forward") + "']").remove();
                frm.add_custom_button(__("Forward"), function() {
                    new frappe.mvd.MailComposer({
                        doc: cur_frm.doc,
                        frm: cur_frm,
                        subject: __("Fw: {0}", [frm.doc.subject]),
                        recipients: frm.doc.sender,
                        attach_document_print: false,
                        real_name: cur_frm.doc.real_name || cur_frm.doc.contact_display || cur_frm.doc.contact_name
                    });
                }, "Actions");
                
                // overwrite E-Mail BTN
                override_default_email_dialog(frm);
        }
    }
});

function override_default_email_dialog(frm) {
    // overwrite E-Mail BTN
    $("[data-label='Email']").parent().off("click");
    $("[data-label='Email']").parent().click(function(){frappe.mvd.new_mail(cur_frm);});
    $("[data-label='E-Mail']").parent().off("click");
    $("[data-label='E-Mail']").parent().click(function(){frappe.mvd.new_mail(cur_frm);});
    $(".btn.btn-default.btn-reply-email.btn-xs").off("click");
    $(".btn.btn-default.btn-reply-email.btn-xs").click(function(){frappe.mvd.new_mail(cur_frm);});
    frappe.ui.keys.off('ctrl+e', cur_frm.page);
}
