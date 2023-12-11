frappe.pages['vbz_beratung_termine'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Verarbeitungszentrale',
		single_column: true
	});
    frappe.vbz_beratung_termine.add_views(page);
    localStorage['firstLoad'] = true;
}
frappe.pages['vbz_beratung_termine'].refresh= function(wrapper){
    frappe.vbz_beratung_termine.show_view('vbz_beratung_termine');
    frappe.dom.unfreeze();
} 

frappe.vbz_beratung_termine = {
    add_views: function(page) {
        frappe.call({
            'method': "mvd.mvd.page.vbz_beratung_termine.vbz_beratung_termine.get_open_data",
            'args': {},
            'freeze': true,
            'freeze_message': 'Lade Verarbeitungszentrale...',
            'async': false,
            'callback': function(r)
            {
                if (r.message) {
                    page.add_view('vbz_beratung_termine', frappe.render_template("vbz_beratung_termine", eval(r.message)))
                    frappe.vbz_beratung_termine.add_click_handlers();
                    localStorage['firstLoad'] = true;
                }
            }
        });
    },
    show_view: function(view) {
        cur_page.page.page.set_view(view);
    },
    remove_click_handlers: function() {

    },
    add_click_handlers: function() {
        $(".termin-tr").each(function() {
            if ($(this).attr('data-beratung')) {
                $(this).click(function(){
                    frappe.set_route("Form", "Beratung", $(this).attr('data-beratung'));
                })
            }
        });
        frappe.dom.unfreeze();
    },
    open_beratung: function(beratung) {
        frappe.set_route("Form", "Beratung", beratung.beratung);
    }
}