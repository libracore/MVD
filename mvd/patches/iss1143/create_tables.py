import frappe

def execute():
    try:
        print("Erstelle Tabelle MitgliedMainNumber")
        frappe.db.sql("""CREATE TABLE MitgliedMainNumber (
            id MEDIUMINT NOT NULL AUTO_INCREMENT,
            name VARCHAR(300) NOT NULL,
            PRIMARY KEY (id)
        );""")
        frappe.db.commit()
        last_nr = frappe.db.sql("""
                                SELECT `mitglied_nr_raw` AS `last_nr`
                                FROM `tabMitglied Main Naming`
                                ORDER BY `mitglied_nr_raw` DESC
                                LIMIT 1
                                """, as_dict=True)[0].last_nr or 5100000
        new_nr = last_nr + 1
        frappe.db.sql("""ALTER TABLE MitgliedMainNumber AUTO_INCREMENT = {0};""".format(new_nr))
        frappe.db.commit()
        
        print("Erstelle Tabelle MitgliedMainId")
        frappe.db.sql("""CREATE TABLE MitgliedMainId (
            id MEDIUMINT NOT NULL AUTO_INCREMENT,
            name VARCHAR(300) NOT NULL,
            PRIMARY KEY (id)
        );""")
        frappe.db.commit()
        last_id = frappe.db.sql("""
                                SELECT `mitglied_id` AS `last_id`
                                FROM `tabMitglied Main Naming`
                                ORDER BY `mitglied_id` DESC
                                LIMIT 1
                                """, as_dict=True)[0].last_id or 1100000
        new_id = last_id + 1
        frappe.db.sql("""ALTER TABLE MitgliedMainId AUTO_INCREMENT = {0};""".format(new_id))
        frappe.db.commit()
        print("Done")
    except Exception as err:
        print("Patch failed")
        print(str(err))
        pass
    return