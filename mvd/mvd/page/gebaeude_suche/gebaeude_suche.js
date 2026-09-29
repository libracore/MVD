/*
 * Einfache Abfragemaske für das Amtliche Gebäudeverzeichnis.
 * Zeigt selbst keine Resultate, sondern öffnet die Listenansicht
 * mit den eingegebenen Werten als Filter.
 */
frappe.pages['gebaeude-suche'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Gebäudesuche',
        single_column: true
    });

    var fields = new frappe.ui.FieldGroup({
        body: page.main,
        fields: [
            {fieldname: 'strasse', fieldtype: 'Data', label: 'Strasse'},
            {fieldname: 'plz', fieldtype: 'Data', label: 'PLZ'},
            {fieldtype: 'Column Break'},
            {fieldname: 'nummer', fieldtype: 'Data', label: 'Nr.'},
            {fieldname: 'ort', fieldtype: 'Data', label: 'Ort'}
        ]
    });
    fields.make();

    page.set_primary_action('In Liste anzeigen', function() {
        gebaeude_suche_open_list(fields);
    });
    page.set_secondary_action('Zurücksetzen', function() {
        fields.set_values({strasse: '', nummer: '', plz: '', ort: ''});
    });

    // Enter in einem der Felder startet die Suche
    $(page.main).on('keydown', 'input', function(e) {
        if (e.which === 13) {
            e.preventDefault();
            gebaeude_suche_open_list(fields);
        }
    });
};

function gebaeude_suche_open_list(fields) {
    var v = fields.get_values(true) || {};
    var trim = function(x) { return (x || '').trim(); };
    var filters = {};

    // Strasse, PLZ und Ort: Anfang genügt ("Bahnhofstr" findet "Bahnhofstrasse").
    // Nummer exakt, sonst findet "2" auch 20, 21, 2a, ...
    if (trim(v.strasse)) filters.stn_label = ['like', trim(v.strasse) + '%'];
    if (trim(v.nummer)) filters.adr_number = trim(v.nummer);
    if (trim(v.plz)) filters.plz = ['like', trim(v.plz) + '%'];
    if (trim(v.ort)) filters.wohnort = ['like', trim(v.ort) + '%'];

    if ($.isEmptyObject(filters)) {
        frappe.msgprint('Bitte mindestens ein Feld ausfüllen.');
        return;
    }

    frappe.route_options = filters;
    frappe.set_route('List', 'Amtliches Gebaeudeverzeichnis');
}
