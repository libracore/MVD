// Copyright (c) 2025, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on("Webshop Order Download Link", {
    refresh(frm) {
        frm.add_custom_button("Links generieren - Klick für mehr Informationen", function() {
            frappe.confirm(
                'Dieser Button erzeugt Download-Links für alle downloadbaren Artikel. <br> Konkret: <br> - alle Artikel-Codes, die auf -D enden werden gesucht <br> - bei jedem Artikel wird geschaut, ob PDFs angehängt sind; falls ja wird das neuste ausgewählt <br> - es wird ein Donwload-Link erzeugt, der auf dieses PDF zeigt <br> Bereits bestehende Links werden NICHT überschrieben, es werden nur Links erzeugt für Artikel, die noch nicht bestehen. <br> Falls du für einen Artikel einen neuen Download-Link generieren willst, dann lösche zuerst den Eintrag in Webshop Order Download Link und generiere einen neuen Link mit diesem Knopf und bestätige mit Ja<br> Falls du ein neues PDF bei einem Artikel hochgeladen hast, musst du ebenfalls mit Ja bestätigen, damit der Link angepasst wird.',
                function() { // yes
                    frappe.call({
                        method: "mvd.mvd.doctype.webshop_order_download_link.webshop_order_download_link.generate_download_links",
                        callback: function(r) {
                            frappe.msgprint(r.message);
                            frm.reload_doc();
                        }
                    });
                },
                function() { // no
                    frappe.msgprint("Aktion abgebrochen");
                }
            );
        }).addClass("btn-primary");
    }
});

