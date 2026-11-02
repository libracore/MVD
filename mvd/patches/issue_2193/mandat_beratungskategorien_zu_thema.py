import frappe

def execute():
    # Mandat: die Felder beratungskategorie(_2/_3) wurden durch die Tabelle "thema" ersetzt.
    # Läuft vor dem DocType-Sync; die alten Spalten sind dann noch vorhanden.
    try:
        spalten = frappe.db.get_table_columns("Mandat")
        if "beratungskategorie" not in spalten:
            return

        mandate = frappe.db.sql("""
            SELECT `name`, `beratungskategorie`, `beratungskategorie_2`, `beratungskategorie_3`
            FROM `tabMandat`
            WHERE IFNULL(`beratungskategorie`, '') != ''
            OR IFNULL(`beratungskategorie_2`, '') != ''
            OR IFNULL(`beratungskategorie_3`, '') != ''
        """, as_dict=True)

        for mandat in mandate:
            vorhanden = frappe.db.sql_list("""
                SELECT `thema` FROM `tabRSV Thema MultiTable`
                WHERE `parenttype` = 'Mandat' AND `parentfield` = 'thema' AND `parent` = %s
            """, mandat.name)
            idx = len(vorhanden)
            for kategorie in (mandat.beratungskategorie, mandat.beratungskategorie_2, mandat.beratungskategorie_3):
                if not kategorie or kategorie in vorhanden:
                    continue
                # gelöschte Beratungskategorien auslassen, sonst lässt sich das Mandat nicht mehr speichern
                if not frappe.db.exists("Beratungskategorie", kategorie):
                    continue
                idx += 1
                frappe.db.sql("""
                    INSERT INTO `tabRSV Thema MultiTable`
                        (`name`, `creation`, `modified`, `owner`, `modified_by`, `docstatus`,
                         `parent`, `parentfield`, `parenttype`, `idx`, `thema`)
                    VALUES (%s, NOW(), NOW(), 'Administrator', 'Administrator', 0,
                            %s, 'thema', 'Mandat', %s, %s)
                """, (frappe.generate_hash(length=10), mandat.name, idx, kategorie))
                vorhanden.append(kategorie)

        frappe.db.commit()
    except Exception as err:
        print("Patch mandat_beratungskategorien_zu_thema failed")
        print(str(err))
