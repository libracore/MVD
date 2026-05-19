import frappe
from frappe import _

def execute():
    try:
        frappe.reload_doc("MVD", "doctype", "Mahnlauf")
        frappe.db.commit()
        frappe.db.sql("""SET SQL_SAFE_UPDATES = 0;""")
        frappe.db.sql("""UPDATE `tabMahnlauf` SET `mahnungen_erstellt` = '1' WHERE `docstatus` = 1;""")
        frappe.db.sql("""SET SQL_SAFE_UPDATES = 1;""")
        frappe.db.commit()
    except Exception as err:
        print("Patch Mark-Mahnungen-as-created failed")
        print(str(err))
        pass
    return
