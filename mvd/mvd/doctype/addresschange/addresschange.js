// Copyright (c) 2026, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Addresschange', {
	refresh: function(frm) {
		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.set_intro(__("Die Adressänderung ist gespeichert und automatisch am angegebenen Datum (Gültig ab) gebucht/wirksam."), "blue");
		}
	},
	plz: function(frm) {
		pincode_lookup(frm.doc.plz, 'ort');
	}
});

function pincode_lookup(pincode, ort) {
	var filters = [['pincode','=', pincode]];
	if (pincode) {
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'Pincode',
				filters: filters,
				fields: ['name', 'pincode', 'city', 'canton_code']
			},
			async: false,
			callback: function(response) {
				if (response.message) {
					if (response.message.length == 1) {
						var city = response.message[0].city;
						cur_frm.set_value(ort, city);
					} else {
						var cities = "";
						response.message.forEach(function (record) {
							cities += (record.city + "\n");
						});
						cities = cities.substring(0, cities.length - 1);
						frappe.prompt([
								{'fieldname': 'city',
								 'fieldtype': 'Select',
								 'label': 'City',
								 'reqd': 1,
								 'options': cities,
								 'default': response.message[0].city
								}
							],
							function(values){
								var city = values.city;
								cur_frm.set_value(ort, city);
							},
							__('City'),
							__('Set')
						);
					}
				}
			}
		});
	}
}
