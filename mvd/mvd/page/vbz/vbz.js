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
                    page.add_view('adresspflege', frappe.render_template("adresspflege", eval(r.message)))
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
        $("#info_blog").off("click");
        $("#massenlauf").off("click");
        $("#adresspflege").off("click");
        $("#serienbrief").off("click");
        $("#serienmail").off("click");
        $("#camt").off("click");
        $("#goto_klassisch").off("click");
        $("#todo").off("click");
        $("#beratung").off("click");
        $("#beratung_alle_sektionen").off("click");
        $("#termin").off("click");
        $("#mahnung").off("click");
        $("#zweimal_unzustellbar").off("click");
        $("#einmal_unzustellbar").off("click");
        $("#offene_retouren").off("click");
        $("#retouren_in_bearbeitung").off("click");
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
            var prompt_txt = `
                    <p>
                        Durch Bestätigung mit "Weiter" können Sie folgenden Workflow verfolgen:
                    </p>
                    <ol>
                        <li>Suchen nach Mitgliedschaften via <a href="/desk#mvd-suchmaske">Suchmaske</a></li>
                        <li>Absprung in die vorgefilterte Listenansicht (ctrl+L oder "Menü > Listenansicht zeigen")</li>
                        <li>Selektieren der Mitgliedschaften</li>
                        <li>Auswahl der Druckvorlage</li>
                        <li>Generierung Korrespondenzen mit Massenvermerkung</li>
                    </ol>
                    <p>
                        Im Anschluss an den obigen Workflow können in der Verarbeitungszentrale unter "Massenlauf > Korrespondenz" ein entsprechendes Sammel-PDF erzeugen und downloaden.
                    </p>
                    <p><b>Hinweis:</b> Sie können auch direkt via <a href="/desk#List/Mitgliedschaft/List">Listenansicht</a> die relevanten Mitglieder selektieren und mit "Aktionen > Erstelle Serienbrief" einen Serienbrief erstellen.</p>`;
            frappe.prompt([
                {'fieldname': 'html', 'fieldtype': 'HTML', 'label': '', 'options': prompt_txt}
            ],
            function(values){
                frappe.set_route("mvd-suchmaske");
            },
            'Wollen Sie weiterfahren?',
            'Weiter'
            )
        });
        $("#serienmail").click(function(){
            var prompt_txt = `
                    <p>
                        Durch Bestätigung mit "Weiter" können Sie folgenden Workflow verfolgen:
                    </p>
                    <ol>
                        <li>Suchen nach Mitgliedschaften via <a href="/desk#mvd-suchmaske">Suchmaske</a></li>
                        <li>Erstellen eines "Serien E-Mail"-Datensatzes (ctrl+M oder "Menü > Serien E-Mail erstellen")</li>
                    </ol>
                    <p><b>Optional<br></b>Sie können auch:<br>
                        <ul>
                            <li>Direkt via <a href="/desk#List/Mitgliedschaft/List">Listenansicht</a> die relevanten Mitglieder selektieren.</li>
                            <li>Oder nach dem Suchen via  <a href="/desk#mvd-suchmaske">Suchmaske</a> in die vorgefilterte Listenansicht (ctrl+L oder "Menü > Listenansicht zeigen") abspringen und
                                den Serien E-Mail Datensatz mittels "Aktionen > Erstelle Serien E-Mail" erzeugen.
                            </li>
                            <li>Oder eine <a href="/desk#List/Serien Email/List">Liste aller "Serien E-Mail"-Datensätze</a> anzeigen.</li>
                        </ul>
                    </p>`;
            frappe.prompt([
                {'fieldname': 'html', 'fieldtype': 'HTML', 'label': '', 'options': prompt_txt}
            ],
            function(values){
                frappe.set_route("mvd-suchmaske");
            },
            'Wollen Sie weiterfahren?',
            'Weiter'
            )
        });
        $("#massenlauf").click(function(){
            frappe.dom.freeze('Öffne Massenläufe...');
            frappe.set_route("vbz-massenlauf");
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
        $("#info_blog").click(function(){
            window.open('https://wiki.mieterverband.ch/pages/viewrecentblogposts.action?key=AMV', '_blank').focus();
        });
        $("#mitglieder").click(function(){
            frappe.route_options = {"aktive_mitgliedschaft": 1};
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#suchmaske").click(function(){
            frappe.set_route("mvd-suchmaske");
        });
        $("#arbeitsbacklog").click(function(){
            frappe.route_options = {"status": "Open"};
            frappe.set_route("List", "Arbeits Backlog", "List");
        });
        $("#beratung").click(function(){
            frappe.dom.freeze('Öffne Beratungen...');
            frappe.set_route("vbz-beratung");
        });
        $("#beratung_alle_sektionen").click(function(){
            frappe.dom.freeze('Öffne Beratungen...');
            frappe.set_route("vbz-beratung-alle-se");
        });
        $("#termin").click(function(){
            frappe.dom.freeze('Öffne Beratungs Terminübersicht...');
            frappe.set_route("vbz_beratung_termine");
        });
        $("#todo").click(function(){
            frappe.route_options = {'status': 'Open'};
            frappe.set_route("List", "ToDo", "List");
        });
        $("#validieren").click(function(){
            frappe.dom.freeze('Öffne Validierungen...');
            frappe.set_route("vbz-validieren");
        });
        $("#neuanlage").click(function(){
            frappe.set_route("mvd-suchmaske");
        });
        $("#zweimal_unzustellbar").click(function(){
            frappe.route_options = {"m_w_anzahl": ['>=', 1], "retoure_in_folge": 1};
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#einmal_unzustellbar").click(function(){
            frappe.route_options = {"m_w_anzahl": 1, "retoure_in_folge": 0};
            frappe.set_route("List", "Mitgliedschaft", "List");
        });
        $("#offene_retouren").click(function(){
            frappe.route_options = {"status": "Offen"};
            frappe.set_route("List", "Retouren", "List");
        });
        $("#retouren_in_bearbeitung").click(function(){
            frappe.route_options = {"status": "In Bearbeitung"};
            frappe.set_route("List", "Retouren", "List");
        });
        
        frappe.dom.unfreeze();
    }
}
