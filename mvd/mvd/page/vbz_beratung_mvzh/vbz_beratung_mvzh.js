frappe.pages['vbz-beratung-mvzh'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Verarbeitungszentrale',
        single_column: true
    });
    frappe.vbz_beratung_mvzh.add_views(page);
    localStorage['firstLoad'] = true;
}
frappe.pages['vbz-beratung-mvzh'].refresh= function(wrapper){
    frappe.vbz_beratung_mvzh.show_view('vbz_beratung_mvzh');
    frappe.dom.unfreeze();
} 

frappe.vbz_beratung_mvzh = {
    add_views: function(page) {
        frappe.call({
            'method': "mvd.mvd.page.vbz_beratung_mvzh.vbz_beratung_mvzh.get_open_data",
            'args': {},
            'freeze': true,
            'freeze_message': 'Lade Verarbeitungszentrale...',
            'async': false,
            'callback': function(r)
            {
                if (r.message) {
                    page.add_view('vbz_beratung_mvzh', frappe.render_template("vbz_beratung_mvzh", eval(r.message.beratung)))
                    frappe.vbz_beratung_mvzh.add_click_handlers(eval(r.message));
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
        //~ frappe.vbz_beratung_mvzh.remove_click_handlers();
        var sektion = frappe.boot.default_sektion || "MVZH";
        $("#s1").click(function(){
            frappe.route_options = {"status": 'Eingang', "mv_mitgliedschaft": ['is', 'not set'], "faktura_kunde": ['is', 'not set'], "sektion_id": sektion}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s6_wohnen").click(function(){
            frappe.route_options = {"status": ["not in", ["Rückfragen", "Rückfrage: Termin vereinbaren", "Eingang", "Open", "Zusammengeführt"]], "ungelesen": 1, "kontaktperson": ['is', 'not set'], "sektion_id": sektion, "typ": "Wohnen"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s6_business").click(function(){
            frappe.route_options = {"status": ["not in", ["Rückfragen", "Rückfrage: Termin vereinbaren", "Eingang", "Open", "Zusammengeführt"]], "ungelesen": 1, "kontaktperson": ['is', 'not set'], "sektion_id": sektion, "typ": "Business"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s10_wohnen").click(function(){
            frappe.call({
                method: "mvd.mvd.page.vbz_beratung_mvzh.vbz_beratung_mvzh.get_termine_in_zukunft",
                args: {},
                callback: function(r) {
                    var parents = r.message || [];
                    if (parents.length === 0) parents = [""];
                    frappe.route_options = {"ungelesen": 1, "sektion_id": sektion, "name": ["in", parents], "typ": "Wohnen"}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#s10_business").click(function(){
            frappe.call({
                method: "mvd.mvd.page.vbz_beratung_mvzh.vbz_beratung_mvzh.get_termine_in_zukunft",
                args: {},
                callback: function(r) {
                    var parents = r.message || [];
                    if (parents.length === 0) parents = [""];
                    frappe.route_options = {"ungelesen": 1, "sektion_id": sektion, "name": ["in", parents], "typ": "Business"}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });

        $("#r_wohnen").click(function(){
            frappe.route_options = {"status": ['in', ['Open', 'In Arbeit']], "sektion_id": sektion, "typ": "Wohnen"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r_business").click(function(){
            frappe.route_options = {"status": ['in', ['Open', 'In Arbeit']], "sektion_id": sektion, "typ": "Business"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r1_wohnen").click(function(){
            frappe.route_options = {"status": ['in', ['Open', 'In Arbeit']], 'beratung_prio': 'Hoch', "sektion_id": sektion, "typ": "Wohnen"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r1_business").click(function(){
            frappe.route_options = {"status": ['in', ['Open', 'In Arbeit']], 'beratung_prio': 'Hoch', "sektion_id": sektion, "typ": "Business"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r2_wohnen").click(function(){
             frappe.route_options = {'status': ['in', ['Open', 'In Arbeit']], 'kontaktperson': ['like', 'Rechtsberatung Pool%'], 'beratung_prio': ['not in', ['Hoch']], "sektion_id": sektion, "typ": "Wohnen"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r2_business").click(function(){
             frappe.route_options = {'status': ['in', ['Open', 'In Arbeit']], 'kontaktperson': ['like', 'Rechtsberatung Pool%'], 'beratung_prio': ['not in', ['Hoch']], "sektion_id": sektion, "typ": "Business"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r3_wohnen").click(function(){
            frappe.route_options = {'status': ['in', ['Open', 'In Arbeit']], 'r3': 1, "sektion_id": sektion, "typ": "Wohnen"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r3_business").click(function(){
            frappe.route_options = {'status': ['in', ['Open', 'In Arbeit']], 'r3': 1, "sektion_id": sektion, "typ": "Business"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r4_wohnen").click(function(){
            frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['is', 'set'], "sektion_id": sektion, "typ": "Wohnen"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r4_business").click(function(){
            frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['is', 'set'], "sektion_id": sektion, "typ": "Business"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r5_wohnen").click(function(){
            frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['like', 'Rechtsberatung Pool%'], 'ungelesen': 1, "sektion_id": sektion, "typ": "Wohnen"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r5_business").click(function(){
            frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['like', 'Rechtsberatung Pool%'], 'ungelesen': 1, "sektion_id": sektion, "typ": "Business"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r6_wohnen").click(function(){
            frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['not like', 'Rechtsberatung Pool%'], 'ungelesen': 1, "sektion_id": sektion, "typ": "Wohnen"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r6_business").click(function(){
            frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['not like', 'Rechtsberatung Pool%'], 'ungelesen': 1, "sektion_id": sektion, "typ": "Business"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r7_wohnen").click(function(){
            frappe.route_options = {'status': ['!=', 'Closed'], 'hat_termine': 1, "sektion_id": sektion, "typ": "Wohnen"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r7_business").click(function(){
            frappe.route_options = {'status': ['!=', 'Closed'], 'hat_termine': 1, "sektion_id": sektion, "typ": "Business"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r8_wohnen").click(function(){
            frappe.route_options = {'status': 'Closed', 'hat_termine': 1, "sektion_id": sektion, "typ": "Wohnen"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r8_business").click(function(){
            frappe.route_options = {'status': 'Closed', 'hat_termine': 1, "sektion_id": sektion, "typ": "Business"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r9_wohnen").click(function(){
            frappe.route_options = {"status": ["not in", ["Rückfragen", "Open", "Zusammengeführt", "Termin vereinbart", "Rückfrage: Termin vereinbaren"]], "ungelesen": 1, "kontaktperson": ['is', 'set'], "sektion_id": sektion, "typ": "Wohnen"}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r9_business").click(function(){
            frappe.route_options = {"status": ["not in", ["Rückfragen", "Open", "Zusammengeführt", "Termin vereinbart", "Rückfrage: Termin vereinbaren"]], "ungelesen": 1, "kontaktperson": ['is', 'set'], "sektion_id": sektion, "typ": "Business"}
            frappe.set_route("List", "Beratung", "List");
        });
     

        $("#p1_wohnen").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung_mvzh.vbz_beratung_mvzh.get_user_kontaktperson",
                'args': {'only_session_user': 1},
                'async': false,
                'callback': function(r) {
                    frappe.route_options = {'status': ['in', ['Open', 'In Arbeit']], 'kontaktperson': ['in', r.message], "sektion_id": sektion, "typ": "Wohnen"}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#p1_business").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung_mvzh.vbz_beratung_mvzh.get_user_kontaktperson",
                'args': {'only_session_user': 1},
                'async': false,
                'callback': function(r) {
                    frappe.route_options = {'status': ['in', ['Open', 'In Arbeit']], 'kontaktperson': ['in', r.message], "sektion_id": sektion, "typ": "Business"}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#p2_wohnen").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung_mvzh.vbz_beratung_mvzh.get_user_kontaktperson",
                'args': {},
                'async': false,
                'callback': function(r) {
                    frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['in', r.message], 'ungelesen': 0, "sektion_id": sektion, "typ": "Wohnen"}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#p2_business").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung_mvzh.vbz_beratung_mvzh.get_user_kontaktperson",
                'args': {},
                'async': false,
                'callback': function(r) {
                    frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['in', r.message], 'ungelesen': 0, "sektion_id": sektion, "typ": "Business"}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#p3_wohnen").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung_mvzh.vbz_beratung_mvzh.get_user_kontaktperson",
                'args': {},
                'async': false,
                'callback': function(r) {
                    frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['in', r.message], 'ungelesen': 1, "sektion_id": sektion, "typ": "Wohnen"}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#p3_business").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung_mvzh.vbz_beratung_mvzh.get_user_kontaktperson",
                'args': {},
                'async': false,
                'callback': function(r) {
                    frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['in', r.message], 'ungelesen': 1, "sektion_id": sektion, "typ": "Business"}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#p4_wohnen").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung_mvzh.vbz_beratung_mvzh.get_user_kontaktperson",
                'args': {},
                'async': false,
                'callback': function(r) {
                    frappe.route_options = {'status': 'Termin vereinbart', 'kontaktperson': ['in', r.message], 'hat_termine': 1, "sektion_id": sektion, "typ": "Wohnen"}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#p4_business").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung_mvzh.vbz_beratung_mvzh.get_user_kontaktperson",
                'args': {},
                'async': false,
                'callback': function(r) {
                    frappe.route_options = {'status': 'Termin vereinbart', 'kontaktperson': ['in', r.message], 'hat_termine': 1, "sektion_id": sektion, "typ": "Business"}
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