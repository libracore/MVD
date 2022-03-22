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
        
        listview.page.add_menu_item( __("Alle Entwurfs-Mahnungen buchen"), function() {
            frappe.confirm(
                'Wollen Sie alle Entwurfs-Mahnungen buchen?',
                function(){
                    // on yes
                    submit_mahnungen([], 1)
                },
                function(){
                    // on no
                }
            )
        });
        
        listview.page.add_menu_item( __("Alle Entwurfs-Mahnungen löschen"), function() {
            frappe.confirm(
                'Wollen Sie alle Entwurfs-Mahnungen löschen?',
                function(){
                    // on yes
                    delete_mahnungen()
                },
                function(){
                    // on no
                }
            )
        });
        
        $("[data-label='Submit']").parent().unbind();
        $("[data-label='Submit']").parent().click(function(){
            frappe.confirm('Möchten Sie die Markierten Mahnungen buchen?',
            () => {
                var selected_mahnungen = cur_list.get_checked_items();
                submit_mahnungen(selected_mahnungen, 0);
            }, () => {
                // No
            })
            
        });
    }
}

function submit_mahnungen(mahnungen, alle) {
    frappe.dom.freeze('Bitte warten, buche Mahnungen...');
    frappe.call({
        'method': "mvd.mvd.doctype.mahnung.mahnung.bulk_submit",
        'args': {
            'mahnungen': mahnungen,
            'alle': alle
        },
        'callback': function(r) {
            var jobname = r.message;
            if (jobname != 'keine') {
                jobname = "Buche Mahnungen " + jobname;
                let mahnung_refresher = setInterval(mahnung_refresher_handler, 3000, jobname);
                function mahnung_refresher_handler(jobname) {
                    frappe.call({
                    'method': "mvd.mvd.doctype.mahnung.mahnung.is_mahnungs_job_running",
                        'args': {
                            'jobname': jobname
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
            } else {
                frappe.dom.unfreeze();
                frappe.msgprint("Es gibt keine Mahnungen zum verbuchen.");
            }
        }
    });
}

function delete_mahnungen() {
    frappe.dom.freeze('Bitte warten, lösche Entwurfs-Mahnungen...');
    frappe.call({
        'method': "mvd.mvd.doctype.mahnung.mahnung.bulk_delete",
        'callback': function(r) {
            var jobname = r.message;
            if (jobname != 'keine') {
                jobname = "Lösche Entwurfs-Mahnungen " + jobname;
                let mahnung_refresher = setInterval(mahnung_refresher_handler, 3000, jobname);
                function mahnung_refresher_handler(jobname) {
                    frappe.call({
                    'method': "mvd.mvd.doctype.mahnung.mahnung.is_mahnungs_job_running",
                        'args': {
                            'jobname': jobname
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
            } else {
                frappe.dom.unfreeze();
                frappe.msgprint("Es gibt keine Mahnungen zum löschen.");
            }
        }
    });
}

function create_payment_reminders(values) {
    if (frappe.user.has_role("MV_MA")) {
        frappe.dom.freeze('Bitte warten, erstelle Mahnungen...');
        frappe.call({
            'method': "mvd.mvd.doctype.mahnung.mahnung.create_payment_reminders",
            'args': {
                'sektion_id': values.sektion_id
            },
            'callback': function(response) {
                var jobname = values.sektion_id + " Mahnlauf";
                let mahnung_refresher = setInterval(mahnung_refresher_handler, 3000, jobname);
                function mahnung_refresher_handler(jobname) {
                    frappe.call({
                    'method': "mvd.mvd.doctype.mahnung.mahnung.is_mahnungs_job_running",
                        'args': {
                            'jobname': jobname
                        },
                        'callback': function(res) {
                            if (res.message == 'refresh') {
                                clearInterval(mahnung_refresher);
                                frappe.dom.unfreeze();
                                cur_list.refresh();
                            }
                        }
                    });
                };
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
