import frappe
from frappe import _

def execute():
    try:
        print("Change Beratungs Status")
        change = frappe.db.sql("""UPDATE `tabBeratung` SET `status` = 'Termin vereinbart' WHERE `status` = 'Termin vergeben'""", as_dict=True)
        frappe.db.commit()
        print("Done")
    except Exception as err:
        print("Patch v10.5.0 failed")
        print(str(err))
        pass
    return
