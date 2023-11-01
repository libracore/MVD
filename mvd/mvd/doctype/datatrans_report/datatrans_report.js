// Copyright (c) 2023, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Datatrans Report', {
    refresh: function(frm) {
        cur_frm.set_df_property('content_html','options', cur_frm.doc.content_code);
    }
});
