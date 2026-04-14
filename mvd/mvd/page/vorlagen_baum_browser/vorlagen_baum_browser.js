// Copyright (c) 2026, libracore AG and contributors
// For license information, please see license.txt
frappe.pages['vorlagen-baum-browser'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Vorlagen Baum Browser',
        single_column: true
    });

    new mvd_vorlagen_baum.ui.VorlagenBaumNavigator({
        wrapper: $(page.body),
        on_select: function(node) {
            frappe.msgprint("Ausgewählt: " + node.label + " (" + node.name + ")");
        }
    });
};