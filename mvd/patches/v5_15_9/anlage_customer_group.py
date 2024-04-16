import frappe
from frappe import _
from mvd.mvd.doctype.mitgliedschaft.utils import get_anredekonvention

def execute():
    print("Lege Customer Group Mitglied an")
    new_customer_group = frappe.get_doc({
        "doctype": "Customer Group",
        "customer_group_name": "Mitglied",
        "parent_customer_group": "All Customer Groups"
    })
    new_customer_group.insert()
    
    return
