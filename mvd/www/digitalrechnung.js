function opt_out(digitalrechnung) {
    frappe.call({
        'method': 'mvd.www.digitalrechnung.handle_digitalrechnung_optout',
        'args': {
            'digitalrechnung': digitalrechnung
        },
        'async': false,
        'callback': function(res) {
            location.reload();
        }
    });
}

function change_email(digitalrechnung) {
    frappe.call({
        'method': 'mvd.www.digitalrechnung.handle_digitalrechnung_email',
        'args': {
            'digitalrechnung': digitalrechnung,
            'email': document.getElementById("email").value
        },
        'async': false,
        'callback': function(res) {
            location.reload();
        }
    });
}