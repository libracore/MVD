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

    me.mvd_fields.pdf_btn = frappe.mvd_individueller_arbeitsplan_client.create_pdf_btn(page)
    me.mvd_fields.pdf_btn.refresh();

    me.mvd_fields.pdf_vorschau = frappe.mvd_individueller_arbeitsplan_client.create_vorschau(page)
    me.mvd_fields.pdf_vorschau.refresh();
}

frappe.mvd_individueller_arbeitsplan_client = {
    create_berater_in_field: function(page) {
        var berater_in_field = frappe.ui.form.make_control({
            parent: page.main.find(".berater_in"),
            df: {
                fieldtype: "Link",
                fieldname: "berater_in",
                options: "Termin Kontaktperson",
                placeholder: "Bitte Berater*in auswählen",
                change: function(){
                    var berater_in = cur_page.page.mvd_fields.berater_in_field.get_value();
                    if (berater_in) {
                        frappe.call({
                            method: "mvd.mvd.doctype.arbeitsplan_beratung.arbeitsplan_beratung.get_termin_uebersicht",
                            args:{
                                    'berater_in': berater_in
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
            },
            only_input: true
        });
        return berater_in_field
    },
    create_pdf_btn: function(page) {
        var pdf_btn = frappe.ui.form.make_control({
            parent: page.main.find(".pdf-erzeugung"),
            df: {
                fieldtype: "Button",
                fieldname: "pdf_btn",
                label: "Erstelle PDF",
                hidden: 0,
                click: function(){
                    var berater_in = cur_page.page.mvd_fields.berater_in_field.get_value();
                    if (berater_in) {
                        var url = "/api/method/mvd.mvd.doctype.arbeitsplan_beratung.arbeitsplan_beratung.get_arbeitsplan_pdf"
                                + "?berater_in=" + encodeURIComponent(berater_in);
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
    }
}