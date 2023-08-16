import frappe
from frappe import _
from mvd.mvd.doctype.retouren.retouren import adresse_geaendert_check

def execute():
    try:
        print("Setze Adress Flag bei Retouren")
        retouren = frappe.db.sql("SELECT `name`, `mv_mitgliedschaft`, `retoure_mw_sequence_number` FROM `tabRetouren` WHERE `adresse_geaendert` = 0 AND `mv_mitgliedschaft` IS NOT NULL""", as_dict=True)
        total = len(retouren)
        loop = 1
        betroffen = 0
        for retoure in retouren:
            print("{0} of {1}".format(loop, total))
            adresse = frappe.db.sql("""SELECT `adresse_mitglied` FROM `tabMitgliedschaft` WHERE `name` = '{mitgliedschaft}'""".format(mitgliedschaft=retoure.mv_mitgliedschaft), as_dict=True)
            if len(adresse) > 0:
                if adresse[0].adresse_mitglied and adresse[0].adresse_mitglied != 'None':
                    adresse = adresse[0].adresse_mitglied
                    datum_adressexport = frappe.db.sql("""SELECT `datum_adressexport` FROM `tabMW` WHERE `laufnummer` = '{retoure_mw_sequence_number}' LIMIT 1""".format(retoure_mw_sequence_number=retoure.retoure_mw_sequence_number), as_dict=True)
                    if len(datum_adressexport) > 0:
                        datum_adressexport = datum_adressexport[0].datum_adressexport
                        
                        adresse_geaendert = adresse_geaendert_check(adr=adresse, datum_adressexport=datum_adressexport)
                        if adresse_geaendert == 1:
                            print("ist betroffen")
                            betroffen += 1
                            frappe.db.sql("""UPDATE `tabRetouren` SET `adresse_geaendert` = {adresse_geaendert} WHERE `name` = '{name}'""".format(adresse_geaendert=adresse_geaendert, name=retoure.name), as_list=True)
            loop += 1
        frappe.db.commit()
        print("Fertig, {0} betroffene korrigiert".format(betroffen))
    except Exception as err:
        print("Patch v8.17.2 failed")
        print(str(err))
        pass
    return
