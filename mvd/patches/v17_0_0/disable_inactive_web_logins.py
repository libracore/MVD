import frappe
from frappe import _
from tqdm import tqdm

def execute():
    try:
        weblogins = frappe.db.sql("""SELECT `name` FROM `tabUser` WHERE `name` LIKE '%@login.ch'""", as_dict=True)
        for weblogin in tqdm(weblogins, desc="Disable inactive Web-Logins", unit=" WebLogins", total=len(weblogins)):
            active_members = frappe.db.sql("""SELECT COUNT(`name`) AS `qty` FROM `tabMitgliedschaft` WHERE `mitglied_nr` = '{0}' AND `status_c` NOT IN ('Inaktiv', 'Ausschluss')""".format(weblogin.name.replace("@login.ch", "")), as_dict=True)[0].qty
            if active_members < 1:
                frappe.db.set_value("User", weblogin.name, "enabled", 0)
    except Exception as err:
        print("Patch Disable-Weblogins failed")
        print(str(err))
        pass
    return
