import frappe

def execute():
    # Die Bestätigungs-Mail an die VA geht neu auch bei Solifonds-Mandaten raus. Bestehende Solifonds-Mandate
    # mit VA als «gesendet» markieren, sonst ginge die Mail beim nächsten Speichern nachträglich raus.
    frappe.reload_doc("mvd", "doctype", "mandat")
    frappe.db.sql("""
        UPDATE `tabMandat`
        SET `bestaetigungs_email_gesendet` = 1
        WHERE `typ` = 'Solidaritätsfonds'
          AND IFNULL(`kontaktperson`, '') != ''
          AND IFNULL(`bestaetigungs_email_gesendet`, 0) = 0
    """)
