import frappe
from frappe import _

def execute():
    try:
        print("Erstelle neuen InteressentIn Typ")
        typen = ['Mitgliedschafts-Interessent*in', 'Unterstützer*in', 'weitere Kontakte']
        for typ in typen:
            neuer_typ = frappe.get_doc({
                'doctype': 'InteressentIn Typ',
                'typ': typ
            })
            neuer_typ.insert()
        frappe.db.commit()
        print("Done")
    except Exception as err:
        print("Patch failed")
        print(str(err))
        pass
    return
