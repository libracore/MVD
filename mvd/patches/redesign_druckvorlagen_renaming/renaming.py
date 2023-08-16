import frappe
from frappe import _

def execute():
    try:
        print("Renaming Druckvorlagen (Druckformat Redesign)")
        frappe.reload_doc("mvd", "doctype", "Druckvorlage")
        druckvorlagen = frappe.db.sql("""SELECT `name` FROM `tabDruckvorlage`""", as_dict=True)
        total = len(druckvorlagen)
        loop = 1
        for druckvorlage in druckvorlagen:
            print("{0} of {1}".format(loop, total))
            d = druckvorlage.name
            if "ä" in d or "ö" in d or "ü" in d or "Ä" in d or "Ö" in d or "Ü" in d:
                new_name = d.replace("ä", "ae").replace("Ä", "Ae").replace("ö", "oe").replace("Ö", "Oe").replace("ü", "ue").replace("Ü", "Ue")
                frappe.rename_doc('Druckvorlage', d, new_name)
            
            loop += 1
        
    except Exception as err:
        print(err)
        print("Patch Druckvorlagen Renaming failed")
        pass
    return
