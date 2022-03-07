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
    frappe.dom.unfreeze();
} 

frappe.vbz = {
    add_views: function(page) {
        frappe.call({
            'method': "mvd.mvd.page.vbz.vbz.get_open_data",
            'args': {},
            'freeze': true,
            'freeze_message': 'Lade Verarbeitungszentrale...',
            'async': false,
            'callback': function(r)
            {
                if (r.message) {
                    page.add_view('overview', frappe.render_template("overview", eval(r.message)))
                    //~ page.add_view('validierung', frappe.render_template("validierung", eval(r.message.validierung)))
                    page.add_view('massenlauf', frappe.render_template("massenlauf", {
                        'kuendigung': eval(r.message.kuendigung_massenlauf),
                        'korrespondenz': eval(r.message.korrespondenz_massenlauf),
                        'zuzug': eval(r.message.zuzug_massenlauf),
                        'rechnungen': eval(r.message.rg_massenlauf),
                        'begruessung_online': eval(r.message.begruessung_online_massenlauf),
                        'mahnungen': eval(r.message.mahnung_massenlauf),
                        'begruessung_bezahlt': eval(r.message.begruessung_bezahlt_massenlauf)
                    }))
                    page.add_view('adresspflege', frappe.render_template("adresspflege", {}))
                    frappe.vbz.add_click_handlers(eval(r.message));
                }
            }
        });
    },
    show_view: function(view) {
        cur_page.page.page.set_view(view);
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
        $("#rechnungen_qty").off("click");
        $("#rechnungen_print").off("click");
        $("#todo").off("click");
        $("#online_mutationen").off("click");
        $("#geschenk_mitgliedschaften").off("click");
        $("#autom_adressaenderungen").off("click");
        $("#begruessung_online_qty").off("click");
        $("#begruessung_online_print").off("click");
        $("#mahnungen_qty").off("click");
        $("#mahnungen_print").off("click");
        $("#termin").off("click");
        $("#mahnung").off("click");
    },
    add_click_handlers: function(open_datas) {
        frappe.vbz.remove_click_handlers();
        $("#camt").click(function(){
            frappe.route_options = {"status": ['!=', 'Closed']};
            frappe.set_route("List", "CAMT Import", "List");
        });
        $("#mahnung").click(function(){
            frappe.route_options = {"docstatus": 0};
            frappe.set_route("List", "Mahnung", "List");
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
            frappe.route_options = {};
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#suchmaske").click(function(){
            frappe.set_route("mvd-suchmaske");
        });
        $("#arbeitsbacklog").click(function(){
            frappe.route_options = {"status": "Open"};
            frappe.set_route("List", "Arbeits Backlog", "List");
        });
        $("#termin").click(function(){
            frappe.route_options = {
                "von": ['between', [frappe.datetime.nowdate(), frappe.datetime.add_days(frappe.datetime.nowdate(), 7)]],
            };
            frappe.set_route("List", "Termin", "List");
        });
        $("#todo").click(function(){
            frappe.route_options = {'status': 'Open'};
            frappe.set_route("List", "ToDo", "List");
        });
        $("#validieren").click(function(){
            //~ frappe.vbz.show_view('validierung');
            frappe.set_route("vbz-validieren");
        });
        $("#validierung_allgemein").click(function(){
            frappe.route_options = {"validierung_notwendig": 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#neuanlage").click(function(){
            frappe.set_route("mvd-suchmaske");
        });
        
        // validierungen
        //~ $("#online_beitritte").click(function(){
            //~ frappe.route_options = {"status_c": 'Online-Beitritt', "validierung_notwendig": 1}
            //~ frappe.set_route("List", "Mitgliedschaft", "List");
        //~ });
        //~ $("#online_anmeldungen").click(function(){
            //~ frappe.route_options = {"status_c": 'Online-Anmeldung', "validierung_notwendig": 1}
            //~ frappe.set_route("List", "Mitgliedschaft", "List");
        //~ });
        //~ $("#online_kuendigungen").click(function(){
            //~ frappe.route_options = {"status_c": 'Online-Kündigung', "validierung_notwendig": 1}
            //~ frappe.set_route("List", "Mitgliedschaft", "List");
        //~ });
        //~ $("#zuzuege").click(function(){
            //~ frappe.route_options = {"status_c": 'Zuzug', "validierung_notwendig": 1}
            //~ frappe.set_route("List", "Mitgliedschaft", "List");
        //~ });
        //~ $("#online_mutationen").click(function(){
            //~ frappe.route_options = {"status_c": 'Online-Mutation', "validierung_notwendig": 1}
            //~ frappe.set_route("List", "Mitgliedschaft", "List");
        //~ });
        //~ $("#geschenk_mitgliedschaften").click(function(){
            //~ frappe.msgprint("Wird noch umgesetzt");
        //~ });
        //~ $("#autom_adressaenderungen").click(function(){
            //~ frappe.msgprint("Wird noch umgesetzt");
        //~ });
        
        // massenlauf
        $("#keundigung_qty").click(function(){
            frappe.route_options = {"kuendigung_verarbeiten": 1, 'kuendigung_verarbeiten': 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#kuendigung_print").click(function(){
            if (!frappe.user.has_role("MV_RB")) {
                frappe.vbz.kuendigung_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        $("#zuzug_qty").click(function(){
            frappe.route_options = {"zuzug_massendruck": 1, 'zuzug_massendruck': 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#zuzug_print").click(function(){
            if (!frappe.user.has_role("MV_RB")) {
                frappe.vbz.zuzug_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        $("#begruessung_qty").click(function(){
            frappe.route_options = {"begruessung_massendruck": 1, 'begruessung_via_zahlung': 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#begruessung_print").click(function(){
            if (!frappe.user.has_role("MV_RB")) {
                frappe.vbz.begruessung_via_zahlung_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        $("#korrespondenz_qty").click(function(){
            frappe.route_options = {"massenlauf": 1}
            frappe.set_route("List", "Korrespondenz", "List");
        });
        $("#korrespondenz_print").click(function(){
            if (!frappe.user.has_role("MV_RB")) {
                frappe.vbz.korrespondenz_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        $("#rechnungen_qty").click(function(){
            frappe.route_options = {"rg_massendruck_vormerkung": 1, 'rg_massendruck_vormerkung': 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#rechnungen_print").click(function(){
            if (!frappe.user.has_role("MV_RB")) {
                frappe.vbz.rg_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        $("#begruessung_online_qty").click(function(){
            frappe.route_options = {"begruessung_massendruck": 1, 'begruessung_via_zahlung': 0}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#begruessung_online_print").click(function(){
            if (!frappe.user.has_role("MV_RB")) {
                frappe.vbz.begruessung_online_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        $("#mahnungen_qty").click(function(){
            frappe.route_options = {"docstatus": 1, 'massenlauf': 1}
            frappe.set_route("List", "Mahnung", "List");
        });
        $("#mahnungen_print").click(function(){
            if (!frappe.user.has_role("MV_RB")) {
                frappe.vbz.mahnung_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        
        frappe.dom.unfreeze();
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
                frappe.set_route("List", "File", "List");
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
                frappe.set_route("List", "File", "List");
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
                frappe.set_route("List", "File", "List");
            }
        });
    },
    rg_massenlauf: function() {
        frappe.dom.freeze('Erstelle Sammel-PDF...');
        frappe.call({
            method: "mvd.mvd.page.vbz.vbz.rg_massenlauf",
            args:{},
            freeze: true,
            freeze_message: 'Erstelle Sammel-PDF...',
            async: false,
            callback: function(r)
            {
                frappe.dom.unfreeze();
                frappe.route_options = {"name": r.message}
                frappe.set_route("List", "File", "List");
            }
        });
    },
    begruessung_online_massenlauf: function() {
        frappe.dom.freeze('Erstelle Sammel-PDF...');
        frappe.call({
            method: "mvd.mvd.page.vbz.vbz.begruessung_online_massenlauf",
            args:{},
            freeze: true,
            freeze_message: 'Erstelle Sammel-PDF...',
            async: false,
            callback: function(r)
            {
                frappe.dom.unfreeze();
                frappe.route_options = {"name": r.message}
                frappe.set_route("List", "File", "List");
            }
        });
    },
    begruessung_via_zahlung_massenlauf: function() {
        frappe.dom.freeze('Erstelle Sammel-PDF...');
        frappe.call({
            method: "mvd.mvd.page.vbz.vbz.begruessung_via_zahlung_massenlauf",
            args:{},
            freeze: true,
            freeze_message: 'Erstelle Sammel-PDF...',
            async: false,
            callback: function(r)
            {
                frappe.dom.unfreeze();
                frappe.route_options = {"name": r.message}
                frappe.set_route("List", "File", "List");
            }
        });
    },
    mahnung_massenlauf: function() {
        frappe.dom.freeze('Vorbereitung Massenlauf...');
        frappe.call({
            method: "mvd.mvd.page.vbz.vbz.mahnung_massenlauf",
            args:{},
            freeze: true,
            freeze_message: 'Vorbereitung Massenlauf...',
            async: false,
            callback: function(r)
            {
                frappe.dom.unfreeze();
                frappe.set_route("Form", "Massenlauf", r.message);
            }
        });
    }
}
