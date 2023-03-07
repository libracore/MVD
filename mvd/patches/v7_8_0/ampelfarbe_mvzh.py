import frappe
from frappe import _
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_ampelfarbe

def execute():
    print("Aktualisiere Ampelfarbe MVZH")
    mitgliedschaften = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `sektion_id` = 'MVZH'""", as_dict=True)
    count = 1
    total = len(mitgliedschaften)
    for mitgliedschaft in mitgliedschaften:
        m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
        ampelfarbe = get_ampelfarbe(m)
        if m.ampel_farbe != ampelfarbe:
            frappe.db.set_value("Mitgliedschaft", m.name, 'ampel_farbe', ampelfarbe)
        frappe.db.commit()
        print("{0} von {1}".format(count, total))
        count += 1
    return
