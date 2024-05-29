frappe.pages['individueller-arbeitsplan'].on_page_load = function(wrapper) {
    var me = this;
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Individueller Arbeitsplan',
        single_column: true
    });

    page.main.html(frappe.render_template("individueller_arbeitsplan", {}));
    me.mvd_fields = {}

    me.mvd_fields.berater_in_field = frappe.mvd_individueller_arbeitsplan_client.create_berater_in_field(page)
    me.mvd_fields.berater_in_field.refresh();

    me.mvd_fields.von_field = frappe.mvd_individueller_arbeitsplan_client.create_von_field(page)
    me.mvd_fields.von_field.refresh();

    me.mvd_fields.bis_field = frappe.mvd_individueller_arbeitsplan_client.create_bis_field(page)
    me.mvd_fields.bis_field.refresh();

    me.mvd_fields.pdf_btn = frappe.mvd_individueller_arbeitsplan_client.create_pdf_btn(page)
    me.mvd_fields.pdf_btn.refresh();

    me.mvd_fields.word_btn = frappe.mvd_individueller_arbeitsplan_client.create_word_btn(page)
    me.mvd_fields.word_btn.refresh();

    me.mvd_fields.pdf_vorschau = frappe.mvd_individueller_arbeitsplan_client.create_vorschau(page)
    me.mvd_fields.pdf_vorschau.refresh();
}

frappe.mvd_individueller_arbeitsplan_client = {
    create_berater_in_field: function(page) {
        var berater_in_field = frappe.ui.form.make_control({
            parent: page.main.find(".berater_in_und_pdf"),
            df: {
                fieldtype: "Link",
                fieldname: "berater_in",
                options: "Termin Kontaktperson",
                placeholder: "Bitte Berater*in auswählen",
                change: function(){
                    frappe.mvd_individueller_arbeitsplan_client.show_vorschau(page);
                }
            },
            only_input: true
        });
        return berater_in_field
    },
    create_von_field: function(page) {
        var von_field = frappe.ui.form.make_control({
            parent: page.main.find(".datum"),
            df: {
                fieldtype: "Date",
                fieldname: "von_field",
                options: "Von Datum",
                placeholder: "Bitte Von-Datum auswählen",
                change: function(){
                    frappe.mvd_individueller_arbeitsplan_client.show_vorschau(page);
                }
            },
            only_input: true
        });
        return von_field
    },
    create_bis_field: function(page) {
        var bis_field = frappe.ui.form.make_control({
            parent: page.main.find(".datum"),
            df: {
                fieldtype: "Date",
                fieldname: "bis_field",
                options: "Bis Datum",
                placeholder: "Bitte Bis-Datum auswählen",
                change: function(){
                    frappe.mvd_individueller_arbeitsplan_client.show_vorschau(page);
                }
            },
            only_input: true
        });
        return bis_field
    },
    create_pdf_btn: function(page) {
        var pdf_btn = frappe.ui.form.make_control({
            parent: page.main.find(".berater_in_und_pdf"),
            df: {
                fieldtype: "Button",
                fieldname: "pdf_btn",
                label: "Erstelle PDF",
                hidden: 0,
                click: function(){
                    var berater_in = cur_page.page.mvd_fields.berater_in_field.get_value();
                    var von = cur_page.page.mvd_fields.von_field.get_value()||'';
                    var bis = cur_page.page.mvd_fields.bis_field.get_value()||'';
                    if (berater_in) {
                        var url = "/api/method/mvd.mvd.doctype.arbeitsplan_beratung.arbeitsplan_beratung.get_arbeitsplan_pdf"
                                + "?berater_in=" + encodeURIComponent(berater_in) + "&von=" + encodeURIComponent(von) + "&bis=" + encodeURIComponent(bis);
                        var w = window.open(
                            frappe.urllib.get_full_url(url)
                        );
                        if (!w) {
                            frappe.msgprint(__("Please enable pop-ups")); return;
                        }
                    } else {
                        frappe.msgprint("Bitte zuerst ein*e Berater*in auswählen");
                    }
                }
            },
            only_input: true,
        });
        return pdf_btn
    },
    create_word_btn: function(page) {
        var word_btn = frappe.ui.form.make_control({
            parent: page.main.find(".berater_in_und_pdf"),
            df: {
                fieldtype: "Button",
                fieldname: "word_btn",
                label: "Erstelle Word-File",
                hidden: 0,
                click: function(){
                    var berater_in = cur_page.page.mvd_fields.berater_in_field.get_value();
                    var von = cur_page.page.mvd_fields.von_field.get_value()||'';
                    var bis = cur_page.page.mvd_fields.bis_field.get_value()||'';
                    if (berater_in) {
                        var url = "/api/method/mvd.mvd.doctype.arbeitsplan_beratung.arbeitsplan_beratung.get_arbeitsplan_word"
                                + "?berater_in=" + encodeURIComponent(berater_in) + "&von=" + encodeURIComponent(von) + "&bis=" + encodeURIComponent(bis);
                        var w = window.open(
                            frappe.urllib.get_full_url(url)
                        );
                        if (!w) {
                            frappe.msgprint(__("Please enable pop-ups")); return;
                        }
                    } else {
                        frappe.msgprint("Bitte zuerst ein*e Berater*in auswählen");
                    }
                }
            },
            only_input: true,
        });
        return word_btn
    },
    create_vorschau: function(page) {
        var vorschau = frappe.ui.form.make_control({
            parent: page.main.find(".pdf-vorschau"),
            df: {
                fieldtype: "HTML",
                fieldname: "pdf-vorschau",
                options: ''
            },
            only_input: true,
        });
        return vorschau
    },
    show_vorschau: function(page) {
        var berater_in = cur_page.page.mvd_fields.berater_in_field.get_value();
        var von = cur_page.page.mvd_fields.von_field.get_value()||'';
        var bis = cur_page.page.mvd_fields.bis_field.get_value()||'';
        if (berater_in) {
            frappe.call({
                method: "mvd.mvd.doctype.arbeitsplan_beratung.arbeitsplan_beratung.get_termin_uebersicht",
                args:{
                        'berater_in': berater_in,
                        'von': von,
                        'bis': bis
                },
                freeze: true,
                freeze_message: 'Lade Termine...',
                callback: function(r)
                {
                    if (r.message) {
                        cur_page.page.mvd_fields.pdf_vorschau.df.options = frappe.render_template("preview", {'berater_in': berater_in, 'termine': r.message});
                        cur_page.page.mvd_fields.pdf_vorschau.refresh();
                    } else {
                        cur_page.page.mvd_fields.pdf_vorschau.df.options = '<div>Keine Termine vorhanden</div>';
                        cur_page.page.mvd_fields.pdf_vorschau.refresh();
                    }
                }
            });
            
        } else {
            cur_page.page.mvd_fields.pdf_vorschau.df.options = '<div></div>';
            cur_page.page.mvd_fields.pdf_vorschau.refresh();
        }
    }
}