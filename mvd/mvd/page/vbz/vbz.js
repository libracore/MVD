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
            'method': "mvd.mvd.page.vbz.vbz.get_open_data",
            'args': {
                'sektion': frappe.vbz.get_default_sektion()
            },
            'freeze': true,
            'freeze_message': 'Lade Verarbeitungszentrale...',
            'async': false,
            'callback': function(r)
            {
                if (r.message) {
                    page.add_view('overview', frappe.render_template("overview", eval(r.message)))
                    page.add_view('validierung', frappe.render_template("validierung", eval(r.message.validierung)))
                    page.add_view('massenlauf', frappe.render_template("massenlauf", {
                        'kuendigung': eval(r.message.kuendigung_massenlauf),
                        'korrespondenz': eval(r.message.korrespondenz_massenlauf),
                        'zuzug': eval(r.message.zuzug_massenlauf)
                    }))
                    page.add_view('adresspflege', frappe.render_template("adresspflege", {}))
                    frappe.vbz.add_click_handlers(eval(r.message));
                }
            }
        });
    },
    show_view: function(view) {
        cur_page.page.page.set_view(view);;
    },
    remove_click_handlers: function() {
        $(".back-to-overview").off("click");
        $("#mitglieder").off("click");
        $("#suchmaske").off("click");
        $("#arbeitsbacklog").off("click");
        $("#validieren").off("click");
        $("#neuanlage").off("click");
        $("#handbuch").off("click");
        $("#massenlauf").off("click");
        $("#adresspflege").off("click");
        $("#serienbrief").off("click");
        $("#camt").off("click");
        $("#adresspflege_second").off("click");
        $("#goto_klassisch").off("click");
        $("#korrespondenz_qty").off("click");
        $("#korrespondenz_print").off("click");
        $("#zuzug_qty").off("click");
        $("#zuzug_print").off("click");
    },
    add_click_handlers: function(open_datas) {
        frappe.vbz.remove_click_handlers();
        $("#camt").click(function(){
            var default_sektion = frappe.vbz.get_default_sektion();
            if (default_sektion) {
                frappe.route_options = {"sektion_id": default_sektion};
            } else {
                frappe.route_options = {};
            }
            frappe.set_route("List", "CAMT Import");
        });
        $("#goto_klassisch").click(function(){
            frappe.set_route("modules/MVD");
        });
        $("#serienbrief").click(function(){
            frappe.prompt([
                {'fieldname': 'html', 'fieldtype': 'HTML', 'label': '', 'options': '<p>Durch Bestätigung mit "Weiter" können Sie folgenden Workflow verfolgen:</p><ol><li>Suchen nach Mitgliedschaften</li><li>Selektieren der Mitgliedschaften</li><li>Auswahl der Druckvorlage</li><li>Generierung Korrespondenzen mit Massenvermerkung</li></ol><p>Im Anschluss an den obigen Workflow können in der Verarbeitungszentrale unter "Massenlauf > Korrespondenz" ein entsprechendes Sammel-PDF erzeugen und downloaden.</p>'}  
            ],
            function(values){
                frappe.set_route("mvd-suchmaske");
            },
            'Wollen Sie weiterfahren?',
            'Weiter'
            )
        });
        $("#massenlauf").click(function(){
            frappe.vbz.show_view('massenlauf');
        });
        $("#adresspflege").click(function(){
            frappe.vbz.show_view('adresspflege');
        });
        $("#adresspflege_second").click(function(){
            frappe.vbz.show_view('adresspflege');
        });
        $(".back-to-overview").click(function(){
            frappe.vbz.show_view('overview');
        });
        $("#handbuch").click(function(){
            window.open('https://wiki.mieterverband.ch/pages/viewpage.action?pageId=74744863', '_blank').focus();
        });
        $("#mitglieder").click(function(){
            var default_sektion = frappe.vbz.get_default_sektion();
            if (default_sektion) {
                frappe.route_options = {"sektion_id": default_sektion};
            } else {
                frappe.route_options = {};
            }
            frappe.set_route("List", "Mitgliedschaft");
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
        $("#validierung_allgemein").click(function(){
            frappe.route_options = {"validierung_notwendig": 1}
            frappe.set_route("List", "Mitgliedschaft");
        });
        $("#neuanlage").click(function(){
            frappe.set_route("mvd-suchmaske");
        });
        
        // validierungen
        $("#online_beitritte").click(function(){
            frappe.route_options = {"name": ['in', open_datas.validierung.online_beitritt.names]}
            frappe.set_route("List", "Mitgliedschaft");
        });
        $("#online_anmeldungen").click(function(){
            frappe.route_options = {"name": ['in', open_datas.validierung.online_anmeldung.names]}
            frappe.set_route("List", "Mitgliedschaft");
        });
        $("#online_kuendigungen").click(function(){
            frappe.route_options = {"name": ['in', open_datas.validierung.online_kuendigung.names]}
            frappe.set_route("List", "Mitgliedschaft");
        });
        $("#zuzuege").click(function(){
            frappe.route_options = {"name": ['in', open_datas.validierung.zuzug.names], "validierung_notwendig": 1}
            frappe.set_route("List", "Mitgliedschaft");
        });
        
        // massenlauf
        $("#keundigung_qty").click(function(){
            frappe.route_options = {"name": ['in', open_datas.kuendigung_massenlauf.names]}
            frappe.set_route("List", "Mitgliedschaft");
        });
        $("#kuendigung_print").click(function(){
            frappe.vbz.kuendigung_massenlauf();
        });
        $("#zuzug_qty").click(function(){
            frappe.route_options = {"name": ['in', open_datas.zuzug_massenlauf.names]}
            frappe.set_route("List", "Mitgliedschaft");
        });
        $("#zuzug_print").click(function(){
            frappe.vbz.zuzug_massenlauf();
        });
        $("#begruessung_qty").click(function(){
            frappe.msgprint("Das muss noch programmiert werden!");
        });
        $("#begruessung_print").click(function(){
            frappe.msgprint("Das muss noch programmiert werden!");
        });
        $("#korrespondenz_qty").click(function(){
            frappe.route_options = {"massenlauf": 1}
            frappe.set_route("List", "Korrespondenz");
        });
        $("#korrespondenz_print").click(function(){
            frappe.vbz.korrespondenz_massenlauf();
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
    korrespondenz_massenlauf: function() {
        frappe.dom.freeze('Erstelle Sammel-PDF...');
        frappe.call({
            method: "mvd.mvd.page.vbz.vbz.korrespondenz_massenlauf",
            args:{},
            freeze: true,
            freeze_message: 'Erstelle Sammel-PDF...',
            async: false,
            callback: function(r)
            {
                frappe.dom.unfreeze();
                frappe.route_options = {"name": r.message}
                frappe.set_route("List", "File");
            }
        });
    },
    kuendigung_massenlauf: function() {
        frappe.dom.freeze('Erstelle Sammel-PDF...');
        frappe.call({
            method: "mvd.mvd.page.vbz.vbz.kuendigung_massenlauf",
            args:{},
            freeze: true,
            freeze_message: 'Erstelle Sammel-PDF...',
            async: false,
            callback: function(r)
            {
                frappe.dom.unfreeze();
                frappe.route_options = {"name": r.message}
                frappe.set_route("List", "File");
            }
        });
    },
    zuzug_massenlauf: function() {
        frappe.dom.freeze('Erstelle Sammel-PDF...');
        frappe.call({
            method: "mvd.mvd.page.vbz.vbz.zuzug_massenlauf",
            args:{},
            freeze: true,
            freeze_message: 'Erstelle Sammel-PDF...',
            async: false,
            callback: function(r)
            {
                frappe.dom.unfreeze();
                frappe.route_options = {"name": r.message}
                frappe.set_route("List", "File");
            }
        });
    }
}
