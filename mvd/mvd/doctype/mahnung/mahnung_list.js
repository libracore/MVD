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
        $("[data-label='Submit']").parent().unbind();
        $("[data-label='Submit']").parent().click(function(){
            frappe.confirm('Möchten Sie die Markierten Mahnungen buchen?',
            () => {
                var selected_mahnungen = cur_list.get_checked_items();
                submit_mahnungen(selected_mahnungen);
            }, () => {
                // No
            })
            
        });
    }
}

function submit_mahnungen(mahnungen) {
    frappe.dom.freeze('Bitte warten, buche Mahnungen...');
    frappe.call({
        'method': "mvd.mvd.doctype.mahnung.mahnung.bulk_submit",
        'args': {
            'mahnungen': mahnungen
        },
        'callback': function(r) {
            var jobname = r.message;
            let mahnung_refresher = setInterval(mahnung_refresher_handler, 3000, jobname);
            function mahnung_refresher_handler(jobname) {
                frappe.call({
                'method': "mvd.mvd.doctype.mahnung.mahnung.is_buhchungs_job_running",
                    'args': {
                        'mahnung': jobname
                    },
                    'callback': function(res) {
                        if (res.message == 'refresh') {
                            clearInterval(mahnung_refresher);
                            frappe.dom.unfreeze();
                            cur_list.refresh();
                        }
                    }
                });
            }
        }
    });
}

function create_payment_reminders(values) {
    if (frappe.user.has_role("MV_MA")) {
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
    } else {
        frappe.msgprint("Sie haben keine Berechtigung zur Ausführung dieser Aktion.");
    }
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
