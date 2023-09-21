import frappe
from frappe import _

def execute():
    try:
        print("Resette Beratungs Protection")
        resette = frappe.db.sql("""UPDATE `tabBeratung` SET `gesperrt_von` = null, `gesperrt_am` = null""", as_dict=True)
        frappe.db.commit()
        print("Done")
    except Exception as err:
        print("Patch v10.3.3 failed")
        print(str(err))
        pass
    return
