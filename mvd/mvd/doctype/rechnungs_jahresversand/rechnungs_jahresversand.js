// Copyright (c) 2022, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Rechnungs Jahresversand', {
    refresh: function(frm) {
        if (!cur_frm.doc.sektion_id) {
            cur_frm.set_value("sektion_id", frappe.boot.default_sektion);
        }
        
        if (!frappe.user.has_role("System Manager")) {
            cur_frm.set_df_property('status', 'read_only', 1);
        }
    },
    download_draft: function(frm) {
        frappe.call({
            'method': "mvd.mvd.doctype.rechnungs_jahresversand.rechnungs_jahresversand.get_draft_csv",
            'args': {
                'jahresversand': cur_frm.doc.name
            },
            'freeze': true,
            'freeze_message': 'Erstelle Entwurfs CSV...',
            'callback': function(response) {
                var csv = response.message;

                if (csv == 'done') {
                    cur_frm.reload_doc();
                }
            }
        });
    },
    rechnungen_stornieren: function(frm) {
        // variante ajax call
        //~ frappe.call({
            //~ 'method': "mvd.mvd.doctype.rechnungs_jahresversand.rechnungs_jahresversand.storno",
            //~ 'args': {
                //~ 'jahresversand': cur_frm.doc.name
            //~ },
            //~ 'freeze': true,
            //~ 'freeze_message': 'Storniere Rechnungen...',
            //~ 'callback': function(response) {
                //~ frappe.set_route("Form", "Rechnungs Jahresversand", r.message);
            //~ }
        //~ });
        
        // variante bg-job
        //~ frappe.dom.freeze('Storniere Rechnungen...');
        //~ frappe.call({
            //~ 'method': "mvd.mvd.doctype.rechnungs_jahresversand.rechnungs_jahresversand.storno",
            //~ 'args': {
                //~ 'jahresversand': cur_frm.doc.name
            //~ },
            //~ 'callback': function(r) {
                //~ var jobname = r.message;
                //~ var jobname_org = r.message;
                //~ if (jobname != 'keine') {
                    //~ jobname = "Storniere Rechnungs Jahresversand " + jobname;
                    //~ let refresher = setInterval(refresher_handler, 3000, jobname);
                    //~ function refresher_handler(jobname) {
                        //~ frappe.call({
                        //~ 'method': "mvd.mvd.doctype.rechnungs_jahresversand.rechnungs_jahresversand.is_job_running",
                            //~ 'args': {
                                //~ 'jobname': jobname
                            //~ },
                            //~ 'callback': function(res) {
                                //~ if (res.message == 'refresh') {
                                    //~ clearInterval(mahnung_refresher);
                                    //~ frappe.dom.unfreeze();
                                    //~ frappe.set_route("Form", "Rechnungs Jahresversand", jobname_org);
                                //~ }
                            //~ }
                        //~ });
                    //~ }
                //~ } else {
                    //~ frappe.dom.unfreeze();
                    //~ frappe.msgprint("Es gibt nichts zum stornieren.");
                //~ }
            //~ }
        //~ });
        
        frappe.msgprint("Diese Funktion steht im Moment nicht zur Verfügung");
    }
});
