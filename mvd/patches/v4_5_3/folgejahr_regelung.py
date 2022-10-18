import frappe
from frappe import _
from mvd.mvd.doctype.mitgliedschaft.mitgliedschaft import get_anredekonvention

def execute():
    print("Get betroffene Sektionen")
    sektionen = frappe.db.sql("""SELECT `name`
                                FROM `tabSektion`
                                WHERE `folgejahr_regelung` = 1""", as_dict=True)
    if len(sektionen) > 0:
        print("{0} betroffene Sektionen gefunden".format(len(sektionen)))
        for sektion in sektionen:
            print("Case Mitgliedschaft: Suche nach betroffenen Mitgliedschaften der Sektion {0}".format(sektion.name))
            mitgliedschaften = frappe.db.sql("""SELECT `name`
                                                FROM `tabMitgliedschaft`
                                                WHERE `bezahltes_mitgliedschaftsjahr` = 2022
                                                AND `datum_zahlung_mitgliedschaft` BETWEEN '2022-09-15' AND '2022-12-31'
                                                AND `sektion_id` = '{sektion}'""".format(sektion=sektion.name), as_dict=True)
            if len(mitgliedschaften) > 0:
                print("{0} betroffene Mitgliedschaften gefunden".format(len(mitgliedschaften)))
                loop = 1
                for mitgliedschaft in mitgliedschaften:
                    m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
                    m.save()
                    print("{0} of {1}".format(loop, len(mitgliedschaften)))
                    loop += 1
            else:
                print("Keine betroffenen Mitgliedschaften gefunden")
            
            print("Case HV: Suche nach betroffenen Mitgliedschaften der Sektion {0}".format(sektion.name))
            mitgliedschaften = frappe.db.sql("""SELECT `name`
                                                FROM `tabMitgliedschaft`
                                                WHERE `zahlung_hv` = 2022
                                                AND `datum_hv_zahlung` BETWEEN '2022-09-15' AND '2022-12-31'
                                                AND `sektion_id` = '{sektion}'""".format(sektion=sektion.name), as_dict=True)
            if len(mitgliedschaften) > 0:
                print("{0} betroffene Mitgliedschaften gefunden".format(len(mitgliedschaften)))
                loop = 1
                for mitgliedschaft in mitgliedschaften:
                    m = frappe.get_doc("Mitgliedschaft", mitgliedschaft.name)
                    m.save()
                    print("{0} of {1}".format(loop, len(mitgliedschaften)))
                    loop += 1
            else:
                print("Keine betroffenen Mitgliedschaften gefunden")
    else:
        print("Keine betroffene Sektionen gefunden")
    
    return
