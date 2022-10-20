import frappe
from frappe import _
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_anredekonvention

def execute():
    print("Markiere alle CAMT Imports der Version 1")
    camts = frappe.db.sql("""SELECT `name` FROM `tabCAMT Import`""", as_dict=True)
    loop = 1
    if len(camts) > 0:
        for camt in camts:
            frappe.db.sql("""UPDATE `tabCAMT Import` SET `version_1` = 1 WHERE `name` = '{camt}'""".format(camt=camt.name), as_list=True)
            print("CAMT {loop} of {total}".format(loop=loop, total=len(camts)))
            loop += 1
    
    return
