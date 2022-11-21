// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mahnlauf', {
    onload: function(frm) {
        if (!cur_frm.doc.sektion_id) {
            cur_frm.set_value("sektion_id", get_default_sektion());
        }
    },
    refresh: function(frm) {
        cur_frm.fields_dict['druckvorlage'].get_query = function(doc) {
             return {
                 filters: {
                     "sektion_id": frm.doc.sektion_id,
                     "mahntyp": frm.doc.typ,
                     "mahnstufe": frm.doc.mahnstufe,
                     "dokument": "Mahnung"
                 }
             }
        }
    },
    mahnungen_buchen: function(frm) {
        frappe.dom.freeze('Bitte warten, buche Mahnungen...');
        frappe.call({
            'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.bulk_submit",
            'args': {
                'mahnlauf': cur_frm.doc.name
            },
            'callback': function(r) {
                var jobname = 'Mahnlauf ' + cur_frm.doc.name + ' (Submit)';
                let mahnung_refresher = setInterval(mahnung_refresher_handler, 3000, jobname);
                function mahnung_refresher_handler(jobname) {
                    frappe.call({
                    'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.is_mahnungs_job_running",
                        'args': {
                            'jobname': jobname
                        },
                        'callback': function(res) {
                            if (res.message == 'refresh') {
                                clearInterval(mahnung_refresher);
                                frappe.dom.unfreeze();
                                cur_frm.reload_doc();
                            }
                        }
                    });
                }
            }
        });
    },
    mahnungen_stornieren: function(frm) {
        frappe.dom.freeze('Bitte warten, storniere Mahnungen...');
        frappe.call({
            'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.bulk_cancel",
            'args': {
                'mahnlauf': cur_frm.doc.name
            },
            'callback': function(r) {
                var jobname = 'Mahnlauf ' + cur_frm.doc.name + ' (Cancel)';
                let mahnung_refresher = setInterval(mahnung_refresher_handler, 3000, jobname);
                function mahnung_refresher_handler(jobname) {
                    frappe.call({
                    'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.is_mahnungs_job_running",
                        'args': {
                            'jobname': jobname
                        },
                        'callback': function(res) {
                            if (res.message == 'refresh') {
                                clearInterval(mahnung_refresher);
                                frappe.dom.unfreeze();
                                cur_frm.reload_doc();
                            }
                        }
                    });
                }
            }
        });
    },
    erstelle_pdf: function(frm) {
        frappe.call({
            'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.mahnung_massenlauf",
            'args': {
                'mahnlauf': cur_frm.doc.name
            },
            "freeze": true,
            "freeze_message": "Bereite Massenlauf vor...",
            'callback': function(r) {
                frappe.set_route("Form", "Massenlauf", r.message);
            }
        })
        
        frappe.dom.freeze('Bitte warten, bereite Massenlauf vor...');
        frappe.call({
            'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.mahnung_massenlauf",
            'args': {
                'mahnlauf': cur_frm.doc.name
            },
            'callback': function(r) {
                var jobname = 'Mahnlauf ' + cur_frm.doc.name + ' (Vorber. Massenlauf)';
                let mahnung_refresher = setInterval(mahnung_refresher_handler, 3000, jobname);
                function mahnung_refresher_handler(jobname) {
                    frappe.call({
                    'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.is_mahnungs_job_running",
                        'args': {
                            'jobname': jobname
                        },
                        'callback': function(res) {
                            if (res.message == 'refresh') {
                                clearInterval(mahnung_refresher);
                                frappe.dom.unfreeze();
                                cur_frm.reload_doc();
                            }
                        }
                    });
                }
            }
        });
    },
    entwuerfe_loeschen: function(frm) {
        frappe.dom.freeze('Bitte warten, lösche Entwurfs Mahnungen...');
        frappe.call({
            'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.bulk_delete",
            'args': {
                'mahnlauf': cur_frm.doc.name
            },
            'callback': function(r) {
                var jobname = 'Mahnlauf ' + cur_frm.doc.name + ' (Delete)';
                let mahnung_refresher = setInterval(mahnung_refresher_handler, 3000, jobname);
                function mahnung_refresher_handler(jobname) {
                    frappe.call({
                    'method': "mvd.mvd.doctype.mahnlauf.mahnlauf.is_mahnungs_job_running",
                        'args': {
                            'jobname': jobname
                        },
                        'callback': function(res) {
                            if (res.message == 'refresh') {
                                clearInterval(mahnung_refresher);
                                frappe.dom.unfreeze();
                                cur_frm.reload_doc();
                            }
                        }
                    });
                }
            }
        });
    }
});

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
