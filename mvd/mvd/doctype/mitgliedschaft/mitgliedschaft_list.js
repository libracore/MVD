// Copyright (c) 2021, libracore and contributors
// For license information, please see license.txt

frappe.listview_settings['Mitgliedschaft'] = {
    onload: function(listview) {
        listview.page.add_action_item(__("Erstelle Serienbrief"), function() {
                var selected = listview.get_checked_items();
                if (selected.length > 0) {
                    create_serienbrief(selected);
                } else {
                    frappe.msgprint("Bitte markieren Sie zuerst die gewünschten Mitgliedschaften");
                }
        });
    }
};

function create_serienbrief(mitgliedschaften) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.call({
            method: "mvd.mvd.doctype.druckvorlage.druckvorlage.get_druckvorlagen",
            args:{
                    'sektion': mitgliedschaften[0].name,
                    'serienbrief': 1
            },
            async: false,
            callback: function(res)
            {
                var druckvorlagen = res.message;
                frappe.prompt([
                    {'fieldname': 'titel', 'fieldtype': 'Data', 'label': 'Titel', 'reqd': 1},
                    {'fieldname': 'druckvorlage', 'fieldtype': 'Link', 'label': 'Druckvorlage', 'reqd': 1, 'options': 'Druckvorlage', 
                        'get_query': function() {
                            return { 'filters': { 'name': ['in', eval(druckvorlagen)] } };
                        }
                    }
                ],
                function(values){
                    frappe.call({
                        method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.create_korrespondenz_massenlauf",
                        args:{
                                'mitgliedschaften': mitgliedschaften,
                                'druckvorlage': values.druckvorlage,
                                'titel': values.titel
                        },
                        freeze: true,
                        freeze_message: 'Erstelle Serienbrief...',
                        callback: function(r)
                        {
                            frappe.msgprint("Die Serienbriefe wurden als Korrespondenzen erzeugt und können einzeln via Mitgliedschaft oder als Sammel-PDF via Verarbeitungszentrale gedruckt werden.");
                        }
                    });
                    
                },
                'Serienbrief Erstellung',
                'Erstellen'
                )
            }
        });
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
}

// obsolet vbz
//~ function erstelle_korrespondenzen(mitgliedschaften, d) {
    //~ frappe.call({
        //~ method: "mvd.mvd.doctype.mitgliedschaft.mitgliedschaft.create_korrespondenz_serienbriefe",
        //~ args:{
                //~ 'mitgliedschaften': mitgliedschaften,
                //~ 'korrespondenzdaten': d.get_values()
        //~ },
        //~ freeze: true,
        //~ freeze_message: 'Erstelle Serienbriefe...',
        //~ callback: function(r)
        //~ {
            //~ if (r.message.length > 0) {
                //~ var erstellte_korrespondenzen = r.message;
                //~ frappe.prompt([
                    //~ {'fieldname': 'pdf', 'fieldtype': 'Button', 'label': 'PDF erstellen', 'click': function() {
                            //~ cur_dialog.hide();
                            //~ console.log("PDF");
                            //~ console.log(erstellte_korrespondenzen);
                            //~ erstelle_korrespondenzen_sammel_output('pdf', erstellte_korrespondenzen);
                        //~ }
                    //~ },
                    //~ {'fieldname': 'cb_1', 'fieldtype': 'Column Break', 'label': ''},
                    //~ {'fieldname': 'xlsx', 'fieldtype': 'Button', 'label': 'XLSX erstellen', 'click': function() {
                            //~ cur_dialog.hide();
                            //~ console.log("XLSX");
                            //~ console.log(erstellte_korrespondenzen);
                            //~ erstelle_korrespondenzen_sammel_output('xlsx', erstellte_korrespondenzen);
                        //~ }
                    //~ },
                    //~ {'fieldname': 'cb_2', 'fieldtype': 'Column Break', 'label': ''},
                    //~ {'fieldname': 'csv', 'fieldtype': 'Button', 'label': 'CSV erstellen', 'click': function() {
                            //~ cur_dialog.hide();
                            //~ console.log("CSV");
                            //~ console.log(erstellte_korrespondenzen);
                            //~ erstelle_korrespondenzen_sammel_output('csv', erstellte_korrespondenzen);
                        //~ }
                    //~ }
                //~ ],
                //~ function(values){
                    //~ // manuell
                //~ },
                //~ 'Wie wollen Sie weiterfahren?',
                //~ 'Manuell'
                //~ )
            //~ } else {
                //~ frappe.msgprint("Oops, da ist etwas schiefgelaufen!");
            //~ }
        //~ }
    //~ });
//~ }

//~ function erstelle_korrespondenzen_sammel_output(output_typ, korrespondenzen) {
    //~ if (output_typ == 'xlsx') {
        //~ frappe.call({
            //~ method: "mvd.mvd.doctype.mv_korrespondenz.mv_korrespondenz.create_sammel_xlsx",
            //~ args:{
                    //~ 'korrespondenzen': korrespondenzen
            //~ },
            //~ freeze: true,
            //~ freeze_message: 'Erstelle XLSX...',
            //~ callback: function(r)
            //~ {
                //~ if (r.message == 'done') {
                    //~ window.location = '/desk#List/File/Home/Korrespondenz';
                //~ } else {
                    //~ frappe.msgprint("Oops, da ist etwas schiefgelaufen!");
                //~ }
            //~ }
        //~ });
    //~ }
    //~ if (output_typ == 'pdf') {
        //~ frappe.call({
            //~ method: "mvd.mvd.doctype.mv_korrespondenz.mv_korrespondenz.create_sammel_pdf",
            //~ args:{
                    //~ 'korrespondenzen': korrespondenzen
            //~ },
            //~ freeze: true,
            //~ freeze_message: 'Erstelle PDF...',
            //~ callback: function(r)
            //~ {
                //~ if (r.message == 'done') {
                    //~ window.location = '/desk#List/File/Home/Korrespondenz';
                //~ } else {
                    //~ frappe.msgprint("Oops, da ist etwas schiefgelaufen!");
                //~ }
            //~ }
        //~ });
    //~ }
    //~ if (output_typ == 'csv') {
        //~ frappe.call({
            //~ method: "mvd.mvd.doctype.mv_korrespondenz.mv_korrespondenz.create_sammel_csv",
            //~ args:{
                    //~ 'korrespondenzen': korrespondenzen
            //~ },
            //~ freeze: true,
            //~ freeze_message: 'Erstelle CSV...',
            //~ callback: function(r)
            //~ {
                //~ if (r.message == 'done') {
                    //~ window.location = '/desk#List/File/Home/Korrespondenz';
                //~ } else {
                    //~ frappe.msgprint("Oops, da ist etwas schiefgelaufen!");
                //~ }
            //~ }
        //~ });
    //~ }
//~ }

//~ function kuendigungs_massendruck() {
    //~ frappe.confirm(
        //~ 'Möchten Sie ein Kündigungs Sammel-PDF erstellen?',
        //~ function(){
            //~ // on yes
            //~ frappe.call({
                //~ method: "mvd.mvd.doctype.arbeits_backlog.arbeits_backlog.kuendigungs_massendruck",
                //~ args:{},
                //~ freeze: true,
                //~ freeze_message: 'Erstelle Kündigungs Sammel-PDF...',
                //~ callback: function(r)
                //~ {
                    //~ if (r.message == 'done') {
                        //~ window.location = '/desk#List/File/Home/Kündigungen';
                    //~ } else {
                        //~ if (r.message == 'keine daten') {
                            //~ frappe.msgprint("Es existieren keine unverarbeitete Kündigungen");
                        //~ } else {
                            //~ frappe.msgprint("Oops, da ist etwas schiefgelaufen!");
                        //~ }
                    //~ }
                //~ }
            //~ });
        //~ },
        //~ function(){
            //~ // on no
            //~ frappe.show_alert('Job abgebrochen');
        //~ }
    //~ )
//~ }
