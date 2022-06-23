frappe.pages['vbz-massenlauf'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Verarbeitungszentrale',
        single_column: true
    });
}
frappe.pages['vbz-massenlauf'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Verarbeitungszentrale',
        single_column: true
    });
    frappe.vbz_massenlauf.add_views(page);
}
frappe.pages['vbz-massenlauf'].refresh= function(wrapper){
    frappe.vbz_massenlauf.show_view('vbz_massenlauf');
    frappe.dom.unfreeze();
} 

frappe.vbz_massenlauf = {
    add_views: function(page) {
        frappe.call({
            'method': "mvd.mvd.page.vbz_massenlauf.vbz_massenlauf.get_open_data",
            'args': {},
            'freeze': true,
            'freeze_message': 'Lade Massenläufe...',
            'async': false,
            'callback': function(r)
            {
                if (r.message) {
                    page.add_view('vbz_massenlauf', frappe.render_template("vbz_massenlauf", {
                        'kuendigung': eval(r.message.kuendigung_massenlauf),
                        'korrespondenz': eval(r.message.korrespondenz_massenlauf),
                        'zuzug': eval(r.message.zuzug_massenlauf),
                        'rechnungen': eval(r.message.rg_massenlauf),
                        'begruessung_online': eval(r.message.begruessung_online_massenlauf),
                        'mahnungen': eval(r.message.mahnung_massenlauf),
                        'begruessung_bezahlt': eval(r.message.begruessung_bezahlt_massenlauf)
                    }))
                    frappe.vbz_massenlauf.add_click_handlers(eval(r.message));
                }
            }
        });
    },
    show_view: function(view) {
        cur_page.page.page.set_view(view);
    },
    remove_click_handlers: function() {
        $("#korrespondenz_qty").off("click");
        $("#korrespondenz_print").off("click");
        $("#zuzug_qty").off("click");
        $("#zuzug_print").off("click");
        $("#rechnungen_qty").off("click");
        $("#rechnungen_print").off("click");
        $("#begruessung_online_qty").off("click");
        $("#begruessung_online_print").off("click");
        $("#mahnungen_qty").off("click");
        $("#mahnungen_print").off("click");
    },
    add_click_handlers: function(open_datas) {
        frappe.vbz_massenlauf.remove_click_handlers();
        
        $("#keundigung_qty").click(function(){
            frappe.route_options = {"kuendigung_verarbeiten": 1, 'kuendigung_verarbeiten': 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#kuendigung_print").click(function(){
            if (!frappe.user.has_role("MV_RB")||frappe.user.has_role("System Manager")) {
                frappe.vbz_massenlauf.kuendigung_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        $("#zuzug_qty").click(function(){
            frappe.route_options = {"zuzug_massendruck": 1, 'zuzug_massendruck': 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#zuzug_print").click(function(){
            if (!frappe.user.has_role("MV_RB")||frappe.user.has_role("System Manager")) {
                frappe.vbz_massenlauf.zuzug_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        $("#begruessung_qty").click(function(){
            frappe.route_options = {"begruessung_massendruck": 1, 'begruessung_via_zahlung': 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#begruessung_print").click(function(){
            if (!frappe.user.has_role("MV_RB")||frappe.user.has_role("System Manager")) {
                frappe.vbz_massenlauf.begruessung_via_zahlung_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        $("#korrespondenz_qty").click(function(){
            frappe.route_options = {"massenlauf": 1}
            frappe.set_route("List", "Korrespondenz", "List");
        });
        $("#korrespondenz_print").click(function(){
            if (!frappe.user.has_role("MV_RB")||frappe.user.has_role("System Manager")) {
                frappe.vbz_massenlauf.korrespondenz_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        $("#rechnungen_qty").click(function(){
            frappe.route_options = {"rg_massendruck_vormerkung": 1, 'rg_massendruck_vormerkung': 1}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#rechnungen_print").click(function(){
            if (!frappe.user.has_role("MV_RB")||frappe.user.has_role("System Manager")) {
                frappe.vbz_massenlauf.rg_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        $("#begruessung_online_qty").click(function(){
            frappe.route_options = {"begruessung_massendruck": 1, 'begruessung_via_zahlung': 0}
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#begruessung_online_print").click(function(){
            if (!frappe.user.has_role("MV_RB")||frappe.user.has_role("System Manager")) {
                frappe.vbz_massenlauf.begruessung_online_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        $("#mahnungen_qty").click(function(){
            frappe.route_options = {"docstatus": 1, 'massenlauf': 1}
            frappe.set_route("List", "Mahnung", "List");
        });
        $("#mahnungen_print").click(function(){
            if (!frappe.user.has_role("MV_RB")||frappe.user.has_role("System Manager")) {
                frappe.vbz_massenlauf.mahnung_massenlauf();
            } else {
                frappe.msgprint("Sie haben eine Read-Only Rolle und sind für zur Ausführung dieser Aktion nicht berechtigt.");
            }
        });
        
        frappe.dom.unfreeze();
    },
    korrespondenz_massenlauf: function() {
        var sektion = frappe.boot.default_sektion;
        if (frappe.boot.multi_sektion) {
            frappe.prompt([
                {'fieldname': 'sektion', 'fieldtype': 'Link', 'label': 'Sektion', 'reqd': 1, 'options': 'Sektion', 'default': sektion}  
            ],
            function(values){
                frappe.vbz_massenlauf.execute_korrespondenz_massenlauf(values.sektion);
            },
            'Sektionsauswahl',
            'Weiter'
            )
        } else {
            frappe.vbz_massenlauf.execute_korrespondenz_massenlauf(sektion);
        }
    },
    execute_korrespondenz_massenlauf: function(sektion) {
        frappe.dom.freeze('Vorbereitung Massenlauf...');
        frappe.call({
            method: "mvd.mvd.page.vbz_massenlauf.vbz_massenlauf.korrespondenz_massenlauf",
            args:{
                'sektion': sektion
            },
            freeze: true,
            freeze_message: 'Vorbereitung Massenlauf...',
            async: false,
            callback: function(r)
            {
                frappe.dom.unfreeze();
                frappe.set_route("Form", "Massenlauf", r.message);
            }
        });
    },
    kuendigung_massenlauf: function() {
        var sektion = frappe.boot.default_sektion;
        if (frappe.boot.multi_sektion) {
            frappe.prompt([
                {'fieldname': 'sektion', 'fieldtype': 'Link', 'label': 'Sektion', 'reqd': 1, 'options': 'Sektion', 'default': sektion}  
            ],
            function(values){
                frappe.vbz_massenlauf.execute_kuendigung_massenlauf(values.sektion);
            },
            'Sektionsauswahl',
            'Weiter'
            )
        } else {
            frappe.vbz_massenlauf.execute_kuendigung_massenlauf(sektion);
        }
    },
    execute_kuendigung_massenlauf: function(sektion) {
        frappe.dom.freeze('Vorbereitung Massenlauf...');
        frappe.call({
            method: "mvd.mvd.page.vbz_massenlauf.vbz_massenlauf.kuendigung_massenlauf",
            args:{
                'sektion': sektion
            },
            freeze: true,
            freeze_message: 'Vorbereitung Massenlauf...',
            async: false,
            callback: function(r)
            {
                frappe.dom.unfreeze();
                frappe.set_route("Form", "Massenlauf", r.message);
            }
        });
    },
    zuzug_massenlauf: function() {
        var sektion = frappe.boot.default_sektion;
        if (frappe.boot.multi_sektion) {
            frappe.prompt([
                {'fieldname': 'sektion', 'fieldtype': 'Link', 'label': 'Sektion', 'reqd': 1, 'options': 'Sektion', 'default': sektion}  
            ],
            function(values){
                frappe.vbz_massenlauf.execute_zuzug_massenlauf(values.sektion);
            },
            'Sektionsauswahl',
            'Weiter'
            )
        } else {
            frappe.vbz_massenlauf.execute_zuzug_massenlauf(sektion);
        }
    },
    execute_zuzug_massenlauf: function(sektion) {
        frappe.dom.freeze('Vorbereitung Massenlauf...');
        frappe.call({
            method: "mvd.mvd.page.vbz_massenlauf.vbz_massenlauf.zuzug_massenlauf",
            args:{
                'sektion': sektion
            },
            freeze: true,
            freeze_message: 'Vorbereitung Massenlauf...',
            async: false,
            callback: function(r)
            {
                frappe.dom.unfreeze();
                frappe.set_route("Form", "Massenlauf", r.message);
            }
        });
    },
    rg_massenlauf: function() {
        var sektion = frappe.boot.default_sektion;
        if (frappe.boot.multi_sektion) {
            frappe.prompt([
                {'fieldname': 'sektion', 'fieldtype': 'Link', 'label': 'Sektion', 'reqd': 1, 'options': 'Sektion', 'default': sektion}  
            ],
            function(values){
                frappe.vbz_massenlauf.execute_rg_massenlauf(values.sektion);
            },
            'Sektionsauswahl',
            'Weiter'
            )
        } else {
            frappe.vbz_massenlauf.execute_rg_massenlauf(sektion);
        }
    },
    execute_rg_massenlauf: function(sektion) {
        frappe.dom.freeze('Vorbereitung Massenlauf...');
        frappe.call({
            method: "mvd.mvd.page.vbz_massenlauf.vbz_massenlauf.rg_massenlauf",
            args:{
                'sektion': sektion
            },
            freeze: true,
            freeze_message: 'Vorbereitung Massenlauf...',
            async: false,
            callback: function(r)
            {
                frappe.dom.unfreeze();
                frappe.set_route("Form", "Massenlauf", r.message);
            }
        });
    },
    begruessung_online_massenlauf: function() {
        var sektion = frappe.boot.default_sektion;
        if (frappe.boot.multi_sektion) {
            frappe.prompt([
                {'fieldname': 'sektion', 'fieldtype': 'Link', 'label': 'Sektion', 'reqd': 1, 'options': 'Sektion', 'default': sektion}  
            ],
            function(values){
                frappe.vbz_massenlauf.execute_begruessung_online_massenlauf(values.sektion);
            },
            'Sektionsauswahl',
            'Weiter'
            )
        } else {
            frappe.vbz_massenlauf.execute_begruessung_online_massenlauf(sektion);
        }
    },
    execute_begruessung_online_massenlauf: function(sektion) {
        frappe.dom.freeze('Vorbereitung Massenlauf...');
        frappe.call({
            method: "mvd.mvd.page.vbz_massenlauf.vbz_massenlauf.begruessung_online_massenlauf",
            args:{
                'sektion': sektion
            },
            freeze: true,
            freeze_message: 'Vorbereitung Massenlauf...',
            async: false,
            callback: function(r)
            {
                frappe.dom.unfreeze();
                frappe.set_route("Form", "Massenlauf", r.message);
            }
        });
    },
    begruessung_via_zahlung_massenlauf: function() {
        var sektion = frappe.boot.default_sektion;
        if (frappe.boot.multi_sektion) {
            frappe.prompt([
                {'fieldname': 'sektion', 'fieldtype': 'Link', 'label': 'Sektion', 'reqd': 1, 'options': 'Sektion', 'default': sektion}  
            ],
            function(values){
                frappe.vbz_massenlauf.execute_begruessung_via_zahlung_massenlauf(values.sektion);
            },
            'Sektionsauswahl',
            'Weiter'
            )
        } else {
            frappe.vbz_massenlauf.execute_begruessung_via_zahlung_massenlauf(sektion);
        }
    },
    execute_begruessung_via_zahlung_massenlauf: function(sektion) {
        frappe.dom.freeze('Vorbereitung Massenlauf...');
        frappe.call({
            method: "mvd.mvd.page.vbz_massenlauf.vbz_massenlauf.begruessung_via_zahlung_massenlauf",
            args:{
                'sektion': sektion
            },
            freeze: true,
            freeze_message: 'Vorbereitung Massenlauf...',
            async: false,
            callback: function(r)
            {
                frappe.dom.unfreeze();
                frappe.set_route("Form", "Massenlauf", r.message);
            }
        });
    },
    mahnung_massenlauf: function() {
        var sektion = frappe.boot.default_sektion;
        if (frappe.boot.multi_sektion) {
            frappe.prompt([
                {'fieldname': 'sektion', 'fieldtype': 'Link', 'label': 'Sektion', 'reqd': 1, 'options': 'Sektion', 'default': sektion}  
            ],
            function(values){
                frappe.vbz_massenlauf.execute_mahnung_massenlauf(values.sektion);
            },
            'Sektionsauswahl',
            'Weiter'
            )
        } else {
            frappe.vbz_massenlauf.execute_mahnung_massenlauf(sektion);
        }
    },
    execute_mahnung_massenlauf: function(sektion) {
        frappe.dom.freeze('Vorbereitung Massenlauf...');
        frappe.call({
            method: "mvd.mvd.page.vbz_massenlauf.vbz_massenlauf.mahnung_massenlauf",
            args:{
                'sektion': sektion
            },
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
