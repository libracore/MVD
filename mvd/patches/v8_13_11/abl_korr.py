import frappe
from frappe import _

def execute():
    try:
        print("Prüfe/Korrigiere offene ABLs")
        abls = frappe.db.sql("""SELECT `name` FROM `tabArbeits Backlog` WHERE `status` = 'Open'""", as_dict=True)
        total = len(abls)
        loop = 1
        for abl in abls:
            print("{0} of {1}".format(loop, total))
            changed = False
            a = frappe.get_doc("Arbeits Backlog", abl.name)
            if a.mv_mitgliedschaft:
                if a.typ == 'Anmeldung mit EZ':
                    if not int(frappe.db.get_value("Mitgliedschaft", a.mv_mitgliedschaft, 'anmeldung_mit_ez')) == 1:
                        a.status = 'Completed'
                        changed = True
                if a.typ == 'Interessent*Innenbrief mit EZ':
                    if not int(frappe.db.get_value("Mitgliedschaft", a.mv_mitgliedschaft, 'interessent_innenbrief_mit_ez')) == 1:
                        a.status = 'Completed'
                        changed = True
            if changed:
                a.save()
            loop += 1
        frappe.db.commit()
    except Exception as err:
        print("Patch v8.13.11 failed")
        print(str(err))
        pass
    return
