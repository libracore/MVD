frappe.pages['vbz-beratung'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Verarbeitungszentrale',
        single_column: true
    });
    frappe.vbz_beratung.add_views(page);
    localStorage['firstLoad'] = true;
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
                    localStorage['firstLoad'] = true;
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

        var sektion = frappe.boot.default_sektion || "MVBE";
        
        $("#s").click(function(){
            frappe.route_options = {"status": 'Eingang', "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s1").click(function(){
            frappe.route_options = {"status": 'Eingang', "mv_mitgliedschaft": ['is', 'not set'], "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s2").click(function(){
            frappe.route_options = {"status": 'Eingang', "beratungskategorie": ['in', ['202 - MZ-Erhöhung', '300 - Nebenkosten', '202 - Mietzinserhöhung', '203 - Mietzinssenkung']], "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s3").click(function(){
            frappe.route_options = {"status": 'Rückfrage: Termin vereinbaren', "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s4").click(function(){
            frappe.route_options = {"status": "Rückfragen", "kontaktperson": ['is', 'not set'], "ungelesen": 0, "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s5").click(function(){
            frappe.route_options = {"status": "Rückfragen", "kontaktperson": ['is', 'not set'], "ungelesen": 1, "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s6").click(function(){
            frappe.route_options = {"status": ["not in", ["Rückfragen", "Rückfrage: Termin vereinbaren", "Eingang", "Open", "Zusammengeführt"]], "ungelesen": 1, "kontaktperson": ['is', 'not set'], "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s7").click(function(){
            frappe.route_options = {"status": ['in', ['Open', 'In Arbeit']], "kontaktperson": ['is', 'not set'], "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s8").click(function(){
            frappe.route_options = {"status": ['!=', 'Closed'], "s8": 1, "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s9").click(function(){
            frappe.route_options = {"status": 'Zusammengeführt', "ungelesen": 1, "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s10").click(function(){
            frappe.route_options = {"hat_termine": 1, "ungelesen": 1, "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        
        $("#r").click(function(){
            frappe.route_options = {"status": ['in', ['Open', 'In Arbeit']], "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r1").click(function(){
            frappe.route_options = {"status": ['in', ['Open', 'In Arbeit']], 'beratung_prio': 'Hoch', "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r2").click(function(){
             frappe.route_options = {'status': ['in', ['Open', 'In Arbeit']], 'kontaktperson': ['like', 'Rechtsberatung Pool%'], 'beratung_prio': ['!=', 'Hoch'], "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r3").click(function(){
            frappe.route_options = {'status': ['in', ['Open', 'In Arbeit']], 'r3': 1, "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r4").click(function(){
            frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['is', 'set'], "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r5").click(function(){
            frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['is', 'set'], 'ungelesen': 1, "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r6").click(function(){
            frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['not like', 'Rechtsberatung Pool%'], 'kontaktperson': ['is', 'set'], 'ungelesen': 1, "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r7").click(function(){
            frappe.route_options = {'status': ['!=', 'Closed'], 'hat_termine': 1, "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r8").click(function(){
            frappe.route_options = {'status': 'Closed', 'hat_termine': 1, "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r9").click(function(){
            frappe.route_options = {"status": ["not in", ["Rückfragen", "Open", "Zusammengeführt", "Termin vereinbart"]], "ungelesen": 1, "kontaktperson": ['is', 'set'], "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        
        $("#p1").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung.vbz_beratung.get_user_kontaktperson",
                'args': {'only_session_user': 1},
                'async': false,
                'callback': function(r)
                {
                    frappe.route_options = {'status': ['in', ['Open', 'In Arbeit']], 'kontaktperson': ['in', r.message], "sektion_id": sektion}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#p2").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung.vbz_beratung.get_user_kontaktperson",
                'args': {},
                'async': false,
                'callback': function(r)
                {
                    frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['in', r.message], 'ungelesen': 0, "sektion_id": sektion}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#p3").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung.vbz_beratung.get_user_kontaktperson",
                'args': {},
                'async': false,
                'callback': function(r)
                {
                    frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['in', r.message], 'ungelesen': 1, "sektion_id": sektion}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#p4").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung.vbz_beratung.get_user_kontaktperson",
                'args': {},
                'async': false,
                'callback': function(r)
                {
                    frappe.route_options = {'status': 'Termin vereinbart', 'kontaktperson': ['in', r.message], 'hat_termine': 1, "sektion_id": sektion}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
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
        
        frappe.dom.unfreeze();
    }
}
