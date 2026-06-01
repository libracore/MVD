import frappe
from frappe import _
from tqdm import tqdm

def execute():
    try:
        mitglieder = frappe.db.sql("""SELECT `name` FROM `tabMitgliedschaft` WHERE `sektion_id` = 'ALVD'""", as_dict=True)
        for mitglied in tqdm(mitglieder, desc="Correct ALVD Mitglieder", unit=" Mitglieder", total=len(mitglieder)):
            m = frappe.get_doc("Mitgliedschaft", mitglied.name)
            if not frappe.db.exists("Region", m.region):
                region = frappe.db.sql("""SELECT `name` FROM `tabRegion` WHERE `region_c` = '{0}' AND `sektion_id` = 'ALVD'""".format(m.region), as_dict=True)
                if len(region) > 0:
                    m.region = region[0].name
                    m.save()
    except Exception as err:
        print("Patch ALV Correction failed")
        print(str(err))
        pass
    return
