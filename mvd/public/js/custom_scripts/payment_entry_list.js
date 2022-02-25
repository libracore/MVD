frappe.listview_settings['Payment Entry'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Zeige Doppelzahlungen"), function() {
            frappe.call({
                method: "mvd.mvd.doctype.camt_import.camt_import.get_filter_for_doppelte",
                args:{},
                callback: function(r)
                {
                    var doppelte = eval(r.message);
                    cur_list.filter_area.add("Payment Entry", "name", "in", doppelte);
                }
            });
        });
        listview.page.add_menu_item( __("Zeige nicht zugewiesene"), function() {
            frappe.call({
                method: "mvd.mvd.doctype.camt_import.camt_import.get_filter_for_unassigned",
                args:{},
                callback: function(r)
                {
                    var standard_kunden = eval(r.message);
                    cur_list.filter_area.add("Payment Entry", "party", "not in", standard_kunden);
                }
            });
        });
    }
}
