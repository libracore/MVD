frappe.pages['vbz-validieren'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Verarbeitungszentrale',
        single_column: true
    });
    frappe.vbz_validieren.add_views(page);
}
frappe.pages['vbz-validieren'].refresh= function(wrapper){
    frappe.vbz_validieren.show_view('vbz_validierung');
    frappe.dom.unfreeze();
} 

frappe.vbz_validieren = {
    add_views: function(page) {
        frappe.call({
            'method': "mvd.mvd.page.vbz_validieren.vbz_validieren.get_open_data",
            'args': {},
            'freeze': true,
            'freeze_message': 'Lade Verarbeitungszentrale...',
            'async': false,
            'callback': function(r)
            {
                if (r.message) {
                    page.add_view('vbz_validierung', frappe.render_template("vbz_validierung", eval(r.message.validierung)))
                    frappe.vbz_validieren.add_click_handlers(eval(r.message));
                }
            }
        });
    },
    show_view: function(view) {
        cur_page.page.page.set_view(view);
    },
    remove_click_handlers: function() {
        //
    },
    add_click_handlers: function(open_datas) {
        //~ frappe.vbz_validieren.remove_click_handlers();
        
        // validierungen
        $("#online_beitritte").click(function(){
            frappe.route_options = {"status_c": 'Online-Beitritt', "validierung_notwendig": 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#online_anmeldungen").click(function(){
            frappe.route_options = {"status_c": 'Online-Anmeldung', "validierung_notwendig": 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#online_kuendigungen").click(function(){
            frappe.route_options = {"status_c": 'Online-Kündigung', "validierung_notwendig": 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#zuzuege").click(function(){
            frappe.route_options = {"status_c": 'Zuzug', "validierung_notwendig": 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#online_mutationen").click(function(){
            frappe.route_options = {"status_c": 'Online-Mutation', "validierung_notwendig": 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#geschenk_mitgliedschaften").click(function(){
            frappe.msgprint("Wird noch umgesetzt");
        });
        $("#autom_adressaenderungen").click(function(){
            frappe.msgprint("Wird noch umgesetzt");
        });
        
        frappe.dom.unfreeze();
    }
}
