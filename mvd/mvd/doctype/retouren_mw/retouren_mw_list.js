frappe.listview_settings['Retouren MW'] = {
    //~ add_fields: ["base_grand_total", "customer_name", "currency", "delivery_date",
        //~ "per_delivered", "per_billed", "status", "order_type", "name"],
    get_indicator: function (doc) {
        if (doc.status === "Offen") {
            return [__("Offen"), "red", "status,=,Offen"];

        } else if (doc.status === "In Bearbeitung") {
            return [__("In Bearbeitung"), "orange", "status,=,In Bearbeitung"];

        } else if (doc.status === "Abgeschlossen") {
            return [__("Abgeschlossen"), "green", "status,=,Abgeschlossen"];

        }

    }
};
