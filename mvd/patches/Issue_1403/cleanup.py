import frappe

def execute():
    print("Starte Patch für Ticket #1403...")
    try:
        print("Evaluire betroffene Mitgliedschaften...")
        mitgliedschaften = frappe.db.sql("""
            SELECT `m`.`name`
            FROM `tabMitgliedschaft` AS `m`
            WHERE 
                (`m`.`m_w_retouren_offen` > 0 OR `m`.`m_w_retouren_in_bearbeitung` > 0)
                AND EXISTS (
                    SELECT 1
                    FROM `tabRetouren` AS `r`
                    WHERE `r`.`mv_mitgliedschaft` = `m`.`name`
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM `tabRetouren` AS `r2`
                    WHERE `r2`.`mv_mitgliedschaft` = `m`.`name`
                    AND `r2`.`status` != 'Abgeschlossen'
                )
        """, as_dict=True)

        loop = 1
        total = len(mitgliedschaften)
        print("starte Verarbeitung...")
        for mitgliedschaft in mitgliedschaften:
            print("{0} von {1}".format(loop, total))
            frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'm_w_retouren_offen', 0)
            frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'm_w_retouren_in_bearbeitung', 0)
            frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'm_w_anzahl', 0)
            frappe.db.set_value("Mitgliedschaft", mitgliedschaft.name, 'retoure_in_folge', 0)
            frappe.db.commit()
            loop += 1
        print("Done")
    except Exception as err:
        print("Patch failed")
        print(str(err))
        pass
    return