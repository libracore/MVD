import frappe
from frappe import _

def execute():
    try:
        from mvd.mvd.doctype.digitalrechnung.digitalrechnung import go_life_reset
        go_life_reset()
        print("Done")
    except Exception as err:
        print("Patch v13.35.0 failed")
        print(str(err))
        pass
    return
