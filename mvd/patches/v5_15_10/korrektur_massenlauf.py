import frappe
from frappe import _
from mvd.mvd.doctype.mitgliedschaft.utils import get_anredekonvention

def execute():
    print("Korrektur Massenlauf Referenzen")
    print("Prüfe betroffene Mitgliedschaften")
    mitgliedschaften = frappe.db.sql("""SELECT
                                            `name`
                                        FROM `tabMitgliedschaft`
                                        WHERE `status_c` = 'Inaktiv'
                                        AND (
                                        `validierung_notwendig` = 1
                                        or `kuendigung_verarbeiten` = 1
                                        or `interessent_innenbrief_mit_ez` = 1
                                        or `anmeldung_mit_ez` = 1
                                        or `zuzug_massendruck` = 1
                                        or `rg_massendruck_vormerkung` = 1
                                        or `begruessung_massendruck` = 1
                                        or `begruessung_via_zahlung` = 1
                                        or `zuzugs_rechnung` is not null
                                        or `zuzug_korrespondenz` is not null
                                        or `kuendigung_druckvorlage` is not null
                                        or `rg_massendruck` is not null
                                        or `begruessung_massendruck_dokument` is not null)""", as_dict=True)
    if len(mitgliedschaften) > 0:
        print("{0} betroffene Mitgliedschaften gefunden".format(len(mitgliedschaften)))
        loop = 1
        for mitgliedschaft in mitgliedschaften:
            print("update {loop} von {total}".format(loop=loop, total=len(mitgliedschaften)))
            update = frappe.db.sql("""UPDATE `tabMitgliedschaft`
                                    SET `validierung_notwendig` = 0,
                                    `kuendigung_verarbeiten` = 0,
                                    `interessent_innenbrief_mit_ez` = 0,
                                    `anmeldung_mit_ez` = 0,
                                    `zuzug_massendruck` = 0,
                                    `rg_massendruck_vormerkung` = 0,
                                    `begruessung_massendruck` = 0,
                                    `begruessung_via_zahlung` = 0,
                                    `zuzugs_rechnung` = '',
                                    `zuzug_korrespondenz` = '',
                                    `kuendigung_druckvorlage` = '',
                                    `rg_massendruck` = '',
                                    `begruessung_massendruck_dokument` = ''
                                    WHERE `name` = '{ms}'""".format(ms=mitgliedschaft.name), as_dict=True)
            loop += 1
    else:
        print("Keine betroffene Mitgliedschaften gefunden")
    
    return
