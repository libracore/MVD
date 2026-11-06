import frappe

def execute():
    # #2209: Mitglied-Nr. (fetch_from mv_mitgliedschaft.mitglied_nr) bei bestehenden Mandaten nachtragen.
    # Patches laufen vor dem Schema-Sync, darum zuerst den DocType neu laden (legt die Spalte an).
    frappe.reload_doc("mvd", "doctype", "mandat")
    frappe.db.sql("""
        UPDATE `tabMandat` AS `m`
        JOIN `tabMitgliedschaft` AS `ms` ON `ms`.`name` = `m`.`mv_mitgliedschaft`
        SET `m`.`mitglied_nr` = `ms`.`mitglied_nr`
        WHERE IFNULL(`m`.`mitglied_nr`, '') = ''
          AND IFNULL(`ms`.`mitglied_nr`, '') != ''
    """)
