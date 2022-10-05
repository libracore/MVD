import frappe
from frappe import _

def execute():
    # Anzahl M+W = 0 bei allen Mitgliedschaften mit zwei Retouren in Folge
    print("Patch: Anzahl M+W = 0 bei allen Mitgliedschaften mit zwei Retouren in Folge")
    mitgliedschaften = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `status_c` != 'Inaktiv' AND `retoure_in_folge` = 1 AND `m_und_w` != 0""", as_dict=True)
    m_max = len(mitgliedschaften)
    print("found {0} Mitgliedschaften".format(m_max))
    loop = 1
    for mitgliedschaft in mitgliedschaften:
        print("Update {0} of {1}".format(loop, m_max))
        try:
            m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
            m.m_und_w = 0
            m.save()
        except Exception as err:
            print("{0} failed".format(mitgliedschaft.name))
        loop += 1
    return
