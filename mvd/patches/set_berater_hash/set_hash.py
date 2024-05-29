import frappe
from frappe import _
import hashlib

def execute():
    # this will create md5 hashes
    try:
        frappe.reload_doc("mvd", "doctype", "Termin Kontaktperson")
        berater = frappe.db.sql("""
                                SELECT `name`
                                FROM `tabTermin Kontaktperson`
                                WHERE `disabled` != 1
                                """, as_dict=True)
        for b in berater:
            try:
                dataset = frappe.get_doc("Termin Kontaktperson", b.name)
                if not dataset.md_hash:
                    dataset.md_hash = hashlib.md5(str(dataset.name).encode()).hexdigest()
                    dataset.save()
                frappe.db.commit()
            except Exception as e:
                print("Unable to create hash for {0}".format(b.name))
                print(str(e))
    except Exception as err:
        print("Unable to create hashes")
        print(str(err))
    return

    
