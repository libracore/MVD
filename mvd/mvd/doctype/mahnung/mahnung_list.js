frappe.listview_settings['Mahnung'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Erstelle Mahnungen"), function() {
            frappe.set_route("List", "Mahnlauf");
        });
    }
}
