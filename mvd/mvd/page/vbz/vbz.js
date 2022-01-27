frappe.pages['vbz'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Verarbeitungszentrale',
        single_column: true
    });
    frappe.vbz.add_views(page);
    
}
frappe.pages['vbz'].refresh= function(wrapper){
    frappe.vbz.show_view('overview');
    if (!frappe.vbz.click_handlers_added) {
        frappe.vbz.add_click_handlers();
    }
} 

frappe.vbz = {
    add_views: function(page) {
        page.add_view('overview', frappe.render_template("overview", {}))
        page.add_view('validierung', frappe.render_template("validierung", {}))
        page.add_view('kuendigung', frappe.render_template("kuendigung", {}))
        
    },
    show_view: function(view) {
        cur_page.page.page.set_view(view);
    },
    add_click_handlers: function() {
        frappe.vbz.click_handlers_added = true;
        $(".fa-chevron-left.pull-left").click(function(){
            frappe.vbz.show_view('overview');
        });
        $("#mitglieder").click(function(){
            frappe.route_options = {"sektion_id": frappe.vbz.get_default_sektion()};
            frappe.set_route("List", "MV Mitgliedschaft");
        });
        $("#suchmaske").click(function(){
            frappe.set_route("mvd-suchmaske");
        });
        $("#arbeitsbacklog").click(function(){
            frappe.route_options = {"status": "Open"};
            frappe.set_route("List", "Arbeits Backlog");
        });
        $("#validieren").click(function(){
            frappe.vbz.show_view('validierung');
        });
        $("#kuendigung").click(function(){
            frappe.vbz.show_view('kuendigung');
        });
        $("#validierung_allgemein").click(function(){
            frappe.route_options = {"validierung_notwendig": 1}
            frappe.set_route("List", "MV Mitgliedschaft");
        });
        $("#kuendigung_mitglieder").click(function(){
            frappe.route_options = {"kuendigung_verarbeiten": 1}
            frappe.set_route("List", "MV Mitgliedschaft");
        });
        $("#massen_kuendigung").click(function(){
            frappe.msgprint("Dies Massenverarbeitung wird durchgeführt");
        });
        $("#neuanlage").click(function(){
            frappe.set_route("mvd-suchmaske");
        });
    },
    get_default_sektion: function() {
        var default_sektion = '';
        if (frappe.defaults.get_user_permissions()["Sektion"]) {
            var sektionen = frappe.defaults.get_user_permissions()["Sektion"];
            sektionen.forEach(function(entry) {
                if (entry.is_default == 1) {
                    default_sektion = entry.doc;
                }
            });
        }
        return default_sektion
    },
    click_handlers_added: false
}
