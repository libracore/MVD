frappe.pages['vbz-beratung'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Verarbeitungszentrale',
        single_column: true
    });
    frappe.vbz_beratung.add_views(page);
}
frappe.pages['vbz-beratung'].refresh= function(wrapper){
    frappe.vbz_beratung.show_view('vbz_beratung');
    frappe.dom.unfreeze();
} 

frappe.vbz_beratung = {
    add_views: function(page) {
        frappe.call({
            'method': "mvd.mvd.page.vbz_beratung.vbz_beratung.get_open_data",
            'args': {},
            'freeze': true,
            'freeze_message': 'Lade Verarbeitungszentrale...',
            'async': false,
            'callback': function(r)
            {
                if (r.message) {
                    page.add_view('vbz_beratung', frappe.render_template("vbz_beratung", eval(r.message.beratung)))
                    frappe.vbz_beratung.add_click_handlers(eval(r.message));
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
        //~ frappe.vbz_beratung.remove_click_handlers();
        
        $("#eingang").click(function(){
            frappe.route_options = {"status": 'Eingang'}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#eingang_ohne_zuordnung").click(function(){
            frappe.route_options = {"status": 'Eingang', "mv_mitgliedschaft": ['is', 'not set']}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#offen").click(function(){
            frappe.route_options = {"status": 'Open'}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#offen_dringend").click(function(){
            frappe.route_options = {"status": 'Open', 'beratung_prio': 'Hoch'}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#offen_zuweisung").click(function(){
            frappe.route_options = {"status": 'Open', 'zuweisung': 0}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#rueckfragen").click(function(){
            frappe.route_options = {"status": ['like', 'Rückfrage%']}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#termine").click(function(){
            frappe.route_options = {"hat_termine": 1, 'status': ['!=', 'Closed']}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#zugewiesene_beratungen").click(function(){
            frappe.route_options = {"_assign": ['like', '%' + frappe.session.user + '%']}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#zugewiesene_termine").click(function(){
            frappe.route_options = {"_assign": frappe.session.user}
            frappe.set_route("query-report/Beratungs Termine");
            
        });
        $("#rechtsberaterinnen").click(function(){
            frappe.set_route("List", "Termin Kontaktperson", "List");
        });
        $("#beratungskategorien").click(function(){
            frappe.set_route("List", "Beratungskategorie", "List");
        });
        $("#statistik").click(function(){
            frappe.set_route(["query-report", "Beratungsstatistik"]);
        });
        $("#hk_u_mz").click(function(){
            frappe.set_route(["#List/Beratung/Report/MVBE Admin: HK_u_MZ"]);
        });
        
        frappe.dom.unfreeze();
    }
}
