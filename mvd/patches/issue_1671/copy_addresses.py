import frappe

def execute():
    try:
        print("Kopiere Korrespondenz- zu Objektadresse")
        frappe.db.sql("""
            UPDATE `tabMitgliedschaft`
            SET
                `objekt_zusatz_adresse` = `zusatz_adresse`,
                `objekt_strasse` = `strasse`,
                `objekt_hausnummer` = `nummer`,
                `objekt_nummer_zu` = `nummer_zu`,
                `objekt_plz` = `plz`,
                `objekt_ort` = `ort`
            WHERE IFNULL(`abweichende_objektadresse`, 0) != 1;
        """)
        frappe.db.commit()
        print("Done")
    except Exception as err:
        print("Patch failed")
        print(str(err))
        pass
    return