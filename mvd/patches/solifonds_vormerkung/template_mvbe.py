import frappe

def execute():
    # Neues Feld Sektion.template_vormerkung_solifonds: zuerst das DocType neu laden (Patches laufen vor dem Schema-Sync)
    frappe.reload_doc("mvd", "doctype", "sektion")

    # MVBE: Vorlage «Vormerkung Solifonds» eintragen, falls vorhanden und noch nichts eingetragen ist
    template = "Vormerkung Solifonds"
    if not frappe.db.exists("Sektion", "MVBE"):
        return
    if not frappe.db.exists("Email Template", template):
        print("Email Template «{0}» nicht gefunden, Feld nicht gesetzt.".format(template))
        return
    if not frappe.db.get_value("Sektion", "MVBE", "template_vormerkung_solifonds"):
        frappe.db.set_value("Sektion", "MVBE", "template_vormerkung_solifonds", template, update_modified=False)
