import frappe
from frappe import _

def execute():
    try:
        print("Füge Nachnamen in Mahnungen hinzu")
        frappe.reload_doc("mvd", "doctype", "Mahnung")
        mahnungen = frappe.db.sql("""SELECT `name` FROM `tabMahnung`""", as_dict=True)
        total = len(mahnungen)
        loop = 1
        for mahnung in mahnungen:
            print("{0} of {1}".format(loop, total))
            m = frappe.get_doc("Mahnung", mahnung.name)
            if m.mv_mitgliedschaft:
                if m.customer == frappe.db.get_value("Mitgliedschaft", m.mv_mitgliedschaft, 'kunde_mitglied'):
                    nachname_kunde = frappe.db.get_value("Mitgliedschaft", m.mv_mitgliedschaft, 'nachname_1')
                    frappe.db.set_value("Mahnung", mahnung.name, 'nachname_kunde', nachname_kunde, update_modified=False)
                elif m.customer == frappe.db.get_value("Mitgliedschaft", m.mv_mitgliedschaft, 'rg_kunde'):
                    nachname_kunde = frappe.db.get_value("Mitgliedschaft", m.mv_mitgliedschaft, 'rg_nachname')
                    frappe.db.set_value("Mahnung", mahnung.name, 'nachname_kunde', nachname_kunde, update_modified=False)
            elif m.mv_kunde:
                nachname_kunde = frappe.db.get_value("Kunden", m.mv_kunde, 'nachname')
                frappe.db.set_value("Mahnung", mahnung.name, 'nachname_kunde', nachname_kunde, update_modified=False)
            
            loop += 1
        frappe.db.commit()
    except:
        print("Patch v8.9.18 failed")
        pass
    return
