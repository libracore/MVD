import frappe
from frappe import _

def execute():
    try:
        print("Aktualisiere Beratungen (Auto ToDo)")
        frappe.reload_doc("mvd", "doctype", "Beratung")
        beratungen = frappe.db.sql("""SELECT `name`, `kontaktperson` FROM `tabBeratung`""", as_dict=True)
        total = len(beratungen)
        loop = 1
        for beratung in beratungen:
            print("{0} of {1}".format(loop, total))
            if beratung.kontaktperson:
                frappe.db.set_value("Beratung", beratung.name, 'auto_todo_log', beratung.kontaktperson, update_modified=False)
            loop += 1
        frappe.db.commit()
    except:
        print("Patch v7.14.0 failed")
        pass
    return
