frappe.pages['vbz-beratung-alle-se'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Verarbeitungszentrale',
        single_column: true
    });
    frappe.vbz_beratung_alle_se.add_views(page);
    localStorage['firstLoad'] = true;
}
frappe.pages['vbz-beratung-alle-se'].refresh= function(wrapper){
    frappe.vbz_beratung_alle_se.show_view('vbz_beratung_alle_se');
    frappe.dom.unfreeze();
} 

frappe.vbz_beratung_alle_se = {
    add_views: function(page) {
        frappe.call({
            'method': "mvd.mvd.page.vbz_beratung_alle_se.vbz_beratung_alle_se.get_open_data",
            'args': {},
            'freeze': true,
            'freeze_message': 'Lade Verarbeitungszentrale...',
            'async': false,
            'callback': function(r)
            {
                if (r.message) {
                    page.add_view('vbz_beratung_alle_se', frappe.render_template("vbz_beratung_alle_se", eval(r.message.beratung)))
                    frappe.vbz_beratung_alle_se.add_click_handlers(eval(r.message));
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
        //~ frappe.vbz_beratung_alle_se.remove_click_handlers();

        // Define the function to hide elements based on the section
        function hideElementsBasedOnSection() {
            let ausgeblendete_elemente = {'MVSH': ['s2','a1','r7','r8','p4']};
            let sektion = frappe.boot.default_sektion;

            if (sektion in ausgeblendete_elemente) {
                ausgeblendete_elemente[sektion].forEach(element => {
                    let elementId = `${element}_as`;
                    document.getElementById(elementId).style.display = 'none';
                    console.log(`Element ${elementId} hidden`);
                });
            }
        }

        // Call the function where needed, for example, in the add_views function
        hideElementsBasedOnSection();
                
        $("#s_as").click(function(){
            frappe.route_options = {"status": 'Eingang'}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s1_as").click(function(){
            frappe.route_options = {"status": 'Eingang', "mv_mitgliedschaft": ['is', 'not set']}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s2_as").click(function(){
            frappe.route_options = {"status": ['!=', 'Closed'], "s8": 1}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s3_as").click(function(){
            frappe.route_options = {"status": 'Zusammengeführt', "ungelesen": 1}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s4_as").click(function(){
            frappe.route_options = {"status": "Rückfragen", "kontaktperson": ['is', 'not set'], "ungelesen": 0}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#s5_as").click(function(){
            frappe.route_options = {"status": "Rückfragen", "kontaktperson": ['is', 'not set'], "ungelesen": 1}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#a1_as").click(function(){
            frappe.route_options = {"status": "Open", "kontaktperson": ['like', 'Administration%']}
            frappe.set_route("List", "Beratung", "List");
        });
        // $("#s6_as").click(function(){
        //     frappe.route_options = {"status": ["not in", ["Rückfragen", "Rückfrage: Termin vereinbaren", "Eingang", "Open", "Zusammengeführt"]], "ungelesen": 1, "kontaktperson": ['is', 'not set']}
        //     frappe.set_route("List", "Beratung", "List");
        // });
        // $("#s7_as").click(function(){
        //     frappe.route_options = {"status": 'Open', "kontaktperson": ['is', 'not set']}
        //     frappe.set_route("List", "Beratung", "List");
        // });
        
        $("#r_as").click(function(){
            frappe.route_options = {"status": 'Open'}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r1_as").click(function(){
            frappe.route_options = {"status": 'Open', 'beratung_prio': 'Hoch'}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r2_as").click(function(){
            frappe.route_options = {'status': 'Open', 'kontaktperson': ['like','Rechtsberatung Pool%'], 'beratung_prio': ['!=', 'Hoch']}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r3_as").click(function(){
            // Wie kann ich machen, dass zwei filter für kontaktperson gleichzeitig funktionieren?
            frappe.route_options = {'status': 'Open', 'kontaktperson': ['not like','Rechtsberatung Pool%'], 'kontaktperson': ['is', 'set']}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r4_as").click(function(){
            frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['is', 'set']}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r5_as").click(function(){
            frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['is', 'set'], 'ungelesen': 1}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r6_as").click(function(){
            frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['not like', 'Rechtsberatung Pool%'], 'kontaktperson': ['is', 'set'], 'ungelesen': 1}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r7_as").click(function(){
            frappe.route_options = {'status': ['!=', 'Closed'], 'hat_termine': 1}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r8_as").click(function(){
            frappe.route_options = {'status': 'Closed', 'hat_termine': 1}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r9_as").click(function(){
            frappe.route_options = {"status": ["not in", ["Rückfragen", "Open", "Zusammengeführt"]], "ungelesen": 1, "kontaktperson": ['is', 'set']}
            frappe.set_route("List", "Beratung", "List");
        });
        $("#r10_bs").click(function(){
            frappe.route_options = {'status': ['!=', 'Closed'], '_user_tags': ['like', '%MNE-MVBS%']};
            frappe.set_route("List", "Beratung");
        });
        $("#r11_bs").click(function(){
            frappe.route_options = {'status': ['!=', 'Closed'], '_user_tags': ['like', '%Mandat-MVBS%']};
            frappe.set_route("List", "Beratung");
        });
        $("#r12_bs").click(function(){
            frappe.route_options = {'status': ['!=', 'Closed'], '_user_tags': ['like', '%PHF-MVBS%']};
            frappe.set_route("List", "Beratung");
        });
        
        $("#p1_as").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung_alle_se.vbz_beratung_alle_se.get_user_kontaktperson",
                'args': {'only_session_user': 1},
                'async': false,
                'callback': function(r)
                {
                    frappe.route_options = {'status': 'Open', 'kontaktperson': ['in', r.message]}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#p2_as").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung_alle_se.vbz_beratung_alle_se.get_user_kontaktperson",
                'args': {},
                'async': false,
                'callback': function(r)
                {
                    frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['in', r.message], 'ungelesen': 0}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#p3_as").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung_alle_se.vbz_beratung_alle_se.get_user_kontaktperson",
                'args': {},
                'async': false,
                'callback': function(r)
                {
                    frappe.route_options = {'status': 'Rückfragen', 'kontaktperson': ['in', r.message], 'ungelesen': 1}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        $("#p4_as").click(function(){
            frappe.call({
                'method': "mvd.mvd.page.vbz_beratung_alle_se.vbz_beratung_alle_se.get_user_kontaktperson",
                'args': {},
                'async': false,
                'callback': function(r)
                {
                    frappe.route_options = {'status': 'Termin vereinbart', 'kontaktperson': ['in', r.message], 'hat_termine': 1}
                    frappe.set_route("List", "Beratung", "List");
                }
            });
        });
        
        
        $("#rechtsberaterinnen_as").click(function(){
            frappe.set_route("List", "Termin Kontaktperson", "List");
        });
        $("#beratungskategorien_as").click(function(){
            frappe.set_route("List", "Beratungskategorie", "List");
        });
        $("#statistik_as").click(function(){
            frappe.set_route(["query-report", "Beratungsstatistik"]);
        });
        
        frappe.dom.unfreeze();
    }
}
