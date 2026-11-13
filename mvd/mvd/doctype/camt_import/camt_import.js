// Copyright (c) 2022, libracore AG and contributors
// For license information, please see license.txt

let clicked = false;

frappe.ui.form.on('CAMT Import', {
    refresh: function(frm) {
        zeige_camt_fehler(frm);

        // hidding Version 1 of CAMT Importer
        if (cur_frm.doc.version_1) {
            cur_frm.set_df_property('section_steuerung','hidden', 1);
            cur_frm.set_df_property('overview','hidden', 1);
            cur_frm.set_df_property('section_verarbeitungs_daten','hidden', 1);
            cur_frm.set_df_property('section_redesign','hidden', 1);
            cur_frm.set_df_property('section_ungebucht','hidden', 1);
            cur_frm.set_df_property('section_import','hidden', 1);
        }
        
        // auto save
        if (frm.doc.__islocal) {
           if (frappe.boot.default_sektion) {
               cur_frm.set_value("sektion_id", frappe.boot.default_sektion);
           }
           cur_frm.save();
        }
        // filter account
        cur_frm.fields_dict['account'].get_query = function(doc) {
            return {
                filters: {
                    'account_type': 'Bank',
                    'company': cur_frm.doc.company
                }
            }
        }
        
        if (cur_frm.doc.status != 'Open') {
            cur_frm.set_df_property('account','read_only',1);
            cur_frm.set_df_property('company','read_only',1);
            cur_frm.set_df_property('sektion_id','read_only',1);
            cur_frm.set_df_property('camt_file','read_only',1);
            if (cur_frm.doc.status == 'Aktualisierung notwendig') {
                aktualisiere_camt_uebersicht(frm);
            }
            cur_frm.set_df_property('html_report','options', cur_frm.doc.report);
        } else {
            ['account', 'sektion_id', 'camt_file'].forEach(field => frm.set_df_property(field, 'read_only', 0));
            frm.set_df_property('html_report', 'options', '');
        }

        frappe.mvd.aktualisiere_verrechnungs_buttons(frm);
        frappe.mvd.aktualisiere_bankkonto_button(frm);
        aktualisiere_matching_button(frm);
        aktualisiere_verbuchen_button(frm);
        ueberwache_camt_reset(frm);
        ueberwache_camt_verarbeitung(frm);
        
        if (frappe.user.has_role("System Manager")) {
            frm.add_custom_button(__("Manuelle Status Änderung"), function() {
                change_state_manual(frm);
            }).addClass("btn-warning")
        }
        if (frappe.user.has_role("System Manager") && frm.doc.status !== 'In Verarbeitung') {
            frm.add_custom_button(__("CAMT Reset"), function() {
                frappe.confirm(
                    'Alle Zahlungen, Firmenverrechnungen und zuordbar erzeugte Belege dieses CAMT-Imports werden storniert und gelöscht. ' +
                    'Mitgliedsdaten werden, soweit zuverlässig möglich, wiederhergestellt. Andernfalls erhalten Sie einen Hinweis. ' +
                    'Bereits versendete E-Mails und externe Aktionen können nicht zurückgeholt werden. CAMT-Import zurücksetzen?',
                    function(){
                        // on yes
                        reset_camt(frm);
                    },
                    function(){
                        // on no
                        show_alert('Abbruch');
                    }
                )
            }).addClass("btn-danger")
        }
    },
    account: function(frm) {
        cur_frm.save();
    },
    import: function(frm) {
        // Verhinderung von Doppelklicks
        if (clicked) return;
        clicked = true;
        setTimeout(() => { clicked = false; }, 2000);

        if (cur_frm.doc.account) {
            import_payments(frm, 1, 0, 0, 1);
        } else {
            frappe.msgprint("Bitte zuerst eine Sektion / ein Account auswählen");
        }
    },
    nur_zahlungen_einlesen: function(frm) {
        // Verhinderung von Doppelklicks
        if (clicked) return;
        clicked = true;
        setTimeout(() => { clicked = false; }, 2000);

        if (cur_frm.doc.account) {
            import_payments(frm, 1, 0, 0, 0);
        } else {
            frappe.msgprint("Bitte zuerst eine Sektion / ein Account auswählen");
        }
    },
    zahlungen_matchen: function(frm) {
        // Verhinderung von Doppelklicks
        if (clicked) return;
        clicked = true;
        setTimeout(() => { clicked = false; }, 2000);

        if (cur_frm.doc.account) {
            import_payments(frm, 0, 1, 0, 0);
        } else {
            frappe.msgprint("Bitte zuerst eine Sektion / ein Account auswählen");
        }
    },
    zahlungen_verbuchen: function(frm) {
        // Verhinderung von Doppelklicks
        if (clicked) return;
        clicked = true;
        setTimeout(() => { clicked = false; }, 2000);
        
        if (cur_frm.doc.account) {
            import_payments(frm, 0, 0, 1, 0);
        } else {
            frappe.msgprint("Bitte zuerst eine Sektion / ein Account auswählen");
        }
    },
    show_overpaid: function(frm) {
        frappe.route_options = {
            "camt_import": cur_frm.doc.name,
            "camt_status": 'Überbezahlt'
        }
        frappe.set_route("List", "Payment Entry");
    },
    show_unassigned: function(frm) {
        frappe.route_options = {
            "camt_import": cur_frm.doc.name,
            "camt_status": 'Nicht zugewiesen',
            "docstatus": 0
        }
        frappe.set_route("List", "Payment Entry");
    },
    aktualisiere_camt_uebersicht: function(frm) {
        aktualisiere_camt_uebersicht(frm);
    },
    show_imported_payments: function(frm) {
        frappe.route_options = {"camt_import": cur_frm.doc.name}
        frappe.set_route("List", "Payment Entry");
    },
    show_zugewiesen_unverbucht: function(frm) {
        frappe.route_options = {
            "camt_import": cur_frm.doc.name,
            "camt_status": 'Zugewiesen',
            "docstatus": 0
        }
        frappe.set_route("List", "Payment Entry");
    },
    zahlungen_nachladen: function(frm) {
        import_payments(frm, 0, 0, 0, 0, 1);
    }
});

function aktualisiere_matching_button(frm) {
    frm.set_df_property('zahlungen_matchen', 'depends_on', function(doc) {
        return doc.camt_file && doc.account && doc.sektion_id &&
            ['Zahlungen eingelesen', 'Zahlungen zugeordnet'].includes(doc.status) &&
            doc.__onload && doc.__onload.hat_zahlungen_zum_matchen;
    });
    frm.layout.refresh_dependency();
}

function aktualisiere_verbuchen_button(frm) {
    frm.set_df_property('zahlungen_verbuchen', 'depends_on', function(doc) {
        return doc.camt_file && doc.account && doc.sektion_id && doc.status === 'Zahlungen zugeordnet' &&
            doc.__onload && doc.__onload.hat_offene_rechnungs_matches;
    });
    frm.layout.refresh_dependency();
    frm.remove_custom_button(__('Zahlungen verbuchen'));

    if (frm.doc.__islocal || frm.doc.version_1 || frm.is_dirty() || frm.doc.status !== 'Verarbeitet' ||
        !frm.doc.camt_file || !frm.doc.account || !frm.doc.sektion_id ||
        !frm.doc.__onload || !frm.doc.__onload.hat_offene_rechnungs_matches) return;
    
    frm.add_custom_button(__('Zahlungen verbuchen'), () => frm.trigger('zahlungen_verbuchen'));
}

function zeige_camt_fehler(frm) {
    if (frm.doc.status !== 'Failed') {
        frm.set_intro('');
        return;
    }

    const details = frm.doc.errors || 'Der CAMT-Import ist fehlgeschlagen. Es wurde keine Fehlerursache gespeichert. Bitte prüfen Sie die Quelldatei.';
    const esc = value => frappe.utils.escape_html(String(value));
    frm.set_intro(esc(details.split('\n')[0]), 'red');

    if (frm.doc.errors) {
        frm.add_custom_button('Fehlerdetails', function() {
            frappe.msgprint({title: 'CAMT-Verarbeitungsfehler', indicator: 'red', message: '<pre style="white-space:pre-wrap">' + esc(details) + '</pre>'});
        });
    }
}

function import_payments(frm, einlesen, matchen, verbuchen, all_in_one, nachladen) {
    beende_camt_reset_ueberwachung(frm);
    beende_camt_verarbeitung_ueberwachung(frm);

    const saved = frm.is_dirty() || frm.doc.__islocal ? frm.save() : Promise.resolve();

    saved.then(function(){
        frappe.call({
            method: 'mvd.mvd.doctype.camt_import.camt_import.lese_camt_file',
            args: {
                'file_path': frm.doc.camt_file,
                'camt_import': frm.doc.name,
                'einlesen': einlesen,
                'matchen': matchen,
                'verbuchen': verbuchen,
                'all_in_one': all_in_one,
                'nachladen': nachladen || 0
            },
            callback: function(r) {
                frm.reload_doc();

                if (r.message && r.message.status === 'Failed') {
                    frappe.msgprint({title: 'CAMT-Import fehlgeschlagen', indicator: 'red', message: frappe.utils.escape_html(r.message.message)});
                    return;
                }

                if (r.message && r.message.progress_token) {
                    verfolge_camt_verarbeitung(frm, r.message.progress_token);
                    return;
                }
                frappe.msgprint("Der CAMT-Import wurde gestartet.<br>Sie können den Fortschritt <a href='/desk#background_jobs'>hier</a> verfolgen.");
            }
        });
    });
}

function aktualisiere_camt_uebersicht(frm) {
    if (!cur_frm.doc.version_1) {
        frappe.call({
            method: 'mvd.mvd.doctype.camt_import.camt_import.aktualisiere_camt_uebersicht',
            args: {
                'camt_import': cur_frm.doc.name
            },
            freeze: true,
            freeze_message: 'Analysiere Daten...',
            callback: function(r) {
                cur_frm.reload_doc();
            }
        });
    } else {
        frappe.msgprint("Dieser Datensatz wurde mit einer vorgänger Version des CAMT Importers erzeugt.", "Diese Funktion steht leider nicht zur Verfügung");
    }
}

function change_state_manual(frm) {
    frappe.prompt([
        {'fieldname': 'new_state', 'fieldtype': 'Select', 'label': 'Neuer Astatus', 'options': "Open\nZahlungen eingelesen\nZahlungen zugeordnet\nClosed", 'reqd': 1}  
    ],
    function(values){
        cur_frm.set_value("status", values.new_state);
        cur_frm.save()
    },
    'Manuelle Status Änderung',
    'Ändern'
    )
}

function reset_camt(frm) {
    beende_camt_verarbeitung_ueberwachung(frm);

    frappe.call({
        method: 'mvd.mvd.doctype.camt_import.utils.reset_camt',
        args: {
            'camt': frm.doc.name
        },
        freeze: true,
        freeze_message: 'Starte CAMT Reset...',
        callback: function(r) {
            frm.reload_doc();
            const result = r.message;
            if (result.status === 'queued' || result.status === 'running') {
                verfolge_camt_reset(frm, result.token);
            } else {
                zeige_reset_ergebnis(result);
            }
        }
    });
}

function zeige_reset_ergebnis(result) {
    const esc = value => frappe.utils.escape_html(String(value));
    frappe.msgprint('CAMT-Import zurückgesetzt.' + (result ? ' Entfernte Belege: ' + esc(result.geloeschte_belege) + (result.hinweise.length ? '<br><br>Bitte prüfen:<br>' + result.hinweise.map(esc).join('<br>') : '') + '<br><br>' + esc(result.externe_aktionen) : ''));
}

function ueberwache_camt_reset(frm) {
    if (['Zahlungen eingelesen', 'Zahlungen zugeordnet', 'Verarbeitet', 'Closed'].includes(frm.doc.status)) {
        beende_camt_reset_ueberwachung(frm);
        return;
    }

    if (frm.doc.status !== 'In Verarbeitung' || !frm.doc.reset_protokoll) return;

    try {
        const job = JSON.parse(frm.doc.reset_protokoll).reset_auftrag;
        if (job && ['queued', 'running'].includes(job.status)) verfolge_camt_reset(frm, job.token);
    } catch (e) {
        // Ein älteres/ungültiges Rücksetzprotokoll, dies darf die übrige Formularanzeige nicht blockieren...
    }
}

function beende_camt_reset_ueberwachung(frm) {
    if (frm.__camt_reset_watch) {
        frm.__camt_reset_finished = frm.__camt_reset_watch;
        frm.__camt_reset_watch = null;
        frm.set_intro('');
    }
}

function setze_camt_fortschritt_hinweis(frm, message) {
    frm.set_intro('');
    if (message) frm.set_intro(message, 'blue');
}

function verfolge_camt_reset(frm, token) {
    if (frm.__camt_reset_finished === token) return;
    if (frm.__camt_reset_watch === token) return;

    frm.__camt_reset_watch = token;
    const name = frm.doc.name;
    const esc = value => frappe.utils.escape_html(String(value));

    setze_camt_fortschritt_hinweis(frm, 'CAMT Reset läuft im Hintergrund. Der Fortschritt wird hier aktualisiert.');

    function aktuell() {
        if (frm.doc.name !== name) {
            if (frm.__camt_reset_watch === token) frm.__camt_reset_watch = null;
            return false;
        }
        return frm.__camt_reset_watch === token;
    }

    function poll() {
        if (!aktuell()) return;

        frappe.call({
            method: 'mvd.mvd.doctype.camt_import.reset_jobs.status',
            args: {camt: name, token: token},
            error: function() { if (aktuell()) frm.__camt_reset_watch = null; },
            callback: function(r) {
                if (!aktuell()) return;

                const state = r.message;
                if (state.status === 'queued' || state.status === 'running') {
                    setze_camt_fortschritt_hinweis(frm, esc(state.message || 'CAMT Reset läuft im Hintergrund.') + ' (' + esc(state.percent || 0) + ' %)');
                    setTimeout(poll, 3000);
                    return;
                }

                frm.__camt_reset_finished = token;
                frm.__camt_reset_watch = null;
                frm.set_intro('');

                if (state.status === 'veraltet') return;

                frm.reload_doc();
                if (state.status === 'done') zeige_reset_ergebnis(state.result);
                if (state.status === 'failed') {
                    frappe.msgprint({title: 'CAMT Reset fehlgeschlagen', indicator: 'red', message: esc(state.error || 'Bitte prüfen Sie die Fehlerdetails im CAMT-Import.')});
                }
            }
        });
    }

    poll();
}

function ueberwache_camt_verarbeitung(frm) {
    const job = frm.doc.__onload && frm.doc.__onload.verarbeitung_auftrag;
    if (job && job.token) verfolge_camt_verarbeitung(frm, job.token);
}

function beende_camt_verarbeitung_ueberwachung(frm) {
    if (frm.__camt_verarbeitung_watch) {
        frm.__camt_verarbeitung_finished = frm.__camt_verarbeitung_watch;
        frm.__camt_verarbeitung_watch = null;
        frm.set_intro('');
    }
}

function verfolge_camt_verarbeitung(frm, token) {
    if (frm.__camt_verarbeitung_finished === token || frm.__camt_verarbeitung_watch === token) return;

    beende_camt_reset_ueberwachung(frm);

    frm.__camt_verarbeitung_watch = token;
    const name = frm.doc.name;
    const esc = value => frappe.utils.escape_html(String(value));

    setze_camt_fortschritt_hinweis(frm, 'CAMT-Verarbeitung wartet auf einen Hintergrund-Worker.');

    function aktuell() {
        if (frm.doc.name !== name) {
            if (frm.__camt_verarbeitung_watch === token) frm.__camt_verarbeitung_watch = null;
            return false;
        }
        return frm.__camt_verarbeitung_watch === token;
    }

    function poll() {
        if (!aktuell()) return;

        frappe.call({
            method: 'mvd.mvd.doctype.camt_import.fortschritt.status',
            args: {camt: name, token: token},
            error: function() {
                if (aktuell()) {
                    setze_camt_fortschritt_hinweis(frm, 'Fortschritt vorübergehend nicht verfügbar. Die Verarbeitung läuft im Hintergrund weiter.');
                    setTimeout(poll, 5000);
                }
            },
            callback: function(r) {
                if (!aktuell()) return;

                const state = r.message;
                if (state.status === 'queued' || state.status === 'running') {
                    const count = state.total == null ? '' : ': ' + esc(state.done || 0) + ' / ' + esc(state.total);
                    setze_camt_fortschritt_hinweis(frm, esc(state.schritt || 'CAMT-Verarbeitung') + count + ' (' + esc(state.percent || 0) + ' %) – ' + esc(state.message || 'Verarbeite Zahlungen.'));
                    setTimeout(poll, 3000);
                    return;
                }

                frm.__camt_verarbeitung_finished = token;
                frm.__camt_verarbeitung_watch = null;
                frm.set_intro('');

                if (state.status === 'weiter') {
                    verfolge_camt_verarbeitung(frm, state.next_token);
                    return;
                }

                if (state.status === 'veraltet') return;

                frm.reload_doc();
                if (state.status === 'failed') {
                    frappe.msgprint({title: 'CAMT-Import fehlgeschlagen', indicator: 'red', message: esc(state.error || 'Bitte prüfen Sie die Fehlerdetails im CAMT-Import.')});
                }
                if (state.status === 'paused') {
                    frappe.msgprint({title: 'CAMT-Verarbeitung angehalten', indicator: 'orange', message: esc(state.message)});
                }
            }
        });
    }
    
    poll();
}
