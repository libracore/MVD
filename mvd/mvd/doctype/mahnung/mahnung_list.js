frappe.listview_settings['Mahnung'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Erstelle Mahnungen"), function() {
            frappe.prompt(
                [
                    {'fieldname': 'sektion_id', 'fieldtype': 'Link', 'options': 'Sektion', 'label': __('Sektion'), 'reqd': 1, 'default': get_default_sektion()}
                ],
                function(values){
                    create_payment_reminders(values);
                },
                __("Erstelle Mahnungen"),
                __("Erstelle")
            );
        });  
    }
}

function create_payment_reminders(values) {
    frappe.call({
        'method': "mvd.mvd.doctype.mahnung.mahnung.create_payment_reminders",
        'args': {
            'sektion_id': values.sektion_id
        },
        'callback': function(response) {
            frappe.msgprint(response.message);
            cur_list.refresh();
        }
    });
}

function get_default_sektion() {
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
