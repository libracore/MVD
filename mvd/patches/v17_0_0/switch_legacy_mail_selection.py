import frappe
from frappe import _

def execute():
    try:
        frappe.db.sql("""SET SQL_SAFE_UPDATES = 0;""")
        frappe.db.sql("""UPDATE `tabSektion` SET `legacy_mode` = '1' WHERE `legacy_mode` = '2';""")
        frappe.db.sql("""SET SQL_SAFE_UPDATES = 1;""")
        frappe.db.commit()
    except Exception as err:
        print("Patch Legacy-Mode-Switch failed")
        print(str(err))
        pass
    return
