import frappe
from frappe import _
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_anredekonvention

def execute():
    print("Lege Customer Group Interessent*in an")
    new_customer_group = frappe.get_doc({
        "doctype": "Customer Group",
        "customer_group_name": "Interessent*in",
        "parent_customer_group": "All Customer Groups"
    })
    new_customer_group.insert()
    
    return
