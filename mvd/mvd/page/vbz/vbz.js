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
} 

frappe.vbz = {
    add_views: function(page) {
        frappe.call({
            method: "mvd.mvd.page.vbz.vbz.get_open_data",
            args:{
                'sektion': frappe.vbz.get_default_sektion()
            },
            freeze: true,
            freeze_message: 'Lade Verarbeitungszentrale...',
            async: false,
            callback: function(r)
            {
                if (r.message) {
                    page.add_view('overview', frappe.render_template("overview", eval(r.message)))
                    page.add_view('validierung', frappe.render_template("validierung", eval(r.message.validierung)))
                    page.add_view('kuendigung', frappe.render_template("kuendigung", eval(r.message.kuendigung)))
                    page.add_view('kuendigung_massen_verarbeitung', frappe.render_template("kuendigung_massen_verarbeitung", eval(r.message.kuendigung)))
                    frappe.vbz.add_click_handlers();
                }
            }
        });
    },
    show_view: function(view) {
        cur_page.page.page.set_view(view);;
    },
    remove_click_handlers: function() {
        $(".back-to-overview").off("click");
        $(".back-to-kuendigung").off("click");
        $("#mitglieder").off("click");
        $("#suchmaske").off("click");
        $("#arbeitsbacklog").off("click");
        $("#validieren").off("click");
        $("#kuendigung").off("click");
        $("#massen_kuendigung").off("click");
        $("#validierung_allgemein").off("click");
        $("#kuendigung_mitglieder").off("click");
        $("#neuanlage").off("click");
    },
    add_click_handlers: function() {
        frappe.vbz.remove_click_handlers();
        $(".back-to-overview").click(function(){
            frappe.vbz.show_view('overview');
        });
        $(".back-to-kuendigung").click(function(){
            frappe.vbz.show_view('kuendigung');
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
        $("#massen_kuendigung").click(function(){
            frappe.vbz.show_view('kuendigung_massen_verarbeitung');
        });
        $("#validierung_allgemein").click(function(){
            frappe.route_options = {"validierung_notwendig": 1}
            frappe.set_route("List", "MV Mitgliedschaft");
        });
        $("#kuendigung_mitglieder").click(function(){
            frappe.route_options = {"kuendigung_verarbeiten": 1}
            frappe.set_route("List", "MV Mitgliedschaft");
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
    }
}
