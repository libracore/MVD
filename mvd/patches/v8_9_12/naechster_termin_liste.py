import frappe
from frappe import _

def execute():
    try:
        print("Aktualisiere Beratungen (Nächster Termin)")
        frappe.reload_doc("mvd", "doctype", "Beratung")
        beratungen = frappe.db.sql("""SELECT `name` FROM `tabBeratung`""", as_dict=True)
        total = len(beratungen)
        loop = 1
        for beratung in beratungen:
            print("{0} of {1}".format(loop, total))
            b = frappe.get_doc("Beratung", beratung.name)
            if len(b.termin) > 0:
                naechster_termin = frappe.utils.get_datetime(b.termin[len(b.termin) - 1].von).strftime('%d.%m.%Y %H:%M')
                frappe.db.set_value("Beratung", beratung.name, 'naechster_termin', naechster_termin, update_modified=False)
            loop += 1
        frappe.db.commit()
    except:
        print("Patch v8.9.12 failed")
        pass
    return
