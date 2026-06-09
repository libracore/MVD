import frappe
from frappe import _
from tqdm import tqdm

def execute():
    try:
        frappe.reload_doc("MVD", "doctype", "APB Zuweisung")
        frappe.reload_doc("MVD", "doctype", "Beratung Termin")
        frappe.db.sql(
            """
                UPDATE `tabAPB Zuweisung` SET `beratungstyp` = `beratungskategorie`
            """
        )
        frappe.db.sql(
            """
                UPDATE `tabBeratung Termin` SET `beratungstyp` = `beratungskategorie`
            """
        )
        frappe.db.commit()
    except Exception as err:
        print("Patch migrate_beratungskategorie_to_beratungstyp failed")
        print(str(err))
        pass
    return
