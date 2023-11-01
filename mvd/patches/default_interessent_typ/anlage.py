import frappe
from frappe import _

def execute():
    try:
        print("Hinterlege default InteressentIn Typ")
        frappe.db.sql("""UPDATE `tabMitgliedschaft` SET `interessent_typ` = 'Mitgliedschafts-Interessent*in' WHERE `status_c` = 'Interessent*in'""", as_list=True)
        frappe.db.commit()
        print("Done")
    except Exception as err:
        print("Patch failed")
        print(str(err))
        pass
    return
