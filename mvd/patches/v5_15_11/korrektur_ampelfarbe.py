import frappe
from frappe import _
from mvd.mvd.doctype.mitgliedschaft.utils import get_ampelfarbe

def execute():
    print("Korrektur Ampelfarben")
    print("Prüfe betroffene Mitgliedschaften")
    mitgliedschaften = frappe.db.sql("""SELECT
                                            `mv_mitgliedschaft`
                                        FROM `tabSales Invoice`
                                        WHERE `mitgliedschafts_jahr` = 2023
                                        AND `rechnungs_jahresversand` IS NOT NULL
                                        AND `docstatus` = 1""", as_dict=True)
    if len(mitgliedschaften) > 0:
        print("{0} betroffene Mitgliedschaften gefunden".format(len(mitgliedschaften)))
        loop = 1
        for mitgliedschaft in mitgliedschaften:
            print("update {loop} von {total}".format(loop=loop, total=len(mitgliedschaften)))
            m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.mv_mitgliedschaft)
            ampelfarbe = get_ampelfarbe(m)
            frappe.db.set_value('Mitgliedschaft', mitgliedschaft.mv_mitgliedschaft, 'ampel_farbe', ampelfarbe)
            loop += 1
    else:
        print("Keine betroffene Mitgliedschaften gefunden")
    
    return
