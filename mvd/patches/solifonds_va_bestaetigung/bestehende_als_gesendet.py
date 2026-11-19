import frappe

def execute():
    # Patches laufen vor dem Schema-Sync: DocTypes zuerst neu laden, damit die neuen Spalten
    # (Sektion.mandat_absender_mail, Sektion.template_bestaetigung_kontaktperson_solifonds) existieren.
    frappe.reload_doc("mvd", "doctype", "sektion")
    frappe.reload_doc("mvd", "doctype", "mandat")

    # MVBE: Absender-Adresse und Solifonds-Template für Mandate
    if frappe.db.exists("Sektion", "MVBE"):
        werte = {"mandat_absender_mail": "mv@be.mieterverband.ch"}
        template = "MVBE - Mandat Kontaktperson Solidaritätsfonds"
        if frappe.db.exists("Email Template", template):
            werte["template_bestaetigung_kontaktperson_solifonds"] = template
        else:
            print("Email Template «{0}» nicht gefunden, Feld nicht gesetzt.".format(template))
        frappe.db.set_value("Sektion", "MVBE", werte, update_modified=False)

    # Die Bestätigungs-Mail an die VA geht neu auch bei Solifonds-Mandaten raus. Bestehende Solifonds-Mandate
    # mit VA als «gesendet» markieren, sonst ginge die Mail beim nächsten Speichern nachträglich raus.
    frappe.db.sql("""
        UPDATE `tabMandat`
        SET `bestaetigungs_email_gesendet` = 1
        WHERE `typ` = 'Solidaritätsfonds'
          AND IFNULL(`kontaktperson`, '') != ''
          AND IFNULL(`bestaetigungs_email_gesendet`, 0) = 0
    """)
